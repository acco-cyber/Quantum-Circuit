exec(open('lp.py').read().split("cur=(tol")[0])
import math
def cost(nrot,m_units):
    if m_units<=0: return float('inf')
    eps=math.pi*m_units*2.0**-40/nrot
    return (1+nrot*(0.56*math.log2(1/eps)+5.3))/4
base=cost(41,3.4927)
for k in range(K):
    r=solve({k})
    if r is None: print(k,'infeasible'); continue
    print(k, 'margin %.3f'%r[0], 'Tcost delta %.2f'%(cost(40,r[0])-base), flush=True)
