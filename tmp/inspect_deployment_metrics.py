import sys
from pathlib import Path
import numpy as np
from pyulog import ULog
sys.path.insert(0,str(Path('data/升力闭环测试').resolve()))
from analyze_closed_loop import topic,detect_ramp
base=Path(r'D:\1-phd_data\3-research_data\quadrotor\0 paper\2-高机动测试台\实验数据\旋转台测试\升力模型+闭环控制')
for p in sorted((base/'20260822').glob('*.ulg')):
 u=ULog(str(p));c=topic(u,'thrust_control_data');t=c['timestamp']/1e6; v=c['bet_freestream_m_s'];sm,t10,t90,lo,hi=detect_ramp(t,v,1/np.median(np.diff(t)))
 r=topic(u,'rpm');tr=r['timestamp']/1e6;rpm=-r['rpm_raw'];pre=(tr>=t10-3)&(tr<=t10-.5);ev=(tr>=t10)&(tr<=t90+3);post=(tr>=t90+2)&(tr<=t90+3);npre=np.mean(rpm[pre]);d=(rpm/npre-1)*100
 print(p.name,'t10/t90',t10,t90,'v',lo,hi,'npre',npre,'bias/peak/rms',np.mean(d[post]),np.max(abs(d[ev])),np.sqrt(np.mean(d[ev]**2)))
 for name,field in [('thrust_control','control[0]'),('actuator_motors','control[0]'),('actuator_outputs','output[0]'),('thrust_control_data','thrust_control_out[0]')]:
  z=next(d.data for d in u.data_list if d.name==name and d.multi_id==0);tz=z['timestamp']/1e6;m=(tz>=t10-3)&(tz<=t90+4);print(name,field,np.min(z[field][m]),np.median(z[field][m]),np.max(z[field][m]))
for p in Path('data/传感器补偿').glob('*.ulg'):
 u=ULog(str(p)); w=topic(u,'vehicle_angular_velocity'); t=w['timestamp']/1e6;v=abs(w['xyz[2]'])*1.5;sm,t10,t90,lo,hi=detect_ramp(t,v,1/np.median(np.diff(t)))
 r=topic(u,'rpm');rt=r['timestamp']/1e6;rw=(rt>=t10-3)&(rt<=t90+4);rr=r['rpm_raw'][rw]
 a=next(d.data for d in u.data_list if d.name=='actuator_outputs' and d.multi_id==0);ta=a['timestamp']/1e6;mm=(ta>=t10-3)&(ta<=t90+4)
 print(p.name,'t10/t90',t10,t90,'delta',t90-t10,'v',lo,hi,'rpm',np.min(rr),np.max(rr),'nonzero',np.count_nonzero(rr),'pwm',np.unique(a['output[0]'][mm]))

