# v16 - best-of public portfolio (public 23.17173)

Submitted 2026-10-30 19:39 UTC, ref 57815640, CPU only.
- invsqrt: yoyobar 62q (sha 67482db6), cost 100,693
- DQI: yoyobar-output 889q (sha 73e1b187), 4.0246e11; official verifier PASS on 12 salts, one value error in 1.23M shots (salt f, ~0.46% DQI cost on such a salt, expected private impact ~0.003)
- chemistry: Ozer weights via manwithacat Real-150K output (npz 47427ee0), lambda_eff 48.2956, 3.37798e8; PASS on 7 salts
Credits: yoyobar, manwithacat, Ahmed Berat Ozer, heliosli, Gluzdov, Aldemir, somejoint.
Chemistry angle circuits (shared by every public portfolio) fail a random-target XOR phase audit (research/chem_xor_audit.py) but run only on their spec'd input sequence in the verifier.
