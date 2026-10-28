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
