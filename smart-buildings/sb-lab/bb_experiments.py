"""Bang-bang heating on top of C42.

Physics (simulator source): AHUs only cool, all heat is VAV reheat, a running AHU
always draws >= 30% outdoor air, VAV discharge is capped at 35 C. Every second an
AHU runs in cold weather, its outdoor air must be reheated; the useful heat per
unit of airflow is largest when the reheat coil runs at the 35 C cap. So in
heating weather: run an AHU only while one of its zones is near the bottom of
the comfort band, at the damper floor with the reheat valve fully open and the
hottest water, then switch it off and let the zones coast down again.
"""
import numpy as np
import policies_local as P


class BB(P.C42):
    ON_K = 0.3          # switch AHU on when coldest zone < lo + ON_K
    OFF_K = 1.2         # switch off when every zone > lo + OFF_K
    HEAT_OAT_K = 283.15 # heating regime below this outside temperature
    COOL_GUARD_K = 0.6  # if a zone is within this of hi, defer to C42
    VALVE_ALL = False   # open the valve on every zone while on
    BB_UNOCC_ONLY = False

    def __init__(self, meta, spec):
        super().__init__(meta, spec)
        self._bb_on = [False] * len(self.ahu_controllers)

    def _oat(self, obs, ctrl):
        idx = ctrl.get("oat_idx")
        if idx is None:
            return None
        v = float(obs[idx])
        return v if v > 150.0 else v * self.outside_std + self.outside_mean

    def get_action(self, obs):
        action = super().get_action(obs)
        if not self._pi_active:
            self._bb_on = [False] * len(self.ahu_controllers)
            return action
        cont, disc = action["continuous_action"], action["discrete_action"]
        lo_c, hi_c = self.comfort_temp_window
        any_on = False
        for i, ctrl in enumerate(self.ahu_controllers):
            oat = self._oat(obs, ctrl)
            if oat is None or oat >= self.HEAT_OAT_K or not ctrl["zones"]:
                self._bb_on[i] = False
                continue
            temps = [self._denormalize_zone_temp(obs[j]) for _, j, _ in ctrl["zones"]]
            if max(temps) > hi_c - self.COOL_GUARD_K:
                self._bb_on[i] = False
                continue  # some zone needs cooling: leave C42 in charge
            need = min(temps) - lo_c
            if self._bb_on[i]:
                if need > self.OFF_K:
                    self._bb_on[i] = False
            elif need < self.ON_K:
                self._bb_on[i] = True
            on = self._bb_on[i]
            disc[ctrl["run_discrete_idx"]] = 1 if on else 0
            if ctrl.get("pressure_idx") is not None:
                cont[ctrl["pressure_idx"]] = -1.0
            if ctrl.get("recirc_idx") is not None:
                cont[ctrl["recirc_idx"]] = 1.0
            for (vav, j, acts), t in zip(ctrl["zones"], temps):
                d = acts.get("supply_air_damper_percentage_command")
                v = acts.get("reheat_valve_percentage_command")
                if d is not None:
                    cont[d] = -1.0
                if v is not None:
                    heat = on and (self.VALVE_ALL or t < lo_c + self.OFF_K)
                    cont[v] = 1.0 if heat else -1.0
            any_on = any_on or on
        if any_on and self.water_temp_idx is not None:
            cont[self.water_temp_idx] = 1.0
            if self.water_pressure_idx is not None:
                cont[self.water_pressure_idx] = 1.0
        return action


class BB_A(BB):
    ON_K = 0.2
    OFF_K = 0.8


class BB_V(BB):
    VALVE_ALL = True


class BB2(P.C42):
    """C42 with the reheat valve fully open on every heating zone in cold weather:
    heat is then metered by the damper alone, so the coil runs at the discharge cap
    at low airflow and less outdoor air is moved per joule delivered."""
    HEAT_OAT_K = 283.15
    DAMPER_GAIN = 1.0
    WATER_MAX = True

    def _bb2_oat(self, obs):
        for c in self.ahu_controllers:
            idx = c.get("oat_idx")
            if idx is not None:
                v = float(obs[idx])
                return v if v > 150.0 else v * self.outside_std + self.outside_mean
        return None

    def get_action(self, obs):
        action = super().get_action(obs)
        if not self._pi_active:
            return action
        oat = self._bb2_oat(obs)
        if oat is None or oat >= self.HEAT_OAT_K:
            return action
        cont = action["continuous_action"]
        heating = False
        for ctrl in self.ahu_controllers:
            for vav, j, acts in ctrl["zones"]:
                u = self._zone_u.get(vav)
                if u is None or u >= 0:
                    continue
                heating = True
                d = acts.get("supply_air_damper_percentage_command")
                v = acts.get("reheat_valve_percentage_command")
                if v is not None:
                    cont[v] = 1.0
                if d is not None:
                    damper = self.MIN_DAMPER + (1 - self.MIN_DAMPER) * min(1.0, abs(u) * self.DAMPER_GAIN)
                    cont[d] = 2 * damper - 1
        if heating and self.WATER_MAX and self.water_temp_idx is not None:
            cont[self.water_temp_idx] = 1.0
        return action


class BB2g(BB2):
    DAMPER_GAIN = 0.5
