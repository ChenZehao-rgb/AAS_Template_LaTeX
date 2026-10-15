from pathlib import Path
from pyulog import ULog
import numpy as np
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path('data/升力闭环测试').resolve()))
from analyze_closed_loop import detect_ramp
for p in Path('data/传感器补偿').glob('未*.ulg'):
 u=ULog(str(p));topic=lambda name:next(d.data for d in u.data_list if d.name==name and d.multi_id==0)
 w=topic('vehicle_angular_velocity');wt=w['timestamp'].astype(float)/1e6
 _,t10,t90,lo,hi=detect_ramp(wt,abs(w['xyz[2]'])*1.5,1/np.median(np.diff(wt)))
 a=topic('vehicle_acceleration');at=a['timestamp'].astype(float)/1e6
 pre=(at>=t10-3)&(at<=t10-.5);ev=(at>=t10)&(at<=t90+3)
 f=topic('pressure_force_sensor');ft=f['timestamp'].astype(float)/1e6
 print(p.name,'t10',t10,'t90',t90,'dt',t90-t10)
 for k in ['xyz[0]','xyz[1]','xyz[2]']:
  x=a[k].astype(float);print(k,'pre mean',x[pre].mean(),'range',x[ev].min(),x[ev].max(),'time of min/max',at[ev][np.argmin(x[ev])]-t10,at[ev][np.argmax(x[ev])]-t10)
 print('acc median timestamp - timestamp_sample us',np.median(a['timestamp'].astype(float)-a['timestamp_sample'].astype(float)))
 q=topic('vehicle_attitude');qt=q['timestamp'].astype(float)/1e6;qm=(qt>=t10)&(qt<=t90+3)
 # NED down direction in body coordinates: R(q)^T * [0,0,1].
 qw,qx,qy,qz=[q[f'q[{k}]'].astype(float)[qm] for k in range(4)]
 down=np.array([2*(qx*qz-qw*qy),2*(qy*qz+qw*qx),1-2*(qx*qx+qy*qy)])
 print('body gravity range',[(z.min()*9.8,z.max()*9.8) for z in down])
 print('acc dt range',np.quantile(np.diff(at),[0,.5,1]),'force dt',np.quantile(np.diff(ft),[0,.5,1]))
