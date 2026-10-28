import sys, time, json, importlib
from pathlib import Path
import numpy as np
ROOT=Path('/home/claude/sbdata/d')
sys.path.insert(0,str(ROOT)); sys.path.insert(0,'/home/claude/sbwork')
import os; os.chdir(ROOT)
import matplotlib; matplotlib.use('Agg')
from smart_buildings import evaluate
from smart_buildings.smart_control.reward import setpoint_energy_carbon_regret as R
LOG=[]
_orig=R.SetpointEnergyCarbonRegretFunction.compute_reward
def patched(self, ri):
    r=_orig(self, ri)
    bl=sum(a.blower_electrical_energy_rate for a in ri.air_handler_reward_infos.values())
    ac=sum(a.air_conditioning_electrical_energy_rate for a in ri.air_handler_reward_infos.values())
    gas=sum(b.natural_gas_heating_energy_rate for b in ri.boiler_reward_infos.values())
    pump=sum(b.pump_electrical_energy_rate for b in ri.boiler_reward_infos.values())
    LOG.append((r.agent_reward_value, r.normalized_productivity_regret, r.normalized_energy_cost, r.normalized_carbon_emission, r.total_occupancy, bl, ac, gas, pump, r.electricity_energy_cost, r.natural_gas_energy_cost))
    return r
R.SetpointEnergyCarbonRegretFunction.compute_reward=patched

def run(policy_cls, scen_dir, steps=8640):
    LOG.clear()
    env=evaluate.load_hybrid_environment(scen_dir/'config.gin')
    env.metrics_path=None; env._occupancy_normalization_constant=125.0
    meta=evaluate.create_building_meta_data(env, scen_dir)
    pol=policy_cls(meta, env.action_spec())
    obs,_=env.reset()
    LOG.clear()
    tot=0;n=0
    for i in range(steps):
        a=evaluate.validate_action(pol.get_action(obs), env.action_spec())
        obs,r,term,trunc,_=env.step(a)
        tot+=r;n+=1
        if term or trunc: break
    L=np.array(LOG)
    occ=L[:,4]>0
    extra=dict(blower_kW=float(L[:,5].mean()/1e3), ac_kW=float(L[:,6].mean()/1e3), gas_kW=float(L[:,7].mean()/1e3), pump_kW=float(L[:,8].mean()/1e3),
        elec_usd=float(L[:,9].sum()), gas_usd=float(L[:,10].sum()), occ_frac=float(occ.mean()),
        cost_occ=float(-(L[occ,0]).sum()/len(L)), cost_unocc=float(-(L[~occ,0]).sum()/len(L)))
    np.save('/home/claude/sbwork/log_%s.npy'%policy_cls.__name__, L)
    return dict(**extra, score=-tot/n, n=n, prod=float(-(L[:,1]).mean()*0.6), energy=float(L[:,2].mean()*0.2), carbon=float(L[:,3].mean()*0.2))

if __name__=='__main__':
    mod, cls = sys.argv[1], sys.argv[2]
    steps=int(sys.argv[3]); scen=sys.argv[4:]
    P=getattr(importlib.import_module(mod), cls)
    for s in scen:
        t=time.time(); res=run(P, ROOT/'smart_buildings'/s, steps)
        print(json.dumps(dict(scen=s, cls=cls, **res, sec=round(time.time()-t))), flush=True)
