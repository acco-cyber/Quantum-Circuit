# Arbitrary-target XOR/phase audit of a dfthcsos angle-circuit family.
# Contract run (as the verifier): ANGLE_k maps batch_{k-1} -> batch_k on the word registers.
# Audit: start ANGLE_k from random words y; require words -> y ^ batch_k ^ batch_{k-1},
# selection unchanged, workspace clean, phase unflipped, on every shot.
import sys, os, json
import numpy as np
comp, subdir = sys.argv[1], sys.argv[2]
reps = int(sys.argv[3]) if len(sys.argv) > 3 else 16
trials = int(sys.argv[4]) if len(sys.argv) > 4 else 3
sys.path[:0] = [os.path.join(comp,'kickmix'), os.path.join(comp,'verifiers')]
import kickmix as km
from dfthcsos.scoreinfra import circuits as C
circs = C.load_circuits(subdir)
L = C.register_layout(circs)
nsel = len(L.selection); brot = L.brot; J = L.batch_size
from dfthcsos import verify as V
nv = V.load_inputs(os.path.join(subdir,'submission.npz')).num_vectors
rng = np.random.default_rng(12345)
sim = km.Simulator(batch_size=nv*reps, debug_print=False, seed=987654321, counting_operations=False)
sim.use_same_registers_as(circs[0])
addr = np.tile(np.arange(nv), reps)
abits = ((addr[None,:] >> np.arange(nsel)[:,None]) & 1).astype(bool)
pv = np.int64(1) << np.arange(brot, dtype=np.int64)
public = L.public_qubits
def setw(vals):  # vals (nv*reps, J)
    for j,w in enumerate(L.words):
        sim.write_across_shots(w, ((vals[:,j][None,:] >> np.arange(brot)[:,None]) & 1).astype(bool))
def readw():
    return np.stack([pv @ sim.read_across_shots(w).astype(np.int64) for w in L.words], axis=1)
def state_ok(c):
    probs = []
    if np.any(sim.read_phase_flipped_across_shots()): probs.append('phase')
    if not np.array_equal(sim.read_across_shots(L.selection), abits): probs.append('selection')
    work = [km.q(i) for i in range(c.num_qubits) if i not in public]
    if work and np.any(sim.read_across_shots(km.array(work))): probs.append('workspace')
    return probs
def run(c, init):
    sim.clear_for_shot(); sim.write_across_shots(L.selection, abits); setw(init)
    sim.do(c); return readw(), state_ok(c)
report = {'circuits': len(circs), 'brot': brot, 'J': J, 'addresses': nv, 'shots_per_address': reps, 'per_circuit': []}
prev = np.zeros((nv*reps, J), dtype=np.int64)
allok = True
for k, c in enumerate(circs):
    out, probs = run(c, prev)
    entry = {'k': k, 'contract_problems': probs}
    delta = out ^ prev
    bad = 0; pb = set()
    for t in range(trials):
        y = rng.integers(0, 1 << brot, size=(nv*reps, J), dtype=np.int64)
        o2, p2 = run(c, y)
        bad += int(np.sum(np.any(o2 != (y ^ delta), axis=1))); pb |= set(p2)
    entry['xor_value_bad_shots'] = bad; entry['xor_problems'] = sorted(pb)
    if probs or bad or pb: allok = False
    report['per_circuit'].append(entry)
    prev = out
report['ALL_OK'] = allok
print(json.dumps(report))
