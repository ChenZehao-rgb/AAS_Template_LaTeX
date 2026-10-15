import sys
sys.dont_write_bytecode=True
from pathlib import Path
import importlib.util
import numpy as np
from pyulog import ULog
root=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('replay',root/'data_process/plot_sensor_source_replay.py')
p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
u=ULog(str(root/'data/传感器补偿/补偿-rawdate显示限幅.ulg'))
raw=p.P.topic(u,'pressure_force_sensor');rt=p.P.tt(raw);s=p.P.val(raw,'sensor2')
f=p.P.topic(u,'thrust_data');t=p.P.tt(f);y=p.P.val(f,'thrust_raw_data_1')
a=p.P.topic(u,'vehicle_acceleration');at=p.P.tt(a)
ri=np.searchsorted(rt,t,side='right')-1
ai=np.maximum(np.searchsorted(at,t,side='right')-1,0)
ss=s[ri];ay=p.P.val(a,'xyz[1]')[ai]
axd,ayd,*_=p.delayed_accel(a,t)
w=p.P.topic(u,'vehicle_angular_velocity');wt=p.P.tt(w);v=abs(p.P.val(w,'xyz[2]'))*1.5
_,t10,t90,lo,hi=p.P.S.detect_ramp(wt,v,1/np.median(np.diff(wt)))
print('RAMP',t10,t90,t90-t10,lo,hi,'log',rt[0],rt[-1])
print('FORCE RANGE',s.min(),s.max(),'logged raw',y.min(),y.max(),'filtered',f['thrust_kalman_filter_data_1'].min(),f['thrust_kalman_filter_data_1'].max())
print('FIRST20 BIAS',np.mean(s[:20]),'param limit',u.initial_parameters['TFC_THRUST_MAX'])
print('RANGES',[(key,float(a[key].min()),float(a[key].max())) for key in ['xyz[0]','xyz[1]','xyz[2]']])
valid=(y>y.min()+1e-5)&(y<y.max()-1e-5)&(ri>=0)
vis=(t>=t10-3)&(t<=t90+4)
for name,z in [('raw9.8',ss*.0098),('mass.33',ss*.00980665+.33*ay),('source2axis', (ss+36.839*ayd-3.332*axd)*.00980665)]:
    for scope,m in [('full',valid),('visible',valid&vis)]:
        delta=z[m]-y[m];b=np.median(delta)
        print(name,scope,'n',sum(m),'offset',b,'RMSE',np.sqrt(np.mean((delta-b)**2)),'p95',np.quantile(abs(delta-b),.95),'range',np.min(z[vis]-b),np.max(z[vis]-b))
print('RAW CLIPS visible',sum(vis&(y==y.min())),sum(vis&(y==y.max())))
print('TIMING force age',np.quantile(t-rt[ri],[0,.5,.95,1]))
X=np.column_stack([ss[valid],ay[valid],np.ones(sum(valid))]);coef=np.linalg.lstsq(X,y[valid],rcond=None)[0]
print('DIAGNOSTIC LINEAR COEFFICIENTS sensor,ay,constant',coef,'residual',np.sqrt(np.mean((X@coef-y[valid])**2)))
print('DROPOUTS',u.dropouts)
X=np.column_stack([ss[valid],ayd[valid],axd[valid],np.ones(sum(valid))]);coef=np.linalg.lstsq(X,y[valid],rcond=None)[0]
print('2axis diagnostic coefficients',coef,'residual',np.sqrt(np.mean((X@coef-y[valid])**2)))
for delay in [0,.01,.02,.03,.04,.05,.06,.08,.1]:
    p.C['fixed_accel_delay_s']=delay
    xx,yy,*_=p.delayed_accel(a,t)
    z=(ss+36.839*yy-3.332*xx)*.00980665
    delta=z[valid]-y[valid];b=np.median(delta)
    print('delay diagnostic',delay,'offset',b,'rmse',np.sqrt(np.mean((delta-b)**2)))
import matplotlib.pyplot as plt
fig,aa=plt.subplots(4,1,figsize=(10,10),sharex=True)
aa[0].plot(rt,s*.00980665);aa[1].plot(t,y);aa[1].plot(t,f['thrust_kalman_filter_data_1']);aa[2].plot(at,a['xyz[0]']);aa[2].plot(at,a['xyz[1]']);aa[3].plot(wt,v)
for ax in aa:ax.set_xlim(t10-3,t90+4);ax.grid()
fig.savefig(root/'tmp/new_compensation_diagnostic.png',dpi=120)
