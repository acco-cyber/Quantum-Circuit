# v13 - 2026-10-28 ~08:55 UTC (quantum slot 5 of 10-28), ref 57731187

v12 with **only the DQI member swapped** for the alexchilton 889-qubit decoder (sha 4ee7a17b), taken from the public
output of `leoprovorov/the-unbearable-lightness-of-quantum-circuits` (run 07:35 UTC, "hybrid: alexchilton DQI +
somejoint chemistry"; source alexchilton '22.34 LB: Verified Three-Task Portfolio'). invsqrt and chemistry are the
v12 bytes (somejoint archive 5b2b5023), so the LB-proven parts are untouched.

| task | component | cost | vs v12 |
|---|---|---:|---|
| invsqrt | busyaprime 63q v2 (07314803) | 102,664 | identical |
| dqi | alexchilton decoder, 889 qubits, 440,564 mean Toffolis | 4.1478e11 | was 897q 4.2235e11 (-1.79%) |
| dfthcsos | somejoint R8/B143 C62 (c59c5992) | 3.47715e8 | identical |

Local check: official `verify_submission_dqi.py` + competition `kickmix.so`, own salts `local-check-1028h` and
`local-check-1028i` -> PASS, 0 value / 0 phase errors, score 4.14781e11 (`dqi-verifier-local.json`). The leoprovorov
receipt only had a byte-pinned DQI report, so this is the first executed check we know of.

Projection: 22.37455 x (4.2235/4.1478)^(1/3) = **22.510**. No GPU used.

Lesson: the 897q decoder was not width-optimal - 8 fewer qubits at ~the same Toffoli count (440.6k vs 440.6k) is a
pure ~1.8% DQI win, so cost ~ Q x T and the width side still has room (ancilla lifetime / reuse in the decoder).
