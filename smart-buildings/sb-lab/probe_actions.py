import sys; sys.argv=[sys.argv[0]]
import harness as H, numpy as np, sbpol
from harness import evaluate, ROOT, LOG
sd=ROOT/'smart_buildings/training_scenarios/building_train_1/fairbanks_1'
env=evaluate.load_hybrid_environment(sd/'config.gin'); env.metrics_path=None; env._occupancy_normalization_constant=125.0
meta=evaluate.create_building_meta_data(env, sd); pol=sbpol.SB06(meta, env.action_spec())
print('recirc idx',meta['recirculation_indices'],'pressure',meta['pressure_indices'],'temp',meta['temp_indices'])
print({k:v for k,v in list(meta['action_normalization_metadata'].items())[:3]})
obs,_=env.reset(); LOG.clear()
for t in range(400):
    a=evaluate.validate_action(pol.get_action(obs), env.action_spec())
    obs,r,te,tr,_=env.step(a)
    if t%24==0:
        c=a['continuous_action']; L=LOG[-1]
        print(t/12, 'disc',a['discrete_action'], 'rec',np.round(c[meta['recirculation_indices']],2),'p',np.round(c[meta['pressure_indices']],2),'sat',np.round(c[meta['temp_indices']],2),'gas %.0f bl %.1f occ %d'%(L[7]/1e3,L[5]/1e3,L[4]))
