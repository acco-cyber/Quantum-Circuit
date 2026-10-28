# NeurIPS 2026 Smart Buildings (Kaggle) - archive

Kept here because no dedicated GitHub repo exists for this competition yet and the scheduled cloud run cannot create
one (GitHub REST API is blocked from the session; plain git push works). Move to its own repo when one is created.

Metric: lower is better. LB 2026-10-28 00:50 UTC top: 0.00514 / 0.00521 / 0.00530.

| sub | kernel | idea | status |
|---|---|---|---|
| sb01 | sb01-tcombod-baseline | fork of public T_COMBO_D (minhduonq; zone-PI + demand SAT) | pending since 10-27 21:03 |
| sb02 | sb-combo-c42 | T_COMBO_D + heating warm-up 4K/h, cooling 2K/h, occupied cooling float 0.8K below upper band (local dev -6.1%) | pending |
| sb03 | sb-combo-c42-f10 | C42 with cooling float 1.0K (conservative) | pending |
| sb04 | sb-combo-c62 | C42 with heating warm-up 6K/h (dev -6.4%, more comfort risk) | pending |
| - | sb-combo-r4 | intermediate variant, not submitted | - |

All CPU only. Next: once sb01-sb04 score, pick the warm-up rate / float direction from the deltas before tuning further.
