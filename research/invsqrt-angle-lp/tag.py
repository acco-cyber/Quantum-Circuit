import sys, re, time
sys.path.insert(0,'/tmp/claude-0/qdata/kickmix'); sys.path.insert(0,'/tmp/claude-0/qdata/verifiers')
import numpy as np, kickmix as km
from fractions import Fraction
from invsqrt.verify_submission_invsqrt import ProblemSpecInvSqrt, to_bits, z_pow_class, reference_values
L=open('/tmp/claude-0/qdata/w.kmx').read().splitlines()
rot=[]
for i,l in enumerate(L):
    if l.startswith('Z_POW'):
        a=Fraction(l.split()[2])
        if z_pow_class(a)=='rotation': rot.append(i)
print('n rot lines',len(rot))
T=list(L)
for k,i in enumerate(rot):
    p=T[i].split(); n=4+k; T[i]=f'{p[0]} {p[1]} 0.'+str(5**n).rjust(n,'0')
open('tag.kmx','w').write('\n'.join(T)+'\n')
c=km.Circuit.from_file('tag.kmx',format='kmx')
spec=ProblemSpecInvSqrt.for_n_p(10)
x_reg=km.array(list(c.register_data['x']))
B=4096
sim=km.Simulator(batch_size=B,debug_print=False,counting_operations=False,seed=int(sys.argv[1]) if len(sys.argv)>1 else 1)
N=spec.max_x; xs_all=np.arange(1,N+1,dtype=np.uint64)
pad=(-N)%B
xs_all=np.concatenate([xs_all,np.ones(pad,dtype=np.uint64)])
bits=np.zeros((len(xs_all),len(rot)),dtype=bool); base=np.zeros(len(xs_all),dtype=np.int64)
t0=time.time()
for s in range(0,len(xs_all),B):
    xs=xs_all[s:s+B]
    sim.clear_for_shot(); sim.write_across_shots(x_reg,to_bits(xs,22)); sim.do(c)
    for j in range(B):
        ph=Fraction(sim.read_shot_phase(j)) % 2   # half turns
        u=int(ph*2**44)  # units 2^-44 half turns
        base[s+j]=u>>41  # multiples of 1/8 half-turn... (2^41 units = 2^-3 half turn)
        frac=u & ((1<<41)-1)
        for k in range(len(rot)):
            bits[s+j,k]=(frac>>(40-k))&1
    if s==0: print('first batch',time.time()-t0, type(sim.read_shot_phase(0)))
bits=bits[:N]; base=base[:N]
np.savez_compressed(f'bits_{sys.argv[1] if len(sys.argv)>1 else 1}.npz',bits=bits,base=base,rot=np.array(rot))
print('done',time.time()-t0)
