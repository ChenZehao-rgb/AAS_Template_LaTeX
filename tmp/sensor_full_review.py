from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pyulog import ULog
fig,axs=plt.subplots(6,1,figsize=(12,14))
for ax,p in zip(axs,Path('data/传感器补偿').glob('*.ulg')):
 u=ULog(str(p)); w=next(d.data for d in u.data_list if d.name=='vehicle_angular_velocity');raw=next(d.data for d in u.data_list if d.name=='pressure_force_sensor');f=next(d.data for d in u.data_list if d.name=='thrust_data')
 t=w['timestamp']/1e6;t0=t[0]
 ax.plot(t-t0,abs(w['xyz[2]'])*1.5,label='V m/s',color='grey')
 ax.plot(raw['timestamp']/1e6-t0,raw['sensor2']*.0098,label='sensor2*.0098',lw=.7)
 ax.plot(f['timestamp']/1e6-t0,f['thrust_kalman_filter_data_1'],label='filtered',lw=.7)
 ax.set_title(p.name,fontfamily='SimSun'); ax.grid();ax.legend();ax.set_xlabel(f't - {t0:.2f} s')
fig.tight_layout();fig.savefig('tmp/sensor_full_review.png',dpi=130)
