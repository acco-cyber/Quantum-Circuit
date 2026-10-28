import sys, importlib, numpy as np
sys.argv=[sys.argv[0]]+sys.argv[1:]
import harness as H
from harness import evaluate, ROOT, LOG
mod, cls, steps, scen = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
P=getattr(importlib.import_module(mod), cls)
sd=ROOT/'smart_buildings'/scen
env=evaluate.load_hybrid_environment(sd/'config.gin'); env.metrics_path=None; env._occupancy_normalization_constant=125.0
meta=evaluate.create_building_meta_data(env, sd); pol=P(meta, env.action_spec())
names=meta['observation_field_names']
oaf=[i for i,n in enumerate(names) if n.endswith('outside_air_flowrate_sensor')]
saf=[i for i,n in enumerate(names) if n.endswith('supply_air_flowrate_sensor')]
oat=[i for i,n in enumerate(names) if n.endswith('outside_air_temperature_sensor')][0]
zt=[i for i,n in enumerate(names) if n.endswith('zone_air_temperature_sensor')]
sw=names.index('hws_supply_water_temperature_sensor')
norm=meta['observation_normalization_metadata']
def den(i,v):
    st=norm.get(names[i]) or {}
    return v*st.get('sample_std',1)+st.get('sample_mean',0)
obs,_=env.reset(); LOG.clear(); rows=[]
for t in range(steps):
    a=evaluate.validate_action(pol.get_action(obs), env.action_spec())
    rec=(t, sum(den(i,obs[i]) for i in oaf), sum(den(i,obs[i]) for i in saf), obs[oat], den(oat,obs[oat]), np.mean([den(i,obs[i]) for i in zt]), den(sw,obs[sw]), int(a['discrete_action'].sum()))
    obs,r,te,tr,_=env.step(a); rows.append(rec+tuple(LOG[-1]))
np.save('probe_%s.npy'%cls, np.array(rows,dtype=float))
R=np.array(rows,dtype=float)
for h in range(0,steps,12):
    x=R[h]; print('h%5.1f oaf%7.2f saf%7.2f oatraw%7.2f oat%7.1f zt%6.1f sw%6.1f on%d | rew%8.4f occ%4.0f bl%6.1f ac%7.1f gas%7.1f' % (h/12, x[1],x[2],x[3],x[4],x[5],x[6],x[7],x[8],x[12],x[13]/1e3,x[14]/1e3,x[15]/1e3))
