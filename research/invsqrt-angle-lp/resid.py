import sys, numpy as np
sys.path.insert(0,'/tmp/claude-0/qdata/kickmix'); sys.path.insert(0,'/tmp/claude-0/qdata/verifiers')
from fractions import Fraction
from invsqrt.verify_submission_invsqrt import ProblemSpecInvSqrt, reference_values
L=open('/tmp/claude-0/qdata/w.kmx').read().splitlines()
d=np.load('bits_1.npz'); bits=d['bits']; base=d['base']; rot=d['rot']
ang=[Fraction(L[i].split()[2]) for i in rot]   # half turns
spec=ProblemSpecInvSqrt.for_n_p(10)
N=spec.max_x
target,tol=reference_values(spec,np.arange(1,N+1,dtype=np.uint64))
np.save('target.npy',target); np.save('tol.npy',tol)
# angles in units of 2^-64 turns: half-turn a -> a/2 turns -> a*2^63 units (exact rational -> round)
A=np.array([int(round(a*2**63)) for a in ang],dtype=object)
Ai=np.array([int(x) for x in A],dtype=np.uint64)
ph=(base.astype(np.uint64)<<np.uint64(60))  # base/8 half-turn = base/16 turn = base*2^60 units
ph=ph+ (bits.astype(np.uint64)*Ai[None,:]).sum(1,dtype=np.uint64)
err=(ph-target).view(np.int64)
ratio=np.abs(err)/tol
i=ratio.argmax(); print('worst ratio',ratio.max(),'x',i+1)
margin=(tol.astype(np.float64)-np.abs(err.astype(np.float64)))
print('min margin turns',margin.min()/2**64,'at x',margin.argmin()+1)
np.save('err.npy',err)
