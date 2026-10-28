# Run log (hourly scheduled task "Koushik-one way", fires :42 every hour; runs can overlap)

Before submitting anything: `kaggle competitions submissions <comp>` and read this file, so two
overlapping runs never spend the same slot or submit the same thing twice. Append one line per action.

- 2026-10-27 19:49 UTC  quantum v7 submitted (21.882 public)
- 2026-10-27 22:50 UTC  quantum v8 submitted (somejoint 21.976 output). Smart Buildings left to the run that is already working on it (sb-combo-r4/c42 kernels at 22:30/22:48).
- 2026-10-28 00:02 UTC  v8 scored 22.00949 public (best). Checked newest public outputs (manwithacat 'The Real 150K' = v8 bytes); nothing ahead to submit. No quantum slot used.
- 2026-10-28 00:45 UTC  quantum v9 submitted (heliosli J5 chem 3.4934e8, chem verifier PASS locally; expect ~22.13). 10-28 quantum slot 1/5.
- 2026-10-28 00:55 UTC  Smart Buildings kernels sb01/r4/c42/c42-f10/c62 archived under smart-buildings/; sb01-sb04 still pending, no SB slot used this run.
- 2026-10-28 02:05 UTC  v9 scored 22.12908. quantum v10 submitted (somejoint 897q DQI + v9 invsqrt/chem, DQI verifier PASS locally x2 salts; expect ~22.34). 10-28 quantum slot 2/5. LB top 25.629/25.052/24.159.
- 2026-10-28 02:55 UTC  v10 scored 22.27620 (best; rank ~34). Newest public heliosli 'dataset now public' = v9 composition (22.129) - nothing ahead to submit; no quantum slot used. LB top 25.629/25.052/24.159/24.079.
- 2026-10-28 04:04 UTC  quantum v11 submitted (busyaprime invsqrt 63q v2 102,664, verifier PASS locally; DQI/chem = v10). Expect ~22.34. 10-28 quantum slot 3/5. kawh1111 'harvest 210' checked: older mrmeows qcc-1375 members, not ahead.
- 2026-10-28 05:05 UTC  v11 scored 22.33981 (best, = projection). Own research: invsqrt rotation-angle LP (research/invsqrt-angle-lp) - published angles already LP-optimal, no rotation droppable; no new circuit, no quantum slot used (2 left for 10-28). NTL s15-s17 pending, 2 NTL slots held per handoff. SB sb02-sb04 pending.
- 2026-10-28 05:58 UTC  quantum v12 submitted (v11 invsqrt/DQI + somejoint '22.44 Local GM' R8/B143 C62 chemistry 3.47715e8, chem verifier PASS locally; expect ~22.375). 10-28 quantum slot 4/5. LB top 26.141/25.052/24.159. SB: sb02 scored 0.01195 (best, sb01 0.01204); sb03/sb04 pending; local sim set up - C42 4-day breakdown: fairbanks cost is 94% energy+carbon (gas 130 kW mean), phoenix 89% energy (AC), comfort <0.002 - top LB 0.00514 needs a large energy cut, not comfort tuning.
- 2026-10-28 06:04 UTC  SB: pushed Kaggle CPU kernel gwey1025/sb-lab-calib (full 30-day eval of T_COMBO_D/C42/C62 on 30 training scenarios, ~6 h) to calibrate local vs LB; no SB slot used. NTL slots still held (s15-s17 pending).
- 2026-10-28 06:28 UTC  SB sb05-c42-holgate submitted (C42 + occupancy gate for US holidays / empty afternoons; local fairbanks_1 New-Year 3-day window -6.9%). 10-28 SB slot 1/5.
- 2026-10-28 06:59 UTC  SB: local heating experiments (bang-bang / valve-full, both worse than C42, notes in smart-buildings/README.md). sb06-c42f10-holgate kernel pushed (sb03 float 1.0 + sb05 gate). Quantum v12 scored 22.37455 (best); no newer public output ahead (newest: saurabhkumar DQI width analysis = negative result, alexchilton 22.34) - 10-28 quantum slot 5/5 held. NTL s15-s17 pending, 2 slots held.
- 2026-10-28 07:12 UTC  SB sb06-c42f10-holgate v1 submitted (10-28 SB slot 2/5; 3 left). Pending.
- 2026-10-28 08:53 UTC  quantum v13 submitted (v12 + alexchilton 889q DQI 4.1478e11 from leoprovorov hybrid output; official DQI verifier PASS locally x2 salts; expect ~22.51), ref 57731187. 10-28 quantum slot 5/5 - quantum budget for 10-28 used up. NTL: s16 scored 0.614 (cut 0.08 hurts under soft-cap); s17/s18 pending, last NTL slot held. SB untouched this run (sb05/sb06 pending).
- 2026-10-28 10:05 UTC  quantum v13 scored 22.57336 (best; LB top 26.141/25.052/24.589). 10-28 quantum budget used. SB: sb07-c42f13-holgate pushed (= sb06 with cooling float 1.3 K, extrapolating 0.8->1.0 K gain); sb05/sb06 pending; sb-lab-calib still running.
