import numpy as np, sys, math
from scipy.optimize import linprog
S=2.0**24  # units of 2^-64 per LP unit (2^-40 turn)
d=np.load('bits_1.npz'); B=d['bits'].astype(np.float64); rot=d['rot']
err=np.load('err.npy').astype(np.float64)/S; tol=np.load('tol.npy').astype(np.float64)/S
L=open('/tmp/claude-0/qdata/w.kmx').read().splitlines()
from fractions import Fraction
A=np.array([float(Fraction(L[i].split()[2])*2**63)/S for i in rot])  # current angles in LP units
K=len(rot)
def solve(drop, iters=30, verbose=False):
    keep=[k for k in range(K) if k not in drop]
    e0=err - B[:,list(drop)]@A[list(drop)] if drop else err.copy()   # removing rotation subtracts its contribution
    Bk=B[:,keep]
    marg=tol-np.abs(e0)
    idx=set(np.argsort(marg)[:3000].tolist())|set(np.random.default_rng(0).choice(len(err),5000,replace=False).tolist())
    for it in range(iters):
        I=np.array(sorted(idx))
        n=len(keep)
        # vars: delta (n), m ; minimize -m ; e0+Bd + m <= tol ; -(e0+Bd) + m <= tol
        Aub=np.vstack([np.hstack([Bk[I],np.ones((len(I),1))]),np.hstack([-Bk[I],np.ones((len(I),1))])])
        bub=np.concatenate([tol[I]-e0[I],tol[I]+e0[I]])
        r=linprog(np.r_[np.zeros(n),-1.0],A_ub=Aub,b_ub=bub,bounds=[(-1e6,1e6)]*n+[(None,None)],method='highs')
        if r.status!=0: return None
        dl=r.x[:n]; m=r.x[n]
        res=e0+Bk@dl; mm=tol-np.abs(res)
        true_m=mm.min()
        if verbose: print(it,len(I),m,true_m)
        if true_m>=m-1e-6: break
        new=np.argsort(mm)[:2000]; idx|=set(new.tolist())
    return true_m, keep, dl
cur=(tol-np.abs(err)).min(); print('current margin units',cur)
def cost(nrot,m_units):
    mt=m_units*2.0**-40
    eps=math.pi*mt/nrot
    return (1+nrot*(0.56*math.log2(1/eps)+5.3))/4
print('current T/4 cost',cost(41,cur))
res=solve(set(),verbose=True); print('LP all 41: margin',res[0],'cost',cost(41,res[0]))
np.save('lp41.npy',res[2])
