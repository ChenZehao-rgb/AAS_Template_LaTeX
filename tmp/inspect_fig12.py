import importlib.util, sys
from pathlib import Path
import numpy as np
from pyulog import ULog
root=Path.cwd()
p=root/'data'/'升力闭环测试'/'analyze_closed_loop.py'
s=importlib.util.spec_from_file_location('ana',p); a=importlib.util.module_from_spec(s);sys.modules[s.name]=a;s.loader.exec_module(a)
for p in sorted(a.DATA_DIR.glob('*.ulg')):
 if a.parse_filename(p)[1:3]!=(20,1) or a.parse_filename(p)[3]=='static': continue
 r=a.load_run(p);u=ULog(str(p));m=(r.tau_s>=-2)&(r.tau_s<=r.t90_s-r.t10_s+4)
 print('\nLOG',p.name,'t10,t90',r.t10_s,r.t90_s,'fs',r.sampling_hz)
 print('info',u.msg_info_dict)
 print('params', {k:v for k,v in u.initial_parameters.items() if any(x in k for x in ('THR','PWM','DSHOT','BET','PID','RPM'))})
 print('topics',[(d.name,d.multi_id,len(d.data['timestamp'])) for d in u.data_list if any(x in d.name for x in ('thrust','rpm','actuator','motor','esc'))])
 for n in ('freestream_m_s','model_rpm','measured_rpm','feedforward_out','feedback_out','total_out','actuator_output_0'):
  v=getattr(r,n)[m];print(n,'range',np.min(v),np.max(v),'pcts',np.percentile(v,[5,50,95]))
 v=r.total_out-r.feedforward_out-r.feedback_out; print('sum residual',np.percentile(v[m],[0,50,100]),'max all',np.max(np.abs(v)))
 print('actuator residual pwm 1000+',np.percentile((r.actuator_output_0-(1000+1000*r.total_out))[m],[0,50,100]))
 raw=a.topic(u,'rpm');t=raw['timestamp']/1e6-r.t10_s;y=-raw['rpm_raw'].astype(float);v=(t>=-2)&(t<=5)
 ixs=np.flatnonzero(v);lowest=ixs[np.argsort(y[v])[:4]]
 for i in lowest: print('raw low neighborhood',list(zip(t[max(0,i-2):i+3],y[max(0,i-2):i+3])))
 for name in ('thrust_control_data','rpm'):
  print('format',name,[str(f) for f in next(f for f in u._message_formats.values() if f.name==name).fields])
