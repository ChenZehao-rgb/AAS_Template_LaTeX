"""Reconstruct real 1s sensor compensation with fixed manuscript Eq.(23).

Leaves all previous figures and manuscript unchanged. Exports a revised 6-axis
figure (only 1s replaced) and a standalone 1s raw/raw comparison, with traceable
native data, metrics, channel signs, and baseline handling.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import hashlib
import importlib.util
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator,MaxNLocator
import numpy as np
import pandas as pd
from pyulog import ULog
import fitz

ROOT=Path(__file__).resolve().parents[1]
CP=Path(__file__).with_name('sensor_offline_1s_config.json')
C=json.loads(CP.read_text(encoding='utf-8'))
OUT=ROOT/C['output_dir'];OUT.mkdir(parents=True,exist_ok=True)
SP=ROOT/'data/升力闭环测试/analyze_closed_loop.py'
spec=importlib.util.spec_from_file_location('style_source',SP)
S=importlib.util.module_from_spec(spec);sys.modules[spec.name]=S;spec.loader.exec_module(S)
S.configure_plotting()
BLUE='#0077BB';ORANGE='#EE7733'
sources=[];metrics=[];plots=[]

def record(p,role):
    p=Path(p);sources.append(dict(path=str(p),role=role,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
def topic(u,n):
    ds=[d.data for d in u.data_list if d.name==n and d.multi_id==0]
    if len(ds)!=1: raise ValueError(f'{n}: expected one multi_id0, found {len(ds)}')
    return ds[0]
def tt(d,key='timestamp'):return np.asarray(d[key],float)/1e6
def val(d,key):return np.asarray(d[key],float)
def mask(t,lo,hi):return (t>=lo)&(t<=hi)
def stats(y,m):
    v=y[m]
    if not len(v) or not np.all(np.isfinite(v)):raise ValueError('Empty/nonfinite valid samples')
    return dict(samples=int(len(v)),rmse_N=float(np.sqrt(np.mean(v*v))),max_abs_N=float(np.max(abs(v))),mean_bias_N=float(np.mean(v)))
def metric(run,name,t,y):
    m=mask(t,run['t10'],run['t90']+C['evaluation_end_after_t90_s'])
    row=dict(file=run['path'].name,nominal_ramp_s=run['nom'],signal=name,
             t10_s=run['t10'],t90_s=run['t90'],actual_10_90_s=run['t90']-run['t10'],
             evaluation_start_s=run['t10'],evaluation_end_s=run['t90']+C['evaluation_end_after_t90_s'],**stats(y,m))
    metrics.append(row);return row
def csv(name,data):pd.DataFrame(data).to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.12g')

def load_run(rel,nom):
    p=ROOT/rel;record(p,'real1s offline reconstruction input' if nom==1 else 'preserved online comparison column')
    u=ULog(str(p));w=topic(u,'vehicle_angular_velocity');wt=tt(w);v=abs(val(w,'xyz[2]'))*C['inflow_arm_length_m']
    sm,t10,t90,lo,hi=S.detect_ramp(wt,v,1/np.median(np.diff(wt)))
    raw=topic(u,C['force_topic']);t=tt(raw);before=(val(raw,C['force_field'])-C['force_offset_units'])*C['force_N_per_unit']
    run=dict(path=p,nom=nom,t10=t10,t90=t90,t=t,before=before,wt=wt,v=v,sm=sm,low=lo,high=hi,firmware_sha=u.msg_info_dict.get('ver_sw',''))
    ptopic=topic(u,'actuator_outputs');pwm_t=tt(ptopic);pm=mask(pwm_t,t10-3,t90+4)
    rpm=topic(u,'rpm');rpm_t=tt(rpm);rm=mask(rpm_t,t10-3,t90+4)
    run['state']=dict(pwm_min_us=float(np.min(ptopic['output[0]'][pm])),pwm_max_us=float(np.max(ptopic['output[0]'][pm])),rpm_samples=int(sum(rm)),nonzero_rpm_samples=int(sum(rpm['rpm_raw'][rm]!=0)),rpm_min=float(np.min(rpm['rpm_raw'][rm])),rpm_max=float(np.max(rpm['rpm_raw'][rm])))
    if nom==1:
        a=topic(u,C['acceleration_topic']);at=tt(a,C['acceleration_time_field'])
        pre=mask(at,t10+C['acceleration_baseline_relative_t10_s'][0],t10+C['acceleration_baseline_relative_t10_s'][1])
        z=val(a,C['axial_field'])*C['axial_sign'];x=val(a,C['radial_field'])*C['radial_sign']
        z0=float(np.mean(z[pre]));x0=float(np.mean(x[pre]))
        valid=mask(t,at[0],at[-1])
        if not valid.all():
            # No extrapolation: synchronization must cover the entire visible
            # and evaluation windows. Exterior logging samples aren't plotted.
            if not valid[mask(t,t10-3,t90+4)].all():raise ValueError('Acceleration does not cover complete force plot window')
        az=np.full_like(t,np.nan);ax=np.full_like(t,np.nan)
        az[valid]=np.interp(t[valid],at,z-z0);ax[valid]=np.interp(t[valid],at,x-x0)
        comp_z=C['A_kg']*az;comp_x=C['B_kg']*ax
        after=before-comp_z-comp_x
        run.update(after_t=t,after=after,az=az,ax=ax,acc_baseline_z=z0,acc_baseline_x=x0,
                   acc_time=at,acc_z=z,acc_x=x,method='offline Eq23, no added filter',native_acc_median_dt_s=float(np.median(np.diff(at))),
                   acc_publish_minus_sample_median_s=float(np.median(tt(a)-at)),outside_acc_range_force_samples=int(sum(~valid)))
        m=mask(t,t10-3,t90+4)
        csv('offline_1s_native_force_and_compensation.csv',[dict(timestamp_s=ti,tau_s=ti-t10,sensor2=si,T_N=tiN,a_z_baseline_removed_m_s2=zi,a_x_baseline_removed_m_s2=xi,Aaz_N=za,Bax_N=xa,T_hat_N=ci) for ti,si,tiN,zi,xi,za,xa,ci in zip(t[m],raw[C['force_field']][m],before[m],az[m],ax[m],comp_z[m],comp_x[m],after[m])])
        am=mask(at,t10-3,t90+4)
        csv('offline_1s_native_acceleration.csv',[dict(timestamp_sample_s=ti,tau_s=ti-t10,axis_y_specific_force_m_s2=zi,axis_x_specific_force_m_s2=xi,a_z_m_s2=zi-z0,a_x_m_s2=xi-x0) for ti,zi,xi in zip(at[am],z[am],x[am])])
    else:
        f=topic(u,'thrust_data');run.update(after_t=tt(f),after=val(f,'thrust_kalman_filter_data_1'),method='logged online compensated+filtered')
    run['before_metric']=metric(run,'before_raw_converted',t,before)
    run['after_metric']=metric(run,'after_offline_eq23_raw' if nom==1 else 'after_online_filtered',run['after_t'],run['after'])
    for name,times,y in [('before',t,before),('after',run['after_t'],run['after'])]:
        mm=mask(times,t10-3,t90+4)
        plots.extend(dict(file=p.name,nominal_ramp_s=nom,signal=name,timestamp_s=ti,tau_s=ti-t10,force_N=yi) for ti,yi in zip(times[mm],y[mm]))
    return run

def shared_limits(runs):
    yy=[]
    for r in runs:
        for t,y in [(r['t'],r['before']),(r['after_t'],r['after'])]:yy.append(y[mask(t,r['t10']-3,r['t90']+4)])
    yy=np.concatenate(yy)
    if not np.isfinite(yy).all():raise ValueError('Nonfinite visible force')
    span=np.ptp(yy);ticks=MaxNLocator(nbins=5).tick_values(min(yy)-span*.06,max(yy)+span*.06)
    return (ticks[0],ticks[-1]),ticks

def draw_axis(ax,r,i,limits,ticks,panel):
    t,y=(r['t'],r['before']) if i==0 else (r['after_t'],r['after'])
    tau=t-r['t10'];end=r['t90']-r['t10']+4;mm=mask(tau,-3,end)
    ax.plot(tau[mm],y[mm],color=ORANGE if i==0 else BLUE,lw=.85,marker='s' if i==0 else 'o',ms=2.7,mfc='white',mew=.7,markevery=max(1,sum(mm)//13))
    ax.axhline(0,color='.12',ls='--',lw=.7);ax.axvline(0,color='.55',ls=':',lw=.7)
    ax.axvspan(0,r['t90']-r['t10'],color='.95',zorder=-3);S.style_grid(ax)
    ax.set_xlim(-3,end);ax.set_ylim(*limits);ax.set_yticks(ticks)
    ax.xaxis.set_major_locator(MultipleLocator(1 if r['nom']==1 else (2 if r['nom']==5 else 4)))
    m=r['before_metric'] if i==0 else r['after_metric']
    # Bottom right avoids the traces near zero; full native dips remain visible.
    ax.text(.97,.08,f'RMSE = {m["rmse_N"]:.2f} N',transform=ax.transAxes,ha='right',va='bottom',fontsize=7.5)
    if i==0:
        S.panel_label(ax,panel,x=.035,y=.97);ax.tick_params(labelbottom=False)
    else:ax.set_xlabel(r'$\tau=t-t_{10}$ (s)',labelpad=2)

def save(fig,name,axes,width_mm=155):
    for ax in axes:
        for label in [ax.xaxis.label,ax.yaxis.label]:
            if any('\u4e00'<=c<='\u9fff' for c in label.get_text()):label.set_fontfamily('SimSun')
    fig.canvas.draw();fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',pad_inches=.03)
    fig.savefig(OUT/f'{name}.png',dpi=C['export_dpi'],bbox_inches='tight',pad_inches=.03)
    d=fitz.open(OUT/f'{name}.pdf');p=d[0]
    p.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(OUT/f'{name}_pdf_check.png')
    scale=width_mm/25.4*180/p.rect.width
    p.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(OUT/f'{name}_{width_mm}mm_preview.png')
    fonts=[dict(name=f[3],embedded_bytes=len(d.extract_font(f[0])[3])) for f in p.get_fonts(full=True)]
    info=dict(file=name,intended_paper_width_mm=width_mm,axes=[dict(xlim=list(a.get_xlim()),ylim=list(a.get_ylim()),yticks=list(a.get_yticks()),position=list(a.get_position().bounds)) for a in axes],fonts=fonts,raster_image_objects=len(p.get_images()),pdf_text=p.get_text(),pdf_page_points=list(p.rect))
    plt.close(fig);return info

def main():
    record(CP,'explicit user-confirmed axis mapping and fixed processing configuration');record(Path(__file__),'offline calculation and plot implementation');record(SP,'existing plot style and inflow detector')
    runs=[load_run(C['source_1s'],1),load_run(C['source_5s_online'],5),load_run(C['source_10s_online'],10)]
    limits,ticks=shared_limits(runs);fig,axes=plt.subplots(2,3,figsize=(6.10,3.60),sharey=True)
    for j,r in enumerate(runs):
        for i in [0,1]:draw_axis(axes[i,j],r,i,limits,ticks,f'({chr(97+j)}) {r["nom"]} s'+('，离线' if j==0 else ''))
        if j>0:
            for i in [0,1]:axes[i,j].tick_params(labelleft=False)
    axes[0,0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    axes[1,0].set_ylabel(r'补偿后输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.095,right=.985,top=.975,bottom=.105,wspace=.10,hspace=.11)
    figures=[save(fig,'motor_off_force_sensor_compensation_offline_1s',list(axes.flat))]
    fig,aa=plt.subplots(2,1,figsize=(3.2,3.75),sharex=True,sharey=True)
    for i in [0,1]:draw_axis(aa[i],runs[0],i,limits,ticks,'1 s加速：式(23)离线补偿')
    aa[0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    aa[1].set_ylabel(r'离线补偿输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.16,right=.98,top=.97,bottom=.105,hspace=.12)
    figures.append(save(fig,'motor_off_force_sensor_1s_eq23',list(aa),width_mm=80))
    csv('sensor_revised_metrics.csv',metrics);csv('sensor_revised_native_plot_data.csv',plots)
    r=runs[0];ev=mask(r['t'],r['t10'],r['t90']+3)
    peakb=np.flatnonzero(ev)[np.argmax(abs(r['before'][ev]))];peaka=np.flatnonzero(ev)[np.argmax(abs(r['after'][ev]))]
    summary=dict(formula=C['equation'],A_kg=C['A_kg'],B_kg=C['B_kg'],axis_confirmation=C['axes_provenance'],baseline_z_m_s2=r['acc_baseline_z'],baseline_x_m_s2=r['acc_baseline_x'],baseline_start_s=r['t10']-3,baseline_end_s=r['t10']-.5,acc_time_field=C['acceleration_time_field'],median_native_acc_sampling_interval_s=r['native_acc_median_dt_s'],median_publish_minus_sample_s=r['acc_publish_minus_sample_median_s'],t10_s=r['t10'],t90_s=r['t90'],actual_10_90_s=r['t90']-r['t10'],evaluation_window_s=[r['t10'],r['t90']+3],before=r['before_metric'],after=r['after_metric'],before_peak=dict(tau_s=float(r['t'][peakb]-r['t10']),T_N=float(r['before'][peakb])),after_peak=dict(tau_s=float(r['t'][peaka]-r['t10']),T_hat_N=float(r['after'][peaka])),motor_state=r['state'],conditional_force_units=C['force_conversion_provenance'],processing=dict(force_zero=C['force_zero_processing'],acc_zero=C['acceleration_zero_processing'],filter=C['additional_filter'],synchronization=C['synchronization']),result_improves_rmse=r['after_metric']['rmse_N']<r['before_metric']['rmse_N'],independent_validation_status='Unknown coefficient provenance; offline application to provided data, not actual online recorded output')
    (OUT/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'source_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'render_verification.json').write_text(json.dumps(figures,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
