# NeurIPS 2026 Smart Buildings (Kaggle) - archive

Kept here because no dedicated GitHub repo exists for this competition yet and the scheduled cloud run cannot create
one (GitHub REST API is blocked from the session; plain git push works). Move to its own repo when one is created.

Metric: lower is better. LB 2026-10-28 00:50 UTC top: 0.00514 / 0.00521 / 0.00530.

| sub | kernel | idea | status |
|---|---|---|---|
| sb01 | sb01-tcombod-baseline | fork of public T_COMBO_D (minhduonq; zone-PI + demand SAT) | **0.01204** |
| sb02 | sb-combo-c42 | T_COMBO_D + heating warm-up 4K/h, cooling 2K/h, occupied cooling float 0.8K below upper band (local dev -6.1%) | **0.01195** (best) |
| sb03 | sb-combo-c42-f10 | C42 with cooling float 1.0K (conservative) | pending |
| sb04 | sb-combo-c62 | C42 with heating warm-up 6K/h (dev -6.4%, more comfort risk) | pending |
| - | sb-combo-r4 | intermediate variant, not submitted | - |
| sb05 | sb05-c42-holgate | C42 + occupancy gate from 06:30 (holidays: comfort schedule still says work day but nobody comes; also stops after everyone left). Local fairbanks_1 3 days -6.9% | submitted 10-28 06:28, pending |
| sb06 | sb06-c42f10-holgate | sb03 cooling float 1.0 K + sb05 occupancy gate | submitted 10-28 07:13, pending |

All CPU only. Next: once sb01-sb04 score, pick the warm-up rate / float direction from the deltas before tuning further.

## 2026-10-28 06:00 UTC - diagnosis (hourly run)
LB 10-28 05:45: top 0.00514 / 0.00521 / 0.00530 / 0.00550; we are at 0.01195 (rank ~133 / 407). Local dev said
sb02 = -6.1% vs sb01, the LB gave -0.75%: the 3-day dev screen does not predict the LB.

4-day local breakdown of C42 (sb02) with the official reward (`harness.py` in the session, components logged):

| scenario | score | comfort (0.6 x regret) | energy (0.2x) | carbon (0.2x) | main load |
|---|---:|---:|---:|---:|---|
| b1 / fairbanks_1 | 0.0393 | 0.0017 | 0.0110 | 0.0265 | gas 130 kW mean (boiler for VAV reheat) |
| b1 / phoenix_5 | 0.0157 | 0.0018 | 0.0113 | 0.0026 | AC 22 kW mean, mostly occupied hours |

So >= 89% of the cost is energy + carbon; comfort tuning can not reach 0.005. Top teams must cut energy ~2x.
Physics notes (from the simulator source): AHUs only cool; all heat is VAV reheat via the boiler; recirculation
capped at 0.7 so a running AHU always brings >= 30% outdoor air; dampers floored at 10%; reward regret is normalised
by the occupants present, so the first arrivals (06:00-07:00, random per occupant) weigh as much as a full floor.
Fairbanks prestart (04:00-06:00) burns ~240 kW of gas while nobody is in the building.

`sb-lab/`: Kaggle CPU kernel `gwey1025/sb-lab-calib` - full 30-day runs of T_COMBO_D, C42, C62 on all 30 training
scenarios (4 processes), writes `lab_results.json` with the comfort/energy/carbon/gas/AC split per scenario.
Purpose: calibrate full-length local scores against the LB (sb01/sb02/sb04) before spending more SB slots.

## 2026-10-28 07:00 UTC - heating-side physics experiments (hourly run, local, CPU)
`sb-lab/bb_experiments.py`, building_train_1/fairbanks_1, first 5 days (1440 steps), official reward:

| policy | score | comfort | energy | carbon | gas kW | pump kW |
|---|---:|---:|---:|---:|---:|---:|
| C42 (sb02) | **0.0486** | 0.0026 | 0.0135 | 0.0326 | 159 | 1.6 |
| BB: AHU on/off hysteresis, damper floor, valve full, max water | 0.3651 | 0.3390 | 0.0091 | 0.0171 | 81 | 6.3 |
| BB2: C42 + valve full on heating zones + max water | 0.0572 | 0.0025 | 0.0170 | 0.0376 | 182 | 5.2 |
| BB2g: BB2 with damper gain 0.5 | 0.0611 | 0.0075 | 0.0170 | 0.0367 | 177 | 5.3 |

Negative results: (1) floor-flow heat (damper 10%, 35 C discharge cap) cannot carry fairbanks zones - on/off cycling at
the floor halves gas but loses comfort 130x; (2) fully open reheat valves raise gas and pump power - the PID hot-water
reset in C42 is already better than max water. Ventilation is ~50-60% of winter gas (OA 1.8-3.4 m3/s at -30 C), so the
remaining lever is AHU on-time/airflow when heat demand is low, not coil temperature.
sb06 = C42-F10 (sb03, best 0.01188) + occupancy gate (sb05) pushed and submitted (10-28 SB slot 2/5).
