"""Traceable source-based sensor compensation with matched before/after filtering.

Reconstructs all three nominal1/5/10s conditions from their uncompensated logs.
Keeps earlier plots and literal +y manuscript diagnostic untouched.
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,importlib.util,shutil
import numpy as np
import pandas as pd
from pyulog import ULog
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
CP=Path(__file__).with_name('sensor_source_replay_config.json')
C=json.loads(CP.read_text(encoding='utf-8'));OUT=ROOT/C['output_dir'];OUT.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('draw_sensor',Path(__file__).with_name('plot_sensor_offline_1s.py'))
P=importlib.util.module_from_spec(spec);sys.modules[spec.name]=P;spec.loader.exec_module(P)
P.OUT=OUT;P.C['export_dpi']=C['export_dpi']
manifest=[];all_rows=[];plotrows=[];details=[]

def record(p,role):
    p=Path(p);manifest.append(dict(path=str(p),role=role,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
def csv(n,r):pd.DataFrame(r).to_csv(OUT/n,index=False,encoding='utf-8-sig',float_format='%.12g')

def filter_source(t,y,q_std,r_std,limit):
    """Source BFS1: state(force,force derivative), CV transition, GQG' noise.
    Matrix implementation mirrors source. Both traces get identical gains.
    """
    state=np.zeros(2);cov=np.eye(2);out=np.empty(len(y));I=np.eye(2)
    for i,measurement in enumerate(y):
        dt=C['first_filter_dt_s'] if i==0 else np.clip(t[i]-t[i-1],*C['filter_dt_limits_s'])
        F=np.array([[1.,dt],[0.,1.]])
        G=np.array([dt*dt/2,dt])
        state=F@state;cov=F@cov@F.T+np.outer(G,G)*q_std*q_std
        gain=cov[:,0]/(cov[0,0]+r_std*r_std)
        state+=gain*(measurement-state[0]);KH=np.zeros((2,2));KH[:,0]=gain
        cov=(I-KH)@cov;out[i]=np.clip(state[0],-limit,limit)
    return out

def delayed_accel(a,t):
    sample=P.tt(a,'timestamp_sample');published=P.tt(a)
    sample=np.where(sample>0,sample,published)
    ix=np.searchsorted(sample,t-C['fixed_accel_delay_s'],side='right')-1
    # Full log may begin after module start; use only already published samples.
    availability=np.searchsorted(published,t,side='right')-1
    usable=(availability>=0)
    ix=np.minimum(ix,availability);ix=np.maximum(ix,0)
    az=P.val(a,'xyz[1]')[ix];ax=P.val(a,'xyz[0]')[ix]
    az=np.where(usable,az,0.);ax=np.where(usable,ax,0.)
    return ax,az,ix,usable,sample

def load(item):
    p=ROOT/item['path'];record(p,'uncompensated native input for source-based offline reconstruction')
    u=ULog(str(p));raw=P.topic(u,'pressure_force_sensor');t=P.tt(raw);s=P.val(raw,'sensor2')
    b0=float(np.mean(s[:C['bias_init_logged_samples']]))
    g=C['N_per_g'];before_raw=(s-b0)*g
    a=P.topic(u,'vehicle_acceleration');ax,ay,ix,usable,ats=delayed_accel(a,t)
    parasitic_g=C['parasitic_coeff_ay_g_per_m_s2']*ay+C['parasitic_coeff_ax_g_per_m_s2']*ax
    after_raw=before_raw-parasitic_g*g
    paper_after_raw=before_raw+C['paper_A_kg']*ay-C['paper_B_kg']*ax
    limit=float(u.initial_parameters['TFC_THRUST_MAX'])*1000*g
    nclip_before=int(sum(abs(before_raw)>limit));nclip_after=int(sum(abs(after_raw)>limit))
    before_raw=np.clip(before_raw,-limit,limit);after_raw=np.clip(after_raw,-limit,limit)
    q=float(u.initial_parameters['TFC_SD_ES']);r=float(u.initial_parameters['TFC_SD_ME'])
    changes=[(int(stamp),key,float(value)) for stamp,key,value in u.changed_parameters if key in ['TFC_SD_ES','TFC_SD_ME','TFC_THRUST_MAX']]
    if changes:raise ValueError(f'Filter/limit parameter change needs explicit replay: {changes}')
    before=filter_source(t,before_raw,q,r,limit);after=filter_source(t,after_raw,q,r,limit)
    w=P.topic(u,'vehicle_angular_velocity');wt=P.tt(w);v=abs(P.val(w,'xyz[2]'))*C['inflow_arm_length_m']
    _,t10,t90,low,high=P.S.detect_ramp(wt,v,1/np.median(np.diff(wt)))
    run=dict(path=p,nom=item['nominal_ramp_s'],t=t,before=before,after_t=t,after=after,t10=t10,t90=t90,raw_before=before_raw,raw_after=after_raw)
    for name,y in [('before_matched_filter',before),('after_source_matched_filter',after),('before_unfiltered',before_raw),('after_source_unfiltered',after_raw),('after_paper_rounded_unfiltered',paper_after_raw)]:
        ev=P.mask(t,t10,t90+3);metric=dict(file=p.name,nominal_ramp_s=run['nom'],signal=name,t10_s=t10,t90_s=t90,actual_10_90_s=t90-t10,evaluation_start_s=t10,evaluation_end_s=t90+3,**P.stats(y,ev));all_rows.append(metric)
        if name=='before_matched_filter':run['before_metric']=metric
        if name=='after_source_matched_filter':run['after_metric']=metric
    vis=P.mask(t,t10-3,t90+4)
    for name,y in [('before',before),('after',after)]:
        plotrows.extend(dict(file=p.name,nominal_ramp_s=run['nom'],signal=name,timestamp_s=ti,tau_s=ti-t10,force_N=yi) for ti,yi in zip(t[vis],y[vis]))
    csv(f'condition_{run["nom"]}s_trace.csv',[dict(timestamp_s=ti,tau_s=ti-t10,sensor2_g=si,b0_g=b0,T_raw_N=bi,T_hat_raw_N=ai,T_matched_filter_N=bf,T_hat_matched_filter_N=af,T_hat_paper_rounded_N=pap,ax_delayed_m_s2=xx,ay_delayed_m_s2=yy,paper_az_m_s2=-yy,accel_timestamp_sample_s=ats[ii],accel_available=bool(available),effective_accel_age_s=ti-ats[ii]) for ti,si,bi,ai,bf,af,pap,xx,yy,ii,available in zip(t[vis],s[vis],before_raw[vis],after_raw[vis],before[vis],after[vis],paper_after_raw[vis],ax[vis],ay[vis],ix[vis],usable[vis])])
    pm=P.topic(u,'actuator_outputs');rpm=P.topic(u,'rpm');pwm_mask=P.mask(P.tt(pm),t10-3,t90+4);rpm_mask=P.mask(P.tt(rpm),t10-3,t90+4)
    detail=dict(nominal_ramp_s=run['nom'],file=p.name,firmware_git_sha=u.msg_info_dict.get('ver_sw',''),b0_g=b0,b0_scope=C['bias_scope'],t10_s=t10,t90_s=t90,actual_10_90_s=t90-t10,q_std=q,r_std=r,force_limit_N=limit,clipped_before_full_log=nclip_before,clipped_after_full_log=nclip_after,median_native_acc_interval_s=float(np.median(np.diff(ats))),effective_accel_age_min_s=float(np.min((t-ats[ix])[vis])),effective_accel_age_max_s=float(np.max((t-ats[ix])[vis])),accel_unavailable_in_plot=int(sum(~usable[vis])),pwm_values_us=np.unique(pm['output[0]'][pwm_mask]).tolist(),nonzero_rpm_samples=int(sum(rpm['rpm_raw'][rpm_mask]!=0)),rpm_samples=int(sum(rpm_mask)),v_low_m_s=low,v_high_m_s=high)
    details.append(detail);return run

def main():
    record(CP,'frozen source coefficients, delay, bias and matched-filter settings');record(Path(__file__),'source-replay implementation');record(Path(__file__).with_name('plot_sensor_offline_1s.py'),'common drawing helpers');record(P.SP,'existing plotting style and ramp detector')
    target=OUT/'source_snapshot';target.mkdir(exist_ok=True)
    for p in (ROOT/C['source_snapshot_dir']).glob('*'):
        if p.is_file():shutil.copy2(p,target/p.name);record(target/p.name,'provided source or firmware-SHA history evidence')
    runs=[load(i) for i in C['files']]
    limits,ticks=P.shared_limits(runs);fig,aa=plt.subplots(2,3,figsize=(6.10,3.60),sharey=True)
    for j,run in enumerate(runs):
        for row in [0,1]:P.draw_axis(aa[row,j],run,row,limits,ticks,f'({chr(97+j)}) {run["nom"]} s')
        if j>0:
            for row in [0,1]:aa[row,j].tick_params(labelleft=False)
    aa[0,0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    aa[1,0].set_ylabel(r'离线补偿输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.095,right=.985,top=.975,bottom=.105,wspace=.10,hspace=.11)
    images=[P.save(fig,'motor_off_force_sensor_source_replay',list(aa.flat))]
    fig,aa=plt.subplots(2,1,figsize=(3.2,3.75),sharex=True,sharey=True)
    for row in [0,1]:P.draw_axis(aa[row],runs[0],row,limits,ticks,'1 s加速：源码规则离线补偿')
    aa[0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3);aa[1].set_ylabel(r'离线补偿输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.16,right=.98,top=.97,bottom=.105,hspace=.12)
    images.append(P.save(fig,'motor_off_force_sensor_1s_source_replay',list(aa),width_mm=80))
    csv('sensor_source_replay_metrics.csv',all_rows);csv('native_plot_data.csv',plotrows)
    summary=dict(source_formula_N='T_hat=(sensor2-b0+36.839*ay(t-0.03)-3.332*ax(t-0.03))*0.00980665',effective_A_kg=36.839*C['N_per_g'],effective_B_kg=3.332*C['N_per_g'],paper_axis_relation='a_z=-a_y, a_x=+a_x; both delayed by source fixed30ms',provided_source_git_head=C['provided_source_git_head'],trials=details,plot_filter=C['plot_filter'],status=C['status'],history_warning='ULog ver_sw1ab74a37 maps to committed source with +TFC_LOAD_M_KG*ay only and nonnegative force clipping; provided current source uses two-axis delayed parasitic compensation. Thus current source is not proven to be exact experimental firmware. No new graph is described as logged online output or independent validation.')
    for n,obj in [('analysis_summary.json',summary),('source_manifest.json',manifest),('render_verification.json',images)]: (OUT/n).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    print(pd.DataFrame(all_rows)[['nominal_ramp_s','signal','rmse_N','max_abs_N','mean_bias_N']].to_string(index=False))
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
