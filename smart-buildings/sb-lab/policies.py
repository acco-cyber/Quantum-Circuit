"""Zone PI controller from the public notebook "smart-buildings-zone-pi-no-night-ceiling".

Copied unchanged from the notebook (credit: Malyshev Danil, "Probe Zone PI K10"),
which scored 0.01981 on the public leaderboard. Only the module layout differs:
the classes here do not inherit the Kaggle `Policy` base, so they import without
`kaggle_evaluation`; the submission notebook mixes that base in.

Classes, each built on the previous one:
  BaselinePolicy     organizer PIDWaterResetPolicy + sensor comfort bands + decoded OAT
  CoolingHoldPolicy  + keep AHUs started for cooling running >= HOLD_STEPS
  ZonePIPolicy       + per-zone PI to band centre during work hours, AHUs forced on
  ZonePIK10          the submitted parameters (KP=0.1, KI=0.005)
"""
import numpy as np

from smart_buildings.baselines.pid_plus import PIDWaterResetPolicy


class BaselinePolicy(PIDWaterResetPolicy):
    USE_SENSOR_BAND = True
    # Worst-zone aggregation increased loss in both full-length pilot scenarios.
    USE_WORST_ZONE = False

    @property
    def name(self):
        return "transfer"

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        stats = self.observation_normalization_metadata.get(
            "outside_air_temperature_sensor", {}
        )
        self.outside_mean = float(stats.get("sample_mean", 0.0))
        self.outside_std = float(stats.get("sample_std", 1.0))

    def _recirculation(self, obs, ctrl, u, low, high):
        # The parent's economizer expects kelvin; the observation is standardized.
        idx = ctrl.get("oat_idx")
        if idx is None:
            return 1.0
        decoded = obs.copy()
        decoded[idx] = obs[idx] * self.outside_std + self.outside_mean
        return super()._recirculation(decoded, ctrl, u, low, high)

    def get_action(self, obs):
        action = super().get_action(obs)
        # Enforce the gateway's dtype, shape and bounds contract.
        for key, dtype in (("continuous_action", np.float32),
                           ("discrete_action", np.int32)):
            space = self.action_spec[key]
            action[key] = np.clip(action[key], space.low, space.high).astype(dtype)
        return action


class CoolingHoldPolicy(BaselinePolicy):
    HOLD_STEPS = 288
    # Outside work hours use (eco low, comfort high): no overnight drift up to
    # the eco ceiling in hot climates, full heating setback kept in cold ones.
    NIGHT_COOL_CEILING = False

    @property
    def name(self):
        return f"cooling_hold_{self.HOLD_STEPS}"

    def _base_action(self, obs):
        if not self.NIGHT_COOL_CEILING:
            return super().get_action(obs)
        hour, day = self._get_hour_and_day(obs)
        if day < 5 and self.morning_start_hour <= hour < self.evening_start_hour:
            return super().get_action(obs)
        saved = self.eco_temp_window
        self.eco_temp_window = (saved[0], self.comfort_temp_window[1])
        try:
            return super().get_action(obs)
        finally:
            self.eco_temp_window = saved

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        self._on_steps = [0] * len(self.ahu_controllers)
        self._last_on = [None] * len(self.ahu_controllers)

    def get_action(self, obs):
        action = self._base_action(obs)
        cont, disc = action["continuous_action"], action["discrete_action"]
        for i, ctrl in enumerate(self.ahu_controllers):
            if not ctrl["zone_obs_indices"]:
                continue
            run = ctrl["run_discrete_idx"]
            # Supply temperature first: its sign tells cooling from heating.
            idx = [j for j in (ctrl["temp_idx"], ctrl["pressure_idx"], ctrl.get("recirc_idx"))
                   if j is not None]
            if (not disc[run] and self._on_steps[i] > 0
                    and self._on_steps[i] < self.HOLD_STEPS and self._last_on[i][0] < 0):
                disc[run] = 1
                cont[idx] = self._last_on[i]
            if disc[run]:
                self._on_steps[i] += 1
                self._last_on[i] = cont[idx].copy()
            else:
                self._on_steps[i] = 0
        return action


class ZonePIPolicy(CoolingHoldPolicy):
    """Per-zone PI control to the band centre in work hours.

    Each zone runs a PI loop on (temperature - band centre) from PRESTART_H
    before occupancy to the end of the work day. One signal u in [-1, 1] drives
    both actuators: the damper opens with |u| and the reheat valve with -u.
    AHUs are kept running in those hours so the zones have air to work with.
    """
    HOLD_STEPS = 288
    NIGHT_COOL_CEILING = False
    KP = 0.2
    KI = 0.02
    PRESTART_H = 1
    FORCED_SAT = -0.7       # normalized supply temp for a forced-on AHU (~15 C)
    FORCED_PRESSURE = -0.6  # normalized static pressure for a forced-on AHU
    MIN_DAMPER = 0.1
    KEY = "zone_pi"

    @property
    def name(self):
        return self.KEY

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        self._zone_integral = {}
        self._pi_active = False
        self._zone_u = {}

    def _pi_hours(self, obs):
        hour, day = self._get_hour_and_day(obs)
        return day < 5 and self.morning_start_hour - self.PRESTART_H <= hour < self.evening_start_hour

    def _command_zones(self, continuous, zones, obs, low, high):
        if not self._pi_active:
            for vav_id, _, _ in zones:
                self._zone_integral[vav_id] = 0.0
            return super()._command_zones(continuous, zones, obs, low, high)
        lo_c, hi_c = self.comfort_temp_window
        for vav_id, obs_idx, action_indices in zones:
            if not action_indices:
                continue
            lo, hi = self._zone_band(obs, vav_id, lo_c, hi_c)
            # Before occupancy the sensor band is still the eco band; aim at comfort.
            if hi - lo > (hi_c - lo_c) + 1e-6:
                lo, hi = lo_c, hi_c
            err = self._denormalize_zone_temp(obs[obs_idx]) - self._zone_target(obs, lo, hi)
            integral = self._zone_integral.get(vav_id, 0.0)
            if err == 0.0:
                # Only reachable with a deadband target; bleeds off stored effort.
                integral *= self.INTEGRAL_LEAK
            u_raw = self.KP * err + self.KI * integral
            # Conditional integration: stop winding up while saturated.
            if abs(u_raw) < 1.0 or np.sign(err) != np.sign(u_raw):
                integral = float(np.clip(integral + err, -1.0 / self.KI, 1.0 / self.KI))
            self._zone_integral[vav_id] = integral
            u = float(np.clip(self.KP * err + self.KI * integral, -1.0, 1.0))
            self._max_heat = max(self._max_heat, -u)
            self._zone_u[vav_id] = u
            gain = self.HEAT_DAMPER_GAIN if u < 0 else 1.0
            damper = self.MIN_DAMPER + (1.0 - self.MIN_DAMPER) * abs(u) * gain
            damper_idx = action_indices.get("supply_air_damper_percentage_command")
            if damper_idx is not None:
                continuous[damper_idx] = 2.0 * damper - 1.0
            reheat_idx = action_indices.get("reheat_valve_percentage_command")
            if reheat_idx is not None:
                continuous[reheat_idx] = 2.0 * max(0.0, -u) - 1.0

    # Damper opening per unit of heating demand (reheated air costs gas).
    HEAT_DAMPER_GAIN = 1.0
    # Integral decay per step while a zone sits exactly on target (deadband targets).
    INTEGRAL_LEAK = 1.0

    def _should_force(self, i, ctrl):
        """Whether an idle AHU is forced on in PI hours; always, by default."""
        return True

    def _zone_target(self, obs, lo, hi):
        """Temperature each zone's PI loop aims at; the band centre by default."""
        return 0.5 * (lo + hi)

    def _base_action(self, obs):
        self._pi_active = self._pi_hours(obs)
        self._max_heat = 0.0
        self._forced = []
        self._zone_u = {}
        action = super()._base_action(obs)
        if self._pi_active:
            cont, disc = action["continuous_action"], action["discrete_action"]
            # Zone reheat needs hot water even when no AHU loop asks for heat.
            if self.water_temp_idx is not None and self._max_heat > 0:
                cont[self.water_temp_idx] = max(cont[self.water_temp_idx],
                                                np.float32(2.0 * self._max_heat - 1.0))
                if self.water_pressure_idx is not None:
                    cont[self.water_pressure_idx] = 1.0
            for i, ctrl in enumerate(self.ahu_controllers):
                if (ctrl["zone_obs_indices"] and not disc[ctrl["run_discrete_idx"]]
                        and self._should_force(i, ctrl)):
                    self._forced.append(i)
                    disc[ctrl["run_discrete_idx"]] = 1
                    cont[ctrl["temp_idx"]] = self.FORCED_SAT
                    if ctrl["pressure_idx"] is not None:
                        cont[ctrl["pressure_idx"]] = self.FORCED_PRESSURE
            if 0 <= self.water_discrete_idx < self.n_discrete:
                disc[self.water_discrete_idx] = 1
        return action

    def get_action(self, obs):
        action = super().get_action(obs)
        # A forced-on unit is not a cooling run; do not let the hold extend it.
        for i in self._forced:
            if self._last_on[i] is not None:
                self._last_on[i][0] = 0.0
        return action


class ZonePIK10(ZonePIPolicy):
    """The parameters submitted in the 0.01981 notebook."""
    KP = 0.1
    KI = 0.005
    HOLD_STEPS = 288
    NIGHT_COOL_CEILING = False
    KEY = "zone_pi_k10"


class PIDWater(PIDWaterResetPolicy):
    """Organizer baseline, clipped to the action bounds (pid_water in baseline_returns.json)."""

    @property
    def name(self):
        return "pid_water"

    def get_action(self, obs):
        action = super().get_action(obs)
        for key, dtype in (("continuous_action", np.float32),
                           ("discrete_action", np.int32)):
            space = self.action_spec[key]
            action[key] = np.clip(action[key], space.low, space.high).astype(dtype)
        return action

"""Off-hours energy variants of the zone PI controller.

Comfort is only charged while zones are occupied (weekdays 06-19 on the sim
clock), so nights and weekends are pure energy/carbon cost. Levers tried here:

  HOLD_STEPS          cooling-run hold length (288 in the baseline; it can keep
                      an AHU cooling through the night)
  SETBACK_LO/HI_K     widen the off-hours (eco) band by this much on the
                      heating / cooling side, for the AHU loop, the zone
                      dampers/reheat and the hot-water reset alike
  ADAPTIVE_PRESTART   start the work-hours PI earlier when zones are far from
                      the comfort band: lead = LEAD_BASE_H + worst shortfall /
                      RECOVERY_K_PER_H, clipped to [LEAD_MIN_H, LEAD_MAX_H]
  OCC_GATE            after OCC_GATE_AFTER_H, once the building is empty
                      (num_occupants == 0) end the work-hours mode for the day
"""
import math

import numpy as np



class OffHoursPolicy(ZonePIK10):
    HOLD_STEPS = 288
    SETBACK_LO_K = 0.0
    SETBACK_HI_K = 0.0
    ADAPTIVE_PRESTART = False
    LEAD_BASE_H = 0.5
    RECOVERY_K_PER_H = 2.0
    LEAD_MIN_H = 1.0
    LEAD_MAX_H = 4.0
    OCC_GATE = False
    OCC_GATE_AFTER_H = 12.0
    # Optimal start: learn the building's recovery rate (K/h) from each morning.
    # Still short of the band at work start -> slower than assumed; band reached
    # EARLY_H or more before work start -> faster than assumed.
    LEARN_RATE = False
    RATE_MIN, RATE_MAX = 0.5, 8.0
    RATE_DOWN, RATE_UP = 0.75, 1.15
    RECOVERED_K = 0.5
    EARLY_H = 0.5
    KEY = "offhours"

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        names = list(self.field_names)
        self._occ_idx = names.index("num_occupants") if "num_occupants" in names else None
        self._zone_obs = [j for c in self.ahu_controllers for j in c["zone_obs_indices"]]
        self._pi_now = False
        self._latched_day = None
        self._gated_day = None
        self._widen = False
        self._rate = float(self.RECOVERY_K_PER_H)
        self._reached_at = None
        self._judged_day = None

    def _hour_frac(self, obs):
        angle = math.atan2(float(obs[self.hod_sin_index]), float(obs[self.hod_cos_index]))
        if angle < 0:
            angle += 2 * math.pi
        # The epsilon keeps exact hour boundaries on the same side as the parent's
        # floor-based integer hour, so the defaults reproduce ZonePIK10.
        return 24.0 * angle / (2 * math.pi) + 1e-6

    def _worst_shortfall(self, obs):
        """Largest distance (K) of any zone outside the comfort band."""
        lo_c, hi_c = self.comfort_temp_window
        temps = np.array([self._denormalize_zone_temp(obs[j]) for j in self._zone_obs])
        return float(np.max(np.maximum(0.0, np.maximum(lo_c - temps, temps - hi_c)), initial=0.0))

    def _lead_hours(self, obs):
        if not self.ADAPTIVE_PRESTART:
            return float(self.PRESTART_H)
        lead = self.LEAD_BASE_H + self._worst_shortfall(obs) / self._rate
        return float(np.clip(lead, self.LEAD_MIN_H, self.LEAD_MAX_H))

    def _learn_rate(self, obs, day, hour):
        """Once per prestarted morning, nudge the recovery-rate estimate."""
        if self._latched_day != day or self._judged_day == day:
            return
        if hour < self.morning_start_hour:
            if self._reached_at is None and self._worst_shortfall(obs) <= self.RECOVERED_K:
                self._reached_at = hour
            return
        if self._worst_shortfall(obs) > self.RECOVERED_K:
            self._rate *= self.RATE_DOWN
        elif self._reached_at is not None and self._reached_at <= self.morning_start_hour - self.EARLY_H:
            self._rate *= self.RATE_UP
        self._rate = float(np.clip(self._rate, self.RATE_MIN, self.RATE_MAX))
        self._judged_day = day
        self._reached_at = None

    def _update_schedule(self, obs):
        _, day = self._get_hour_and_day(obs)
        hour = self._hour_frac(obs)
        active = False
        if day < 5 and hour < self.evening_start_hour and self._gated_day != day:
            if self._latched_day != day and hour >= self.morning_start_hour - self._lead_hours(obs):
                self._latched_day = day
                self._reached_at = None
            active = self._latched_day == day
            if active and self.LEARN_RATE:
                self._learn_rate(obs, day, hour)
            if (active and self.OCC_GATE and self._occ_idx is not None
                    and hour >= self.OCC_GATE_AFTER_H and float(obs[self._occ_idx]) <= 0.0):
                self._gated_day = day
                active = False
        self._pi_now = active

    def _pi_hours(self, obs):
        return self._pi_now

    def _zone_band(self, obs, vav_id, low, high):
        lo, hi = super()._zone_band(obs, vav_id, low, high)
        if self._widen:
            lo, hi = lo - self.SETBACK_LO_K, hi + self.SETBACK_HI_K
        return lo, hi

    def _base_action(self, obs):
        if self._pi_now or (self.SETBACK_LO_K == 0.0 and self.SETBACK_HI_K == 0.0):
            return super()._base_action(obs)
        saved = self.eco_temp_window
        self.eco_temp_window = (saved[0] - self.SETBACK_LO_K, saved[1] + self.SETBACK_HI_K)
        self._widen = True
        try:
            return super()._base_action(obs)
        finally:
            self.eco_temp_window = saved
            self._widen = False

    def get_action(self, obs):
        self._update_schedule(obs)
        return super().get_action(obs)


class NoHold(OffHoursPolicy):
    HOLD_STEPS = 0
    KEY = "nohold"


class AdaptPre(OffHoursPolicy):
    ADAPTIVE_PRESTART = True
    KEY = "adaptpre"


class Setback2(OffHoursPolicy):
    SETBACK_LO_K = 2.0
    SETBACK_HI_K = 2.0
    ADAPTIVE_PRESTART = True
    KEY = "setback2"


class Setback2NoHold(Setback2):
    HOLD_STEPS = 0
    KEY = "setback2_nohold"


class CoolSetback3NoHold(OffHoursPolicy):
    SETBACK_HI_K = 3.0
    HOLD_STEPS = 0
    ADAPTIVE_PRESTART = True
    KEY = "coolsetback3_nohold"


class OccGate(OffHoursPolicy):
    OCC_GATE = True
    KEY = "occgate"


class OptStart(OffHoursPolicy):
    ADAPTIVE_PRESTART = True
    LEARN_RATE = True
    KEY = "optstart"


class OptStart4(OptStart):
    RECOVERY_K_PER_H = 4.0
    KEY = "optstart4"


class OptStartSetback2(OptStart):
    SETBACK_LO_K = 2.0
    SETBACK_HI_K = 2.0
    KEY = "optstart_setback2"


class OptStartLazy(OptStart):
    """Optimal start that stays near the baseline 1 h lead unless mornings really fail.

    Prior rate 8 K/h gives about 1.1 h of lead from a 5 K setback. Only a zone still
    more than RECOVERED_K short at work start lengthens it, and quickly (rate halves).
    """
    RECOVERY_K_PER_H = 8.0
    RECOVERED_K = 1.5
    RATE_DOWN = 0.5
    KEY = "optstart_lazy"


class OptStartLazy1K(OptStartLazy):
    RECOVERED_K = 1.0
    KEY = "optstart_lazy1k"


class OptStartLazyCoolSetback2(OptStartLazy):
    SETBACK_HI_K = 2.0
    KEY = "optstart_lazy_coolsb2"

"""Demand-based supply air + economizer fix, from the public notebook
"smart-buildings-probe-ds-k07" (public LB 0.01708 at the time of copying).

Classes up to TunedDemandSatPolicy are copied unchanged from that notebook.
Its ideas on top of zone PI:
  * Economizer fix: the AHU outside-air sensors arrive in raw kelvin, but
    BaselinePolicy decoded them as normalized (271 K -> ~3000 K), so the
    economizer never drew free cooling. Verified locally.
  * Demand SAT: in work hours a running AHU's supply-air setpoint follows the
    mean PI demand of its zones: net heating -> SAT at maximum (no chilling of
    air that zone reheat must warm again); net cooling -> ~15 C.
  * Forced-on AHUs at minimum static pressure, deeper night heating setback
    (2 K) with a fixed 2 h prestart, night cooling ceiling, softer zone gains.

DSK07 is their submitted configuration. EconFixOnly isolates the economizer
fix; DSK07Adapt swaps the fixed prestart for our adaptive one (offhours.py).
"""
import numpy as np



def _outside_kelvin(policy, value):
    """AHU outside-air sensors arrive in raw kelvin; decode only if normalized."""
    value = float(value)
    return value if value > 150.0 else value * policy.outside_std + policy.outside_mean


class ZonePIEconFixPolicy(ZonePIPolicy):
    """pe_lowp with a working economizer (raw-kelvin outside air temperature).

    TransferPolicy decoded the AHU outside-air sensor as if normalized, but it
    arrives in kelvin, so the economizer saw ~3000 K outside and never opened.
    """
    KP = 0.10
    KI = 0.005
    FORCED_PRESSURE = -1.0
    WARM_SAT = None
    WARM_BELOW_K = 283.15
    KEY = "econ_fix"

    def _recirculation(self, obs, ctrl, u, low, high):
        idx = ctrl.get("oat_idx")
        if idx is None:
            return 1.0
        fixed = obs.copy()
        fixed[idx] = _outside_kelvin(self, obs[idx])
        # Skip TransferPolicy's decoding; call the organizer economizer directly.
        return super(BaselinePolicy, self)._recirculation(fixed, ctrl, u, low, high)

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if self.WARM_SAT is None:
            return action
        cont = action["continuous_action"]
        for i in self._forced:
            ctrl = self.ahu_controllers[i]
            idx = ctrl.get("oat_idx")
            if idx is not None and _outside_kelvin(self, obs[idx]) < self.WARM_BELOW_K:
                cont[ctrl["temp_idx"]] = self.WARM_SAT
        return action


class DemandSatPolicy(ZonePIEconFixPolicy):
    """Supply-air temperature follows the zones' own PI demand in work hours.

    Forced-on AHUs used a fixed ~15 C supply. In cool weather that chills an
    already cool mix, then zone reheat burns gas to warm it back. Here each
    running AHU looks at the mean PI output of its zones (positive = cooling):
    with net heating demand the supply setpoint goes to maximum (no chiller);
    with cooling demand it ramps down to ~15 C, reached at mean demand RAMP
    (RAMP 0 = switch at zero demand).
    """
    RAMP = 0.0
    COLD_SAT = -0.7
    KEY = "dsat_bin"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            us = [self._zone_u[v] for v, _, _ in ctrl["zones"] if v in self._zone_u]
            if not us or not disc[ctrl["run_discrete_idx"]]:
                continue
            d = float(np.mean(us))
            frac = (float(np.clip(d / self.RAMP, 0.0, 1.0)) if self.RAMP > 0
                    else (1.0 if d > 0 else 0.0))
            cont[ctrl["temp_idx"]] = np.float32(1.0 + frac * (self.COLD_SAT - 1.0))
        return action


class TunedPIPolicy(ZonePIEconFixPolicy):
    """econ_fix_warmcold plus switchable energy measures, all off by default.

    NIGHT_HEAT_DROP_K: lower the heating setpoint outside PI hours.
    WATER_SCALE: scale the hot-water temperature command (0..1 of range).
    TARGET_SHIFT_K: aim zones this far from the band centre towards the side
        the weather pushes them to (cheaper to hold).
    OCC_GATE: after the arrival hour, run PI hours only while the building
        reports occupants (skips holidays and empty days).
    """
    WARM_SAT = -0.4
    NIGHT_HEAT_DROP_K = 0.0
    WATER_SCALE = 1.0
    TARGET_SHIFT_K = 0.0
    OCC_GATE = False
    KEY = "tuned"

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        names = list(self.field_names)
        self._occ_idx = names.index("num_occupants") if "num_occupants" in names else None
        self._oat_any = next((c["oat_idx"] for c in self.ahu_controllers
                              if c.get("oat_idx") is not None), None)

    def _pi_hours(self, obs):
        active = super()._pi_hours(obs)
        if active and self.OCC_GATE and self._occ_idx is not None:
            hour, _ = self._get_hour_and_day(obs)
            if hour >= self.morning_start_hour + 2 and float(obs[self._occ_idx]) < 0.5:
                return False
        return active

    def _zone_target(self, obs, lo, hi):
        centre = 0.5 * (lo + hi)
        if self.TARGET_SHIFT_K <= 0 or self._oat_any is None:
            return centre
        outside = _outside_kelvin(self, obs[self._oat_any])
        shift = min(self.TARGET_SHIFT_K, 0.4 * (hi - lo))
        return centre - shift if outside < centre else centre + shift

    def _zone_band(self, obs, vav_id, low, high):
        lo, hi = super()._zone_band(obs, vav_id, low, high)
        if self.NIGHT_HEAT_DROP_K and not self._pi_active:
            lo -= self.NIGHT_HEAT_DROP_K
        return lo, hi

    def _ahu_error(self, obs, ctrl, low, high):
        if self.NIGHT_HEAT_DROP_K and not self._pi_active:
            low -= self.NIGHT_HEAT_DROP_K
        return super()._ahu_error(obs, ctrl, low, high)

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if self.WATER_SCALE != 1.0 and self.water_temp_idx is not None:
            cont = action["continuous_action"]
            frac = (float(cont[self.water_temp_idx]) + 1.0) * 0.5 * self.WATER_SCALE
            cont[self.water_temp_idx] = np.float32(2.0 * frac - 1.0)
        return action


class TunedDemandSatPolicy(TunedPIPolicy, DemandSatPolicy):
    """dsat_bin with the TunedPIPolicy switches (all off by default)."""
    WARM_SAT = None  # dsat_bin did not use the cold-weather warm supply
    KEY = "tuned_dsat"


class DSK07(TunedDemandSatPolicy):
    """The configuration submitted in the 0.01708 notebook."""
    KP = 0.07
    KI = 0.0035
    HOLD_STEPS = 288
    NIGHT_COOL_CEILING = True
    FORCED_PRESSURE = -1.0
    NIGHT_HEAT_DROP_K = 2.0
    PRESTART_H = 2
    KEY = "ds_k07"


class EconFixOnly(ZonePIEconFixPolicy):
    """ZonePIK10 with only the economizer fix (forced pressure kept at -0.6)."""
    FORCED_PRESSURE = -0.6
    KEY = "econ_fix_only"


class DSK07Adapt(OffHoursPolicy, DSK07):
    """DSK07 with our adaptive prestart (1-4 h by worst zone shortfall) instead of a fixed 2 h.

    OffHoursPolicy only supplies the schedule (_pi_hours); its setback is off, so the
    night heating drop still comes from DSK07. ZonePIK10 sits earlier in the MRO, so
    DSK07's attributes are restated here.
    """
    KP = 0.07
    KI = 0.0035
    HOLD_STEPS = 288
    NIGHT_COOL_CEILING = True
    FORCED_PRESSURE = -1.0
    NIGHT_HEAT_DROP_K = 2.0
    PRESTART_H = 2
    WARM_SAT = None
    ADAPTIVE_PRESTART = True
    KEY = "ds_k07_adapt"


class DSA_Deadband(DSK07Adapt):
    """Zones float freely inside [lo + DEADBAND_K, hi - DEADBAND_K]; an idle AHU is only
    forced on in PI hours when one of its zones actually asks for air (|u| > FORCE_U_MIN)."""
    DEADBAND_K = 0.5
    INTEGRAL_LEAK = 0.97
    FORCE_U_MIN = 0.05
    KEY = "dsa_deadband"

    def _zone_target(self, obs, lo, hi):
        # Called once per zone with that zone's live temperature in self._cur_temp.
        return float(np.clip(self._cur_temp, lo + self.DEADBAND_K, hi - self.DEADBAND_K))

    def _denormalize_zone_temp(self, normalized_value):
        t = super()._denormalize_zone_temp(normalized_value)
        self._cur_temp = t
        return t

    def _should_force(self, i, ctrl):
        us = [abs(self._zone_u.get(v, 0.0)) for v, _, _ in ctrl["zones"]]
        return bool(us) and max(us) > self.FORCE_U_MIN


class DSA_Shift1(DSK07Adapt):
    TARGET_SHIFT_K = 1.0
    KEY = "dsa_shift1"


class DSA_NightFloat(DSK07Adapt):
    NIGHT_COOL_CEILING = False
    SETBACK_HI_K = 3.0
    KEY = "dsa_nightfloat"


class DSA_SatRamp(DSK07Adapt):
    RAMP = 0.5
    KEY = "dsa_satramp"


class DSA_HeatLowAir(DSK07Adapt):
    HEAT_DAMPER_GAIN = 0.3
    KEY = "dsa_heatlowair"


class DSA_DeepNight(DSK07Adapt):
    NIGHT_HEAT_DROP_K = 5.0
    LEAD_MAX_H = 6.0
    KEY = "dsa_deepnight"


class DSA_DeadbandRamp(DSA_Deadband):
    RAMP = 0.5
    KEY = "dsa_deadband_ramp"


class DSA_Combo(DSK07Adapt):
    """NightFloat (no night cooling ceiling, +3 K cooling setback) + DeepNight (5 K heat drop)."""
    NIGHT_COOL_CEILING = False
    SETBACK_HI_K = 3.0
    NIGHT_HEAT_DROP_K = 5.0
    LEAD_MAX_H = 6.0
    KEY = "dsa_combo"


class DSA_DeadbandHeat(DSA_Deadband):
    """Float only on the heating side: zones between lo + DEADBAND_K and the band centre
    are left alone; above the centre the PI regulates to the centre as in DSK07."""
    KEY = "dsa_deadband_heat"

    def _zone_target(self, obs, lo, hi):
        return float(np.clip(self._cur_temp, lo + self.DEADBAND_K, 0.5 * (lo + hi)))


class DSA_ComboDBH(DSA_DeadbandHeat):
    NIGHT_COOL_CEILING = False
    SETBACK_HI_K = 3.0
    NIGHT_HEAT_DROP_K = 5.0
    LEAD_MAX_H = 6.0
    KEY = "dsa_combo_dbh"


class DSA_PBoost(DSA_ComboDBH):
    """Raise an AHU's static pressure when its zones run out of authority.

    VAV flow scales with sqrt(static pressure / 2000 Pa), so at the 200 Pa floor
    (FORCED_PRESSURE = -1) a fully open damper still gets only ~32% of design flow.
    Every running AHU in PI hours gets pressure -1 + 2 * clip((demand - BOOST_U0) /
    (1 - BOOST_U0), 0, 1) if that is above what it already commands, where demand is
    the largest zone |u|. Screened: fixes Phoenix July comfort, but makes deep cold
    much worse (see DSA_PBoostCool), so do not submit this one.
    """
    BOOST_U0 = 0.7
    KEY = "dsa_pboost"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            if ctrl["pressure_idx"] is None or not disc[ctrl["run_discrete_idx"]]:
                continue
            demand = self._boost_demand(ctrl)
            if demand is None:
                continue
            frac = float(np.clip((demand - self.BOOST_U0) / (1.0 - self.BOOST_U0), 0.0, 1.0))
            cont[ctrl["pressure_idx"]] = np.float32(max(float(cont[ctrl["pressure_idx"]]), 2.0 * frac - 1.0))
        return action

    def _boost_demand(self, ctrl):
        """Largest zone PI effort |u| under this AHU, or None if no zone reported."""
        us = [abs(self._zone_u[v]) for v, _, _ in ctrl["zones"] if v in self._zone_u]
        return max(us) if us else None


class DSA_PBoost4(DSA_PBoost):
    BOOST_U0 = 0.4
    KEY = "dsa_pboost4"


class DSA_PBoostCool(DSA_PBoost):
    """Pressure boost driven by cooling saturation only.

    The plain boost fixed hot-climate comfort (Phoenix July zones too warm) but hurt
    deep cold badly: more air drags 30% outdoor air at -30 C through reheat coils that
    are already at their limit, so discharge air cools and zones get colder. Heating
    demand (u < 0) therefore never raises the pressure here.
    """
    KEY = "dsa_pboost_cool"

    def _boost_demand(self, ctrl):
        us = [self._zone_u[v] for v, _, _ in ctrl["zones"] if v in self._zone_u]
        return max(0.0, max(us)) if us else None


class DSA_HeatGain0(DSA_ComboDBH):
    """Heating zones keep the damper at its floor (HEAT_DAMPER_GAIN = 0).

    The hot-water loop is shared: total flow = Kv_sum * sqrt(dP / (1 + Kv_sum^2 * R)),
    so in deep cold with most valves open each coil gets a fixed trickle of water and
    transfers a fixed amount of heat. Extra air then only adds ~0 C mixed air (30%
    outdoor air at -30 C), cooling the zone. Opening the damper for heating demand is
    counterproductive in that regime; this tests the other extreme.
    """
    HEAT_DAMPER_GAIN = 0.0
    KEY = "dsa_heatgain0"


class DSA_HeatGain05(DSA_ComboDBH):
    HEAT_DAMPER_GAIN = 0.5
    KEY = "dsa_heatgain05"


class DSA_HeatGain07(DSA_ComboDBH):
    HEAT_DAMPER_GAIN = 0.7
    KEY = "dsa_heatgain07"


class DSA_HeatGain035(DSA_ComboDBH):
    HEAT_DAMPER_GAIN = 0.35
    KEY = "dsa_heatgain035"


# Simulator constants shared by every shipped and generated building (config.gin:
# vav_max_air_flowrate, vav_reheat_water_flowrate; VAV / hot-water code defaults).
VAV_MAX_FLOW_M3S = 2.0
VAV_DESIGN_PRESSURE_PA = 2000.0
REHEAT_KV_MAX = 0.108          # m^3/h per sqrt(bar), header resistance 0
MAX_DISCHARGE_K = 308.15
AIR_CP_RHO = 1.2 * 1006.0      # J/(m^3 K)
WATER_CP_RHO = 1000.0 * 4180.0
SAT_MIN_K, SAT_MAX_K = 285.0, 305.0


class DSA_HeatOpt(DSA_ComboDBH):
    """Cap each heating zone's damper at the airflow that maximises delivered heat.

    Reheat coil (vav.py): discharge = T_s + e (T_w - T_s), e = min(1, C_w / C_a,
    (35 C - T_s) / (T_w - T_s)). Heat into the zone is C_a (discharge - T_z):
    it rises with air while the 35 C discharge cap binds, and falls once the water
    side limits, because extra air is mixed air (30% outdoor air) the coil can no
    longer warm. The peak is at C_a* = C_w (T_w - T_s) / (35 C - T_s), i.e. the
    damper at which discharge air just reaches 35 C. Each coil's water flow is
    Kv * sqrt(dP) / 3600 (header resistance is 0, so coils do not share).
    Everything comes from live observations (water temperature, pump dP, outside
    air) and this step's own commands (valve, recirculation, SAT, static pressure).
    """
    HEAT_CAP = True
    HEAT_PRESSURE_OPT = False
    SAT_HEAT_U = -0.9          # zones at or below this effort count as saturated
    KEY = "dsa_heatopt"

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        names = list(self.field_names)
        self._tw_idx = names.index("hws_supply_water_temperature_sensor") \
            if "hws_supply_water_temperature_sensor" in names else None
        self._dp_idx = names.index("hws_differential_pressure_sensor") \
            if "hws_differential_pressure_sensor" in names else None

    @staticmethod
    def _native(cmd, lo, hi):
        return lo + (float(cmd) + 1.0) * 0.5 * (hi - lo)

    def _coil_targets(self, obs, cont, ctrl, pressure_pa):
        """Per heating zone: (damper index, optimal damper at pressure_pa, needed flow m^3/s)."""
        tw = float(obs[self._tw_idx])
        dp = max(float(obs[self._dp_idx]), 0.0)
        oat_idx = ctrl.get("oat_idx")
        if oat_idx is None or tw <= MAX_DISCHARGE_K or dp <= 0.0:
            return []
        oat = _outside_kelvin(self, obs[oat_idx])
        t_ret = float(np.mean([self._denormalize_zone_temp(obs[j]) for j in ctrl["zone_obs_indices"]]))
        recirc = 0.7
        if ctrl.get("recirc_idx") is not None:
            recirc = min(0.7, max(0.0, self._native(cont[ctrl["recirc_idx"]], 0.0, 1.0)))
        t_mix = recirc * t_ret + (1.0 - recirc) * oat
        sat = self._native(cont[ctrl["temp_idx"]], SAT_MIN_K, SAT_MAX_K)
        t_s = sat if t_mix > sat else t_mix
        if t_s >= MAX_DISCHARGE_K:
            return []
        out = []
        unit_flow = VAV_MAX_FLOW_M3S * np.sqrt(pressure_pa / VAV_DESIGN_PRESSURE_PA)
        for vav_id, _, acts in ctrl["zones"]:
            u = self._zone_u.get(vav_id)
            d_idx = acts.get("supply_air_damper_percentage_command")
            r_idx = acts.get("reheat_valve_percentage_command")
            if u is None or u >= 0.0 or d_idx is None or r_idx is None:
                continue
            valve = (float(cont[r_idx]) + 1.0) * 0.5
            c_w = WATER_CP_RHO * valve * REHEAT_KV_MAX * np.sqrt(dp) / 3600.0
            flow = c_w * (tw - t_s) / (MAX_DISCHARGE_K - t_s) / AIR_CP_RHO
            out.append((d_idx, flow / unit_flow, flow, u))
        return out

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active or self._tw_idx is None or self._dp_idx is None:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            if not disc[ctrl["run_discrete_idx"]] or ctrl["pressure_idx"] is None:
                continue
            p_pa = max(200.0, self._native(cont[ctrl["pressure_idx"]], 0.0, 2000.0))
            targets = self._coil_targets(obs, cont, ctrl, p_pa)
            if not targets:
                continue
            if self.HEAT_PRESSURE_OPT:
                us = [self._zone_u[v] for v, _, _ in ctrl["zones"] if v in self._zone_u]
                needed = [f for _, _, f, u in targets if u <= self.SAT_HEAT_U]
                if us and float(np.mean(us)) < 0.0 and needed:
                    p_opt = VAV_DESIGN_PRESSURE_PA * (max(needed) / VAV_MAX_FLOW_M3S) ** 2
                    p_new = float(np.clip(p_opt, 200.0, 2000.0))
                    if p_new > p_pa:
                        p_pa = p_new
                        cont[ctrl["pressure_idx"]] = np.float32(p_pa / 1000.0 - 1.0)
                        targets = self._coil_targets(obs, cont, ctrl, p_pa)
            if self.HEAT_CAP:
                for d_idx, d_opt, _, _ in targets:
                    d_now = (float(cont[d_idx]) + 1.0) * 0.5
                    d_new = min(d_now, max(self.MIN_DAMPER, d_opt))
                    cont[d_idx] = np.float32(2.0 * d_new - 1.0)
        return action


class DSA_HeatOptP(DSA_HeatOpt):
    HEAT_PRESSURE_OPT = True
    KEY = "dsa_heatopt_p"


class DSA_HeatOpt05(DSA_HeatOpt):
    HEAT_DAMPER_GAIN = 0.5
    KEY = "dsa_heatopt05"


class DSA_HeatOptP05(DSA_HeatOptP):
    HEAT_DAMPER_GAIN = 0.5
    KEY = "dsa_heatopt_p05"


class DSA_HOP_Econ(DSA_HeatOptP):
    """Economizer for every AHU that is cooling in PI hours.

    Forced-on AHUs keep recirculation at its maximum (the organizer economizer only
    runs inside the PID branch), so the chiller does all the cooling even when the
    outside air is colder than the return air. In this simulator the recirculation
    command does not change airflow, so outside air costs no fan energy: draw enough
    of it to bring the mix down to the supply-air target, or all of it when the
    outside air lies between the target and the return air. Heating-mode AHUs keep
    maximum recirculation.
    """
    KEY = "dsa_hop_econ"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            r_idx, oat_idx = ctrl.get("recirc_idx"), ctrl.get("oat_idx")
            if r_idx is None or oat_idx is None or not disc[ctrl["run_discrete_idx"]]:
                continue
            if float(cont[ctrl["temp_idx"]]) >= 0.0:      # heating mode: keep return air
                continue
            target = self._native(cont[ctrl["temp_idx"]], SAT_MIN_K, SAT_MAX_K)
            inside = float(np.mean([self._denormalize_zone_temp(obs[j]) for j in ctrl["zone_obs_indices"]]))
            oat = _outside_kelvin(self, obs[oat_idx])
            if oat >= inside or inside <= target:
                continue
            f_out = float(np.clip((inside - target) / (inside - oat), 0.3, 1.0))
            cont[r_idx] = np.float32(2.0 * (1.0 - f_out) - 1.0)
        return action


class DSA_HOP_NightP(DSA_HeatOptP):
    """Outside PI hours, heating AHUs use the HeatOptP airflow model too.

    The organizer PID sets static pressure proportional to |u|, so the colder the
    building the more 30%-outdoor-air flow it pushes through coils whose water the
    night reset may have cooled. Here a heating-mode AHU (SAT command > 0) runs at the
    200 Pa floor unless a zone's valve is saturated, in which case the pressure is set
    (up or down) to that zone's optimal airflow; heating dampers are capped at d*.
    Heating demand comes from the reheat valve commands, as no zone PI runs at night.
    """
    KEY = "dsa_hop_nightp"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if self._pi_active or self._tw_idx is None or self._dp_idx is None:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        saved = self._zone_u
        try:
            for ctrl in self.ahu_controllers:
                p_idx = ctrl["pressure_idx"]
                if p_idx is None or not disc[ctrl["run_discrete_idx"]] or float(cont[ctrl["temp_idx"]]) <= 0.0:
                    continue
                self._zone_u = {}
                for vav_id, _, acts in ctrl["zones"]:
                    r_idx = acts.get("reheat_valve_percentage_command")
                    if r_idx is not None:
                        valve = (float(cont[r_idx]) + 1.0) * 0.5
                        if valve > 0.01:
                            self._zone_u[vav_id] = -valve
                if not self._zone_u:
                    continue
                p_pa = 200.0
                targets = self._coil_targets(obs, cont, ctrl, p_pa)
                needed = [f for _, _, f, u in targets if u <= self.SAT_HEAT_U]
                if needed:
                    p_pa = float(np.clip(VAV_DESIGN_PRESSURE_PA * (max(needed) / VAV_MAX_FLOW_M3S) ** 2,
                                         200.0, 2000.0))
                cont[p_idx] = np.float32(p_pa / 1000.0 - 1.0)
                for d_idx, d_opt, _, _ in self._coil_targets(obs, cont, ctrl, p_pa):
                    d_now = (float(cont[d_idx]) + 1.0) * 0.5
                    cont[d_idx] = np.float32(2.0 * min(d_now, max(self.MIN_DAMPER, d_opt)) - 1.0)
        finally:
            self._zone_u = saved
        return action


class DSA_HOP_Hold24(DSA_HeatOptP):
    """Cooling-run hold cut from 24 h to 2 h (it kept AHUs cooling through the night)."""
    HOLD_STEPS = 24
    KEY = "dsa_hop_hold24"


class DSA_HOP_PBC(DSA_PBoostCool, DSA_HeatOptP):
    """HeatOptP plus the cooling-saturation pressure boost (fixed Phoenix July comfort)."""
    KEY = "dsa_hop_pbc"


class DSA_PRE_ND3(DSA_HOP_Econ):
    """Shallower night heating setback (3 K instead of 5 K): less to recover each morning."""
    NIGHT_HEAT_DROP_K = 3.0
    KEY = "dsa_pre_nd3"


class DSA_PRE_ND7(DSA_HOP_Econ):
    """Deeper night heating setback (7 K), prestart allowed up to 8 h."""
    NIGHT_HEAT_DROP_K = 7.0
    LEAD_MAX_H = 8.0
    KEY = "dsa_pre_nd7"


class DSA_PRE_WaterPre(DSA_HOP_Econ):
    """During the morning prestart (PI hours before occupancy) command the hot-water
    loop to its maximum temperature and pump pressure straight away.

    The night water reset leaves the tank near 310 K, and it only climbs 0.5 K/min,
    so for the first ~80 min of a recovery the coils cannot reach their 35 C
    discharge and the forced AHUs mostly move cold outdoor air.
    """
    KEY = "dsa_pre_waterpre"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if self._pi_active and self._hour_frac(obs) < self.morning_start_hour:
            cont = action["continuous_action"]
            if self.water_temp_idx is not None:
                cont[self.water_temp_idx] = np.float32(1.0)
            if self.water_pressure_idx is not None:
                cont[self.water_pressure_idx] = np.float32(1.0)
        return action


class DSA_PRE_Learn(DSA_HOP_Econ):
    """Optimal start with a learned recovery rate (lazy variant from offhours.py)."""
    LEARN_RATE = True
    RECOVERY_K_PER_H = 2.0
    RECOVERED_K = 1.0
    RATE_DOWN = 0.75
    KEY = "dsa_pre_learn"


class DSA_PRE_ND7X(DSA_PRE_ND7):
    """ND7 with a prestart that may begin the evening before (or Sunday for Monday).

    OffHoursPolicy latches its prestart per calendar day, so it can only start at
    00:00 of the work day and the lead is silently capped at 6 h whatever LEAD_MAX_H
    says. Here the schedule counts hours to the next weekday morning start across
    midnight and weekends, and starts the work-hours mode once that is within the
    adaptive lead (0.5 h + worst comfort shortfall / RECOVERY_K_PER_H).
    """
    LEAD_MAX_H = 10.0
    KEY = "dsa_pre_nd7x"

    def _hours_to_next_start(self, day, hour):
        """(weekday index of the next morning start not yet over, hours until it)."""
        if day < 5 and hour < self.evening_start_hour:
            return day, self.morning_start_hour - hour      # <= 0 during work hours
        nxt, t = (day + 1) % 7, 24.0 - hour + self.morning_start_hour
        while nxt >= 5:
            nxt, t = (nxt + 1) % 7, t + 24.0
        return nxt, t

    def _update_schedule(self, obs):
        _, day = self._get_hour_and_day(obs)
        hour = self._hour_frac(obs)
        target, t_to = self._hours_to_next_start(day, hour)
        if self._latched_day != target and t_to <= self._lead_hours(obs):
            self._latched_day = target
        self._pi_now = self._latched_day == target


class DSA_PRE_ND10X(DSA_PRE_ND7X):
    NIGHT_HEAT_DROP_K = 10.0
    LEAD_MAX_H = 12.0
    KEY = "dsa_pre_nd10x"


class DSA_PRE_ND14X(DSA_PRE_ND7X):
    NIGHT_HEAT_DROP_K = 14.0
    LEAD_MAX_H = 14.0
    KEY = "dsa_pre_nd14x"


class DSA_PRE_ND10(DSA_PRE_ND7):
    """10 K night heating drop, prestart still latched per day (starts no earlier than 00:00).

    Screening showed the cross-midnight prestart (ND7X/ND10X/ND14X) buys morning comfort
    with more energy than it saves, so the effective 6 h cap is kept.
    """
    NIGHT_HEAT_DROP_K = 10.0
    KEY = "dsa_pre_nd10"


class DSA_PRE_ND7_R3(DSA_PRE_ND7):
    """ND7 with a faster assumed recovery (3 K/h): shorter prestart."""
    RECOVERY_K_PER_H = 3.0
    KEY = "dsa_pre_nd7_r3"


class DSA_PRE_ND10_R3(DSA_PRE_ND10):
    RECOVERY_K_PER_H = 3.0
    KEY = "dsa_pre_nd10_r3"


class DSA_PRE_ND14(DSA_PRE_ND10):
    NIGHT_HEAT_DROP_K = 14.0
    KEY = "dsa_pre_nd14"


class DSA_PRE_ND20(DSA_PRE_ND10):
    """Night heating essentially off (eco floor 269 K); recovery still capped at 6 h."""
    NIGHT_HEAT_DROP_K = 20.0
    KEY = "dsa_pre_nd20"


class DSA_HOT_Sat12(DSA_PRE_ND10):
    """Cooling supply air at 12 C (COLD_SAT -1.0) instead of 15 C.

    Chiller load is flow * (T_mix - SAT) with 30% outside air in the mix, so in hot
    climates a large share of it is ventilation load, which scales with airflow.
    Colder supply air delivers the same zone cooling with ~30% less air.
    """
    COLD_SAT = -1.0
    KEY = "dsa_hot_sat12"


class DSA_HOT_Shift05(DSA_PRE_ND10):
    """When cooling, regulate zones to the band centre + COOL_SHIFT_K (1 K below the top).

    Only zones above the centre are shifted, so the heating-side deadband of
    DSA_DeadbandHeat is unchanged. A 1 K shift (DSA_Shift1) cost Phoenix comfort.
    """
    COOL_SHIFT_K = 0.5
    KEY = "dsa_hot_shift05"

    def _zone_target(self, obs, lo, hi):
        centre = 0.5 * (lo + hi)
        if self._cur_temp > centre:
            return centre + min(self.COOL_SHIFT_K, 0.4 * (hi - lo))
        return super()._zone_target(obs, lo, hi)


class DSA_HOT_NightHi6(DSA_PRE_ND10):
    """Off-hours cooling ceiling raised 6 K above the eco band (304 K) instead of 3 K."""
    SETBACK_HI_K = 6.0
    KEY = "dsa_hot_nighthi6"


class DSA_HOT_PBC(DSA_PBoostCool, DSA_PRE_ND10):
    """ND10 plus the cooling-saturation static pressure boost."""
    KEY = "dsa_hot_pbc"


class DSA_HOT_Sat12Hot(DSA_PRE_ND10):
    """Cooling supply air at 12 C only when the outside air is warmer than the return air.

    DSA_HOT_Sat12 (always 12 C) cut hot-climate loss ~15% but cost 7% on a winter
    Atlanta week: when the outside air is cooler than the return air, airflow brings
    free cooling through the economizer and colder supply air only wastes it. Here a
    cooling-mode AHU drops to the 12 C floor only while its ventilation air is a load
    (OAT > mean zone temperature); otherwise it keeps the 15 C demand-SAT setting, and
    the economizer (which only acts when OAT < return air) is unaffected.
    """
    HOT_SAT = -1.0
    HOT_MARGIN_K = 0.0     # switch to 12 C once OAT > mean zone temp - HOT_MARGIN_K
    KEY = "dsa_hot_sat12hot"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            oat_idx = ctrl.get("oat_idx")
            if oat_idx is None or not disc[ctrl["run_discrete_idx"]]:
                continue
            if float(cont[ctrl["temp_idx"]]) > self.COLD_SAT + 1e-6:   # not in cooling mode
                continue
            inside = float(np.mean([self._denormalize_zone_temp(obs[j]) for j in ctrl["zone_obs_indices"]]))
            if _outside_kelvin(self, obs[oat_idx]) > inside - self.HOT_MARGIN_K:
                cont[ctrl["temp_idx"]] = np.float32(self.HOT_SAT)
        return action


class DSA_HOT_Sat12Hot_N6(DSA_HOT_Sat12Hot):
    SETBACK_HI_K = 6.0
    KEY = "dsa_hot_sat12hot_n6"


class DSA_MILD_SatWarm(DSA_HOT_Sat12Hot_N6):
    """In the economizer regime, reset the cooling supply air between 15 and 19 C.

    Mild weather with large internal gains: the AHU cools (economizer air is free)
    while perimeter and small zones reheat the same cold air (0501/denver_apr: 63 kW
    of reheat in a building that needs to reject 129 kW). When the outside air is
    cooler than the return air, the cooling setpoint follows the hungriest zone:
    19 C when no zone asks for more than SAT_U_LO of cooling effort, 15 C at SAT_U_HI.
    Cooling zones make up with more (nearly free) air; the economizer mix is
    recomputed for the new target. Hot weather keeps the 12 C rule of Sat12Hot.
    """
    SAT_U_LO, SAT_U_HI = 0.2, 0.6
    SAT_WARM_K = 292.15
    KEY = "dsa_mild_satwarm"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        cold_k = self._native(self.COLD_SAT, SAT_MIN_K, SAT_MAX_K)
        for ctrl in self.ahu_controllers:
            oat_idx = ctrl.get("oat_idx")
            if oat_idx is None or not disc[ctrl["run_discrete_idx"]]:
                continue
            if abs(float(cont[ctrl["temp_idx"]]) - self.COLD_SAT) > 1e-6:   # not mild cooling mode
                continue
            inside = float(np.mean([self._denormalize_zone_temp(obs[j]) for j in ctrl["zone_obs_indices"]]))
            oat = _outside_kelvin(self, obs[oat_idx])
            if oat >= inside:
                continue
            us = [self._zone_u[v] for v, _, _ in ctrl["zones"] if v in self._zone_u]
            if not us:
                continue
            frac = float(np.clip((max(us) - self.SAT_U_LO) / (self.SAT_U_HI - self.SAT_U_LO), 0.0, 1.0))
            target = self.SAT_WARM_K - frac * (self.SAT_WARM_K - cold_k)
            cont[ctrl["temp_idx"]] = np.float32((target - SAT_MIN_K) / (SAT_MAX_K - SAT_MIN_K) * 2.0 - 1.0)
            r_idx = ctrl.get("recirc_idx")
            if r_idx is not None and inside > target:
                f_out = float(np.clip((inside - target) / (inside - oat), 0.3, 1.0))
                cont[r_idx] = np.float32(2.0 * (1.0 - f_out) - 1.0)
        return action


class DSA_MILD_HeatSeq(DSA_HOT_Sat12Hot_N6):
    """Dual-maximum reheat sequence for zones that need heat in PI hours (ASHRAE G36).

    The zone PI opened damper and valve together (damper = floor + |u|), so a mildly
    cold zone under a cooling AHU took in more cold supply air and reheated it. Here
    the valve opens first (fully at |u| = HEAT_VALVE_U) with the damper at its floor;
    airflow rises only beyond that. The HeatOpt d* cap still applies afterwards.
    """
    HEAT_VALVE_U = 0.5
    KEY = "dsa_mild_heatseq"

    def _command_zones(self, continuous, zones, obs, low, high):
        super()._command_zones(continuous, zones, obs, low, high)
        if not self._pi_active:
            return
        for vav_id, _, acts in zones:
            u = self._zone_u.get(vav_id)
            if u is None or u >= 0.0:
                continue
            d_idx = acts.get("supply_air_damper_percentage_command")
            r_idx = acts.get("reheat_valve_percentage_command")
            if d_idx is None or r_idx is None:
                continue
            e = -u
            valve = min(1.0, e / self.HEAT_VALVE_U)
            air = float(np.clip((e - self.HEAT_VALVE_U) / (1.0 - self.HEAT_VALVE_U), 0.0, 1.0))
            damper = self.MIN_DAMPER + (1.0 - self.MIN_DAMPER) * air * self.HEAT_DAMPER_GAIN
            continuous[r_idx] = np.float32(2.0 * valve - 1.0)
            continuous[d_idx] = np.float32(2.0 * damper - 1.0)


class DSA_MILD_Both(DSA_MILD_HeatSeq, DSA_MILD_SatWarm):
    KEY = "dsa_mild_both"


class DSA_MILD_SatWarm21(DSA_MILD_SatWarm):
    SAT_WARM_K = 294.15
    KEY = "dsa_mild_satwarm21"


class DSA_MILD_SatWarmLo(DSA_MILD_SatWarm):
    """Stay warm longer: full 15 C only when some zone's cooling effort reaches 0.8."""
    SAT_U_LO, SAT_U_HI = 0.3, 0.8
    KEY = "dsa_mild_satwarmlo"


class DSA_HOL_0630(DSA_HOT_Sat12Hot_N6):
    """End the work-hours mode for the day once the building reports no occupants.

    US federal holidays are weekends to the occupancy model and the tariff but not to
    the comfort schedule, so the policy used to condition an empty building all day
    (23 of the 30 training strips contain one). Occupants are always present by
    06:15 on a real work day, so an empty building at OCC_GATE_AFTER_H means a
    holiday; later in the day the same gate stops conditioning once everyone has
    left. No occupants means no comfort charge, so this is energy only.
    """
    OCC_GATE = True
    OCC_GATE_AFTER_H = 6.5
    KEY = "dsa_hol_0630"


class DSA_HOL_1600(DSA_HOT_Sat12Hot_N6):
    """Diagnostic: the same gate from 16:00 only (empty late afternoons, no holidays)."""
    OCC_GATE = True
    OCC_GATE_AFTER_H = 16.0
    KEY = "dsa_hol_1600"


class DSA_HOL2_0630(DSA_HOL_0630):
    """DSA_HOL_0630 with the occupancy gate reset at every day change.

    OffHoursPolicy stores the gated day as a weekday index (0-6) and never clears it,
    so a gated holiday Monday also blocked every later Monday (no prestart, no work
    mode): DSA_HOL_0630/1600 lost 40-150% on holiday scenarios. The gate now only
    lasts for the calendar day it fired on.
    """
    KEY = "dsa_hol2_0630"

    def _update_schedule(self, obs):
        _, day = self._get_hour_and_day(obs)
        if day != getattr(self, "_sched_day", None):
            self._sched_day = day
            self._gated_day = None
        super()._update_schedule(obs)


class DSA_CAP_TR(DSA_HOT_Sat12Hot_N6):
    """Trim-and-respond static pressure for cooling AHUs (ASHRAE G36 style).

    At the 200 Pa floor a VAV gets at most 0.63 m^3/s (~9 kW of cooling) whatever
    the zone's size, so big zones run warm in hot weather (0504/atlanta_may,
    Phoenix July). DSA_PBoostCool jumped straight to a fixed pressure map and paid
    fan and ventilation energy on every other zone. Here each cooling AHU keeps a
    pressure that rises by TR_UP_PA per step while one of its zones is saturated
    (PI effort >= TR_SAT_U) and falls by TR_DN_PA once none is above TR_REL_U.
    """
    TR_UP_PA, TR_DN_PA = 50.0, 25.0
    TR_SAT_U, TR_REL_U = 0.95, 0.8
    KEY = "dsa_cap_tr"

    def __init__(self, building_meta_data, action_spec):
        super().__init__(building_meta_data, action_spec)
        self._tr_p = [200.0] * len(self.ahu_controllers)

    def _base_action(self, obs):
        action = super()._base_action(obs)
        cont, disc = action["continuous_action"], action["discrete_action"]
        for i, ctrl in enumerate(self.ahu_controllers):
            p_idx = ctrl["pressure_idx"]
            cooling = (self._pi_active and p_idx is not None and disc[ctrl["run_discrete_idx"]]
                       and float(cont[ctrl["temp_idx"]]) < 0.0)
            if not cooling:
                self._tr_p[i] = 200.0
                continue
            us = [self._zone_u[v] for v, _, _ in ctrl["zones"] if v in self._zone_u]
            u_max = max(us) if us else 0.0
            if u_max >= self.TR_SAT_U:
                self._tr_p[i] = min(2000.0, self._tr_p[i] + self.TR_UP_PA)
            elif u_max < self.TR_REL_U:
                self._tr_p[i] = max(200.0, self._tr_p[i] - self.TR_DN_PA)
            cont[p_idx] = np.float32(max(float(cont[p_idx]), self._tr_p[i] / 1000.0 - 1.0))
        return action


class DSA_CAP_TRFast(DSA_CAP_TR):
    TR_UP_PA = 100.0
    KEY = "dsa_cap_trfast"


class DSA_CAP_PBC(DSA_PBoostCool, DSA_HOT_Sat12Hot_N6):
    KEY = "dsa_cap_pbc"

"""One-parameter-at-a-time tuning variants around the current best policy.

Each class differs from DSA_HOT_Sat12Hot_N6 (LB 0.01228) in exactly the attributes
passed to _variant, so a screen isolates that parameter's effect.
"""

BASE = DSA_HOT_Sat12Hot_N6


def _variant(name, **attrs):
    cls = type(name, (BASE,), {**attrs, "KEY": name.lower(), "__doc__": f"BASE with {attrs}"})
    globals()[name] = cls
    return cls


_variant("T_PI_SOFT", KP=0.05, KI=0.0025)
_variant("T_PI_STIFF", KP=0.10, KI=0.005)
_variant("T_KI_HI", KI=0.007)
_variant("T_SAT14", COLD_SAT=-0.8)
_variant("T_SAT16", COLD_SAT=-0.6)
_variant("T_HOT_M2", HOT_MARGIN_K=2.0)
_variant("T_NIGHTHI8", SETBACK_HI_K=8.0)
_variant("T_DB03", DEADBAND_K=0.3)
_variant("T_DB08", DEADBAND_K=0.8)
_variant("T_FORCE015", FORCE_U_MIN=0.15)
_variant("T_HOLD72", HOLD_STEPS=72)
_variant("T_REC23", RECOVERY_K_PER_H=2.3)

# Round 2: push the two monotone trends and combine the round-1 winners.
_variant("T_DB015", DEADBAND_K=0.15)
_variant("T_NIGHTHI10", SETBACK_HI_K=10.0)
_variant("T_SAT17", COLD_SAT=-0.5)
_variant("T_COMBO", DEADBAND_K=0.3, COLD_SAT=-0.6, SETBACK_HI_K=8.0, HOLD_STEPS=72)
_variant("T_COMBO_B", DEADBAND_K=0.15, COLD_SAT=-0.6, SETBACK_HI_K=8.0, HOLD_STEPS=72)

# Round 3: SAT16 helps winter (economizer) weeks but costs capacity in warm-mild weeks
# (atlanta_may +1.2%, SAT17 +3.3%), so only use the warmer cooling air when the
# outside air is cold enough for the economizer to supply it for free.
import numpy as np  # noqa: E402



class T_COMBO_C(BASE):
    """DB 0.15 K + night cooling float +8 K + 6 h cooling hold (no SAT change)."""
    DEADBAND_K = 0.15
    SETBACK_HI_K = 8.0
    HOLD_STEPS = 72
    KEY = "t_combo_c"


class T_COMBO_D(T_COMBO_C):
    """T_COMBO_C plus a 16 C cooling supply air only while OAT < COLD_OAT_K (12 C).

    In that regime the economizer can mix the supply air down for free, so warmer
    air only means more (free) airflow and less reheat of perimeter zones.
    """
    WARM_COLD_SAT = -0.6
    COLD_OAT_K = 285.15
    KEY = "t_combo_d"

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if not self._pi_active:
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        for ctrl in self.ahu_controllers:
            oat_idx = ctrl.get("oat_idx")
            if oat_idx is None or not disc[ctrl["run_discrete_idx"]]:
                continue
            if abs(float(cont[ctrl["temp_idx"]]) - self.COLD_SAT) > 1e-6:
                continue
            oat = _outside_kelvin(self, obs[oat_idx])
            if oat >= self.COLD_OAT_K:
                continue
            cont[ctrl["temp_idx"]] = np.float32(self.WARM_COLD_SAT)
            target = SAT_MIN_K + (self.WARM_COLD_SAT + 1.0) * 0.5 * (SAT_MAX_K - SAT_MIN_K)
            inside = float(np.mean([self._denormalize_zone_temp(obs[j]) for j in ctrl["zone_obs_indices"]]))
            r_idx = ctrl.get("recirc_idx")
            if r_idx is not None and inside > target:
                f_out = float(np.clip((inside - target) / (inside - oat), 0.3, 1.0))
                cont[r_idx] = np.float32(2.0 * (1.0 - f_out) - 1.0)
        return action

"""Extra switches on top of T_COMBO_D."""
import numpy as np

class V(T_COMBO_D):
    """T_COMBO_D + switchable extras."""
    COOL_FLOAT_K = None     # if set: zones above centre float up to hi - COOL_FLOAT_K
    GATE = False            # end work mode for the day once building empty after GATE_AFTER_H
    GATE_AFTER_H = 6.5
    GATE_MIN_HOLD_STEPS = 0
    KEY = "v"

    def _zone_target(self, obs, lo, hi):
        t = super()._zone_target(obs, lo, hi)
        if self.COOL_FLOAT_K is not None:
            centre = 0.5 * (lo + hi)
            if self._cur_temp > centre:
                return float(np.clip(self._cur_temp, centre, hi - self.COOL_FLOAT_K))
        return t

    def _update_schedule(self, obs):
        _, day = self._get_hour_and_day(obs)
        if day != getattr(self, "_sched_day", None):
            self._sched_day = day
            self._gated_day = None
        if not self.GATE:
            self.OCC_GATE = False
        else:
            self.OCC_GATE = True
            self.OCC_GATE_AFTER_H = self.GATE_AFTER_H
        super()._update_schedule(obs)


class V2(V):
    """V + anti-windup band and optional max hot water during morning prestart."""
    INT_ERR_MAX = None      # integrate zone PI error only while |err| < this (K)
    PRE_WATER_MAX = False
    KEY = "v2"

    def _command_zones(self, continuous, zones, obs, low, high):
        if self.INT_ERR_MAX is None or not self._pi_active:
            return super()._command_zones(continuous, zones, obs, low, high)
        saved = dict(self._zone_integral)
        super()._command_zones(continuous, zones, obs, low, high)
        # Undo integration for zones far from target (large errors are handled by P action).
        lo_c, hi_c = self.comfort_temp_window
        for vav_id, obs_idx, action_indices in zones:
            if not action_indices or vav_id not in saved:
                continue
            lo, hi = self._zone_band(obs, vav_id, lo_c, hi_c)
            if hi - lo > (hi_c - lo_c) + 1e-6:
                lo, hi = lo_c, hi_c
            t = self._denormalize_zone_temp(obs[obs_idx])
            err = t - self._zone_target(obs, lo, hi)
            if abs(err) >= self.INT_ERR_MAX:
                self._zone_integral[vav_id] = saved[vav_id]

    def _base_action(self, obs):
        action = super()._base_action(obs)
        if self.PRE_WATER_MAX and self._pi_active and self._hour_frac(obs) < self.morning_start_hour:
            cont = action["continuous_action"]
            if self.water_temp_idx is not None and cont[self.water_temp_idx] > -1.0 + 1e-6:
                cont[self.water_temp_idx] = np.float32(1.0)
        return action


class V3(V2):
    """V2 with separate assumed recovery rates for heating and cooling shortfalls."""
    HEAT_RATE = 4.0
    COOL_RATE = 4.0
    KEY = "v3"

    def _lead_hours(self, obs):
        if not self.ADAPTIVE_PRESTART:
            return float(self.PRESTART_H)
        lo_c, hi_c = self.comfort_temp_window
        temps = np.array([self._denormalize_zone_temp(obs[j]) for j in self._zone_obs])
        heat = float(np.max(np.maximum(0.0, lo_c - temps), initial=0.0))
        cool = float(np.max(np.maximum(0.0, temps - hi_c), initial=0.0))
        lead = self.LEAD_BASE_H + max(heat / self.HEAT_RATE, cool / self.COOL_RATE)
        return float(np.clip(lead, self.LEAD_MIN_H, self.LEAD_MAX_H))


class C42(V3):
    HEAT_RATE = 4.0
    COOL_RATE = 2.0
    COOL_FLOAT_K = 0.8


class C42F10(C42):
    COOL_FLOAT_K = 1.0


class C62(C42):
    HEAT_RATE = 6.0
