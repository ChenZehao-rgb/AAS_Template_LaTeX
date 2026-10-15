from pathlib import Path
from pyulog import ULog
import numpy as np
for p in Path('data/传感器补偿').glob('未*.ulg'):
 u=ULog(str(p));raw=next(d.data for d in u.data_list if d.name=='pressure_force_sensor'); f=next(d.data for d in u.data_list if d.name=='thrust_data')
 print(p.name)
 for mode in ['previous','next','nearest']:
  ix=np.clip(np.searchsorted(raw['timestamp'],f['timestamp'],side='right')-1,0,len(raw['timestamp'])-1)
  if mode=='next': ix=np.clip(ix+1,0,len(raw['timestamp'])-1)
  if mode=='nearest':
   j=np.clip(ix+1,0,len(raw['timestamp'])-1);ix=np.where(abs(f['timestamp'].astype(float)-raw['timestamp'][ix])<=abs(f['timestamp'].astype(float)-raw['timestamp'][j]),ix,j)
  x=raw['sensor2'][ix].astype(float);y=f['thrust_raw_data_1'].astype(float);m=(y>0.05)&(y<3)
  a,b=np.polyfit(x[m],y[m],1);res=y[m]-a*x[m]-b; print(mode,a,b,'res RMS/max',np.sqrt(np.mean(res**2)),np.max(abs(res)), 't diff',np.median(f['timestamp'].astype(float)-raw['timestamp'][ix]))
  if mode=='previous': print(np.column_stack([x[m][:12],y[m][:12]]))
