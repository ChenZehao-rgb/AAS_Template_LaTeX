from pathlib import Path
from pyulog import ULog
import numpy as np
import pandas as pd
BASE=Path(r'D:\1-phd_data\3-research_data\quadrotor\0 paper\2-高机动测试台\实验数据\旋转台测试')
paths=list(Path('data/传感器补偿').glob('*.ulg'))+[next((BASE/'升力模型+闭环控制/20260822').glob('7-*'))]
for p in paths:
 u=ULog(str(p)); print('\nFILE',p.name)
 print('info',u.msg_info_dict)
 print('params',{k:v for k,v in u.initial_parameters.items() if any(x in k for x in ['PWM_MAIN','TFC','THR','SENS_BOARD'])})
 for d in u.data_list:
  if any(x in d.name for x in ['thrust','rpm','pressure','angular','acceleration','actuator','attitude']):
   print(d.name,d.multi_id,len(d.data['timestamp']),list(d.data))
   for k,v in d.data.items():
    if k!='timestamp' and any(x in k for x in ['sensor2','raw','filter_data_1','xyz','output[0]','control[0]']): print(k,np.nanmin(v),np.nanmedian(v),np.nanmax(v))
p=BASE/'升力模型+闭环控制/转速-控制量标定.xlsx'
xl=pd.ExcelFile(p);print('WORKBOOK',xl.sheet_names)
for s in xl.sheet_names:
 print(s);print(pd.read_excel(p,sheet_name=s).to_string(index=False))
