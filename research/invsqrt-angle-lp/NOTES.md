# invsqrt: rotation-angle LP on the current best circuit (2026-10-28 ~05:00 UTC)

Circuit: busyaprime 63q v2 (sha 07314803...), cost 102,664 = 63 x 1629.59; of C, 1334.50 are Toffolis and
**295.09 are the 41 fine Z_POW rotations** (eps 2.43e-13 -> 28.77 T each). Rotations are 18% of the cost.

Method (zero GPU, ~1 min CPU per pass):
1. `tag.py` replaces rotation k's angle by 2^-(4+k) half-turns and simulates every x in [1, max_x] once; the
   tracked phase then encodes which rotations fired (bit k) plus the Clifford/T base. The bits are identical for
   two simulator seeds, i.e. each rotation's control bit is a deterministic function of x.
2. `resid.py` rebuilds the phase from those bits and the real angles and reproduces the official verifier exactly
   (worst error/tol 0.99932 at x=161, min margin 3.18e-12 turns at x=52229).
3. `lp.py` maximises the margin min_x(tol(x) - |err(x)|) over all 41 angles (cutting-plane LP, HiGHS).
4. `drop.py` re-solves with each rotation removed.

Result:
* The published angles are already **LP-optimal** (margin 3.4927 vs 3.4927 units of 2^-40 turn): nothing to gain from
  retuning angles.
* **No rotation can be dropped**: removing even the cheapest (rotation 15, LSB of block 2) leaves margin -3.6 units.
* So the invsqrt lever is structural: fewer Toffolis in the NR / polynomial stages, a lower-error y0 (more margin ->
  larger eps -> ~0.56 log2 gain per rotation), or fewer qubits. Doubling the margin is only ~-10 Toffoli-eq (-0.6%).
