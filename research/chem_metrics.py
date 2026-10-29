import sys,json
sys.path[:0]=['/home/claude/qc/comp/kickmix','/home/claude/qc/comp/verifiers']
from dfthcsos import verify as vd
r=vd.verify(sys.argv[1], salt='local1')
print(json.dumps(r['metrics'],indent=0,default=str)); print(json.dumps(r['resources'],indent=0,default=str))
