import sys
from pathlib import Path
from pyulog import ULog
import numpy as np
sys.path.insert(0,str(Path('data/升力闭环测试').resolve()))
from analyze_closed_loop import detect_ramp
base=Path(r'D:\1-phd_data\3-research_data\quadrotor\0 paper\2-高机动测试台\实验数据\旋转台测试\升力模型+闭环控制')
paths=list((base/'20260819').glob('*无转速*.ulg'))+list((base/'20260818').glob('16-*.ulg'))
for p in paths:
 u=ULog(str(p));tpc=lambda n: next(d.data for d in u.data_list if d.name==n and d.multi_id==0)
 w=tpc('vehicle_angular_velocity');t=w['timestamp']/1e6;v=abs(w['xyz[2]'])*1.5
 try: sm,t10,t90,lo,hi=detect_ramp(t,v,1/np.median(np.diff(t)))
 except Exception as e: print(p.name,e);continue
 f=tpc('thrust_data');tf=f['timestamp']/1e6;m=(tf>=t10)&(tf<=t90+3)
 raw=tpc('pressure_force_sensor');tr=raw['timestamp']/1e6;mm=(tr>=t10)&(tr<=t90+3)
 a=tpc('actuator_outputs');ta=a['timestamp']/1e6;am=(ta>=t10)&(ta<=t90+3)
 print(p.parent.name,p.name,'sha',u.msg_info_dict.get('ver_sw'),'10-90',t90-t10,'rawsensor',np.min(raw['sensor2'][mm]),np.max(raw['sensor2'][mm]),'raw thrust minmax',np.min(f['thrust_raw_data_1'][m]),np.max(f['thrust_raw_data_1'][m]),'filtered RMS',np.sqrt(np.mean(f['thrust_kalman_filter_data_1'][m]**2)),'pwm',np.unique(a['output[0]'][am]))
