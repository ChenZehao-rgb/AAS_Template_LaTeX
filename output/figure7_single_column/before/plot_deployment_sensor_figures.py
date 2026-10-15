"""Source-backed figures for sections 3.3/3.4. No manuscript/legacy output edits.

Run: python data_process/plot_deployment_sensor_figures.py
Important: sensor2 is converted using the project's gram-force convention,
not a newly fitted calibration. Unverified source details remain explicit.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MultipleLocator, MaxNLocator
import numpy as np
import pandas as pd
from pyulog import ULog
import fitz

ROOT=Path(__file__).resolve().parents[1]
CFG_PATH=Path(__file__).with_name('deployment_sensor_figures_config.json')
CFG=json.loads(CFG_PATH.read_text(encoding='utf-8'))
OUT=ROOT/CFG['output_dir']
OUT.mkdir(parents=True,exist_ok=True)
STYLE_PATH=ROOT/'data/升力闭环测试/analyze_closed_loop.py'
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('existing_style',STYLE_PATH)
style=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=style
spec.loader.exec_module(style)
style.configure_plotting()
COLORS=['#0077BB','#EE7733','#009988','#666666']
MARKERS=['o','s','^','D']
LINES=['-','--','-.',':']
manifest=[]
geometry={}

def record(path,role):
    path=Path(path)
    if not any(r['path']==str(path) for r in manifest):
        manifest.append(dict(path=str(path),role=role,bytes=path.stat().st_size,
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

def csv(name,rows):
    pd.DataFrame(rows).to_csv(OUT/name,index=False,encoding='utf-8-sig',float_format='%.12g')

def topic(u,name):
    ds=[d.data for d in u.data_list if d.name==name and d.multi_id==0]
    if len(ds)!=1: raise ValueError(f'{name}: expected multi_id=0, found {len(ds)}')
    return ds[0]

def ts(d): return np.asarray(d['timestamp'],float)/1e6
def mask(t,a,b): return (t>=a)&(t<=b)
def values(d,k): return np.asarray(d[k],float)
def stats(y,m):
    z=y[m]
    if not len(z) or not np.all(np.isfinite(z)): raise ValueError('Empty/nonfinite metric data')
    return dict(samples=len(z),bias=float(np.mean(z)),rms=float(np.sqrt(np.mean(z*z))),peak_abs=float(np.max(abs(z))))

def save(fig,name,axes):
    # Matplotlib mathtext otherwise sends Chinese outside $...$ to a Latin-only
    # default font. Explicit SimSun on mixed labels preserves Chinese, while
    # custom mathtext still renders mathematics with Times New Roman.
    for ax in axes:
        for label in (ax.xaxis.label,ax.yaxis.label):
            if any('\u4e00'<=c<='\u9fff' for c in label.get_text()):
                label.set_fontfamily('SimSun')
    fig.canvas.draw()
    geometry[name]=dict(axes=[dict(position=list(a.get_position().bounds),xlim=list(a.get_xlim()),ylim=list(a.get_ylim()),yticks=list(a.get_yticks())) for a in axes])
    fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight',pad_inches=.03)
    fig.savefig(OUT/f'{name}.png',dpi=CFG['export']['png_dpi'],bbox_inches='tight',pad_inches=.03)
    doc=fitz.open(OUT/f'{name}.pdf')
    doc[0].get_pixmap(matrix=fitz.Matrix(2,2),alpha=False).save(OUT/f'{name}_pdf_check.png')
    # A 155 mm full-width paper figure preview; 180 dpi makes physical labels inspectable.
    width_in=155/25.4
    scale=width_in*180/doc[0].rect.width
    doc[0].get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False).save(OUT/f'{name}_155mm_preview.png')
    fonts=[]
    for f in doc[0].get_fonts(full=True):
        font=doc.extract_font(f[0]);fonts.append(dict(name=f[3],type=f[2],embedded_bytes=len(font[3])))
    geometry[name].update(pdf_points=list(doc[0].rect),fonts=fonts,text=doc[0].get_text())
    plt.close(fig)

def static_data():
    p=ROOT/CFG['static_csv'];record(p,'four user-confirmed sweeps of exported plateau means')
    df=pd.read_csv(p);df['csv_data_row_1based']=np.arange(1,len(df)+1)
    groups=[];all_rows=[];fits=[];audit=[]
    for g in CFG['static_groups']:
        first,last=g['csv_rows_1based'];raw=df.iloc[first-1:last].copy()
        raw['group']=g['id'];raw['excluded_stopped']=raw.rpm_mean<=0
        all_rows.extend(raw.to_dict('records'))
        work=raw[raw.rpm_mean>0].copy().reset_index(drop=True)
        # Only adjacent near-equal commands are combined; preserve every original mean above.
        ids=[0]
        for i in range(1,len(work)):
            ids.append(ids[-1]+int(abs(work.control_normalized.iloc[i]-work.control_normalized.iloc[i-1])>CFG['static_point_cluster_tolerance_u']))
        work['plateau_cluster']=ids
        points=work.groupby('plateau_cluster',sort=False).agg(u=('control_normalized','mean'),n=('rpm_mean','mean'),exported_means=('rpm_mean','size'),first_source_row=('csv_data_row_1based','min'),last_source_row=('csv_data_row_1based','max')).reset_index()
        points['group']=g['id'];csv(f"static_points_{g['id']}.csv",points.to_dict('records'))
        omega=points.n.to_numpy()*2*np.pi/60
        coeff=np.polyfit(omega,points.u,2)
        res=points.u-np.polyval(coeff,omega)
        fits.append(dict(group=g['id'],a_s2_per_rad2=coeff[0],b_s_per_rad=coeff[1],c_dimensionless=coeff[2],a_per_rpm2=coeff[0]*(2*np.pi/60)**2,b_per_rpm=coeff[1]*(2*np.pi/60),fit_rmse_u=np.sqrt(np.mean(res**2)),points=len(points),u_min=points.u.min(),u_max=points.u.max()))
        audit.append(dict(group=g['id'],raw_rows=len(raw),positive_rows=len(work),stopped_rows=sum(raw.rpm_mean<=0),adjacent_plateau_clusters=len(points),nominal_13_matches=len(points)==13,stable_samples_available=False,stable_window_reextractable=False))
        groups.append(dict(**g,points=points,coeff=coeff))
    csv('static_input_row_audit.csv',all_rows);csv('static_fits.csv',fits);csv('static_point_count_audit.csv',audit)
    low=max(g['points'].u.min() for g in groups);high=min(g['points'].u.max() for g in groups)
    knots=np.unique(np.concatenate([g['points'].u.to_numpy() for g in groups]))
    knots=knots[(knots>=low)&(knots<=high)]
    ui=np.unique(np.r_[np.linspace(low,high,1001),knots,low,high])
    speeds=[]
    for g in groups:
        pt=g['points'].sort_values('u');speeds.append(np.interp(ui,pt.u,pt.n))
    speeds=np.asarray(speeds);dif=(speeds.max(0)-speeds.min(0))/speeds.mean(0)*100
    table=pd.DataFrame(dict(u_cal=ui,**{g['id']+'_rpm':speeds[k] for k,g in enumerate(groups)},D_pct=dif))
    csv('static_common_u_spread.csv',table.to_dict('records'))
    imax=np.argmax(dif)
    result=dict(Dmax_pct=float(dif[imax]),u_at_Dmax=float(ui[imax]),common_u=[float(low),float(high)],interpretation='four sweeps in two cycles, not four independent test repetitions',method='piecewise linear n(u), no extrapolation, common interval; union of all knots plus dense sampling; adjacent duplicate plateau means averaged equally because sample counts unavailable')
    return groups,result

def dynamic_data():
    runs=[];rows=[];traces=[]
    for p in sorted(Path(CFG['dynamic_dir']).glob('*.ulg')):
        seq,load,nom,method=style.parse_filename(p)
        if method!='static': raise ValueError('Dynamic input is not static-map trial')
        record(p,'fixed final command dynamic inflow')
        u=ULog(str(p));c=topic(u,'thrust_control_data');ct=ts(c);v=values(c,'bet_freestream_m_s')
        sm,t10,t90,lo,hi=style.detect_ramp(ct,v,1/np.median(np.diff(ct)))
        r=topic(u,'rpm');rt=ts(r);n=-values(r,'rpm_raw')
        pre=mask(rt,t10-3,t10-.5);npre=np.mean(n[pre]);delta=100*(n-npre)/npre
        ev=mask(rt,t10,t90+3);steady=mask(rt,t90+2,t90+3)
        cmd=topic(u,'thrust_control');cmdt=ts(cmd);cv=values(cmd,'control[0]');cm=mask(cmdt,t10,t90+3)
        pwm=topic(u,'actuator_outputs');pwmt=ts(pwm);pv=values(pwm,'output[0]');pm=mask(pwmt,t10,t90+3)
        mc=topic(u,'actuator_motors');mct=ts(mc);mcm=mask(mct,t10,t90+3)
        es=stats(delta,ev);ss=stats(delta,steady)
        internal=values(c,'thrust_control_out[0]');cwin=mask(ct,t10,t90+3)
        row=dict(file=p.name,sequence=seq,nominal_reference_load_N=load,nominal_ramp_s=nom,t10_s=t10,t90_s=t90,actual_10_90_s=t90-t10,v_low_m_s=lo,v_high_m_s=hi,n_pre_rpm=npre,baseline_start_s=t10-3,baseline_end_s=t10-.5,steady_start_s=t90+2,steady_end_s=t90+3,evaluation_start_s=t10,evaluation_end_s=t90+3,u_cmd_min=np.min(cv[cm]),u_cmd_max=np.max(cv[cm]),u_cmd_mean=np.mean(cv[cm]),pwm_min_us=np.min(pv[pm]),pwm_max_us=np.max(pv[pm]),pwm_mean_us=np.mean(pv[pm]),u_pwm_1100_1900=(np.mean(pv[pm])-1100)/800,u_pwm_1000_2000=(np.mean(pv[pm])-1000)/1000,internal_controller_min=np.min(internal[cwin]),internal_controller_max=np.max(internal[cwin]),actuator_motors_control_min=np.min(mc['control[0]'][mcm]),actuator_motors_control_max=np.max(mc['control[0]'][mcm]),steady_mean_delta_pct=ss['bias'],disturbance_max_abs_delta_pct=es['peak_abs'],disturbance_rms_delta_pct=es['rms'],disturbance_samples=es['samples'],steady_samples=ss['samples'],rpm_filter='none; native samples',rpm_loop_active_values=';'.join(map(str,np.unique(c['rpm_loop_active[0]'][cwin]))),thrust_start_values=';'.join(map(str,np.unique(c['thrust_start'][cwin]))),firmware_sha=u.msg_info_dict.get('ver_sw',''))
        if row['u_cmd_max']-row['u_cmd_min']>1e-5 or row['pwm_max_us']-row['pwm_min_us']>1: raise ValueError('Applied command is not fixed')
        plotmask=mask(rt,t10-3,t90+4)
        traces.extend(dict(file=p.name,timestamp_s=t,tau_s=t-t10,n_rpm=nn,delta_n_pct=dd) for t,nn,dd in zip(rt[plotmask],n[plotmask],delta[plotmask]))
        runs.append(dict(path=p,row=row,rt=rt,tau=rt-t10,n=n,delta=delta,ct=ct,v=v,sm=sm,t10=t10,t90=t90))
        rows.append(row)
    csv('dynamic_all_9_trials_metrics.csv',rows);csv('dynamic_native_rpm_plot_data.csv',traces)
    selected=[r for r in runs if r['row']['nominal_ramp_s']==CFG['main_dynamic_nominal_ramp_s']]
    grid=np.arange(-3,max(r['t90']-r['t10'] for r in selected)+4,.01)
    vv=np.array([np.interp(grid,r['ct']-r['t10'],r['sm']) for r in selected])
    consistency=dict(selected_files=[r['path'].name for r in selected],max_pairwise_aligned_smoothed_v_difference_m_s=float(np.ptp(vv,axis=0).max()),actual_10_90_span_range_s=[float(min(r['t90']-r['t10'] for r in selected)),float(max(r['t90']-r['t10'] for r in selected))],high_plateau_range_m_s=[min(r['row']['v_high_m_s'] for r in selected),max(r['row']['v_high_m_s'] for r in selected)],representative_file=next(r['path'].name for r in selected if r['row']['nominal_reference_load_N']==20))
    csv('dynamic_main_inflow_comparison.csv',[dict(tau_s=t,**{f"v_{r['row']['nominal_reference_load_N']}N_m_s":vv[k,i] for k,r in enumerate(selected)}) for i,t in enumerate(grid)])
    return runs,selected,consistency

def plot_A(groups,spread,selected):
    fig,(a,b)=plt.subplots(2,1,figsize=(6.10,4.85))
    for k,g in enumerate(groups):
        pt=g['points'];n=np.linspace(pt.n.min(),pt.n.max(),300)
        a.plot(n,np.polyval(g['coeff'],n*2*np.pi/60),color=COLORS[k],ls=LINES[k],lw=1.1,zorder=2)
        a.plot(pt.n,pt.u,ls='none',marker=MARKERS[k],ms=3.5,mfc='white',mec=COLORS[k],mew=.8,color=COLORS[k],label=g['label'],zorder=3)
    a.set_xlabel(r'电机机械转速 $n$ (rpm)',labelpad=2)
    a.set_ylabel(r'归一化控制量 $u_{\mathrm{cal}}$')
    a.set_xlim(800,5900);a.set_ylim(.07,.96)
    a.xaxis.set_major_locator(MultipleLocator(1000));a.yaxis.set_major_locator(MultipleLocator(.2))
    style.panel_label(a,'(a) 四次静态扫描',y=.97)
    a.text(.025,.79,rf'$\max_j D_j={spread["Dmax_pct"]:.2f}\%$',transform=a.transAxes,fontsize=8)
    handles=[Line2D([0],[0],color=COLORS[k],ls=LINES[k],lw=1.1,marker=MARKERS[k],ms=3.5,mfc='white',mew=.8,label=g['label']) for k,g in enumerate(groups)]
    a.legend(handles=handles,loc='lower right',ncol=2,frameon=False,columnspacing=1,handlelength=2.6)
    xmax=max(r['t90']-r['t10'] for r in selected)+4
    for k,r in enumerate(selected):
        m=mask(r['tau'],-3,xmax)
        b.plot(r['tau'][m],r['delta'][m],color=COLORS[k],ls=LINES[k],lw=.85,marker=MARKERS[k],ms=2.8,mfc='white',mew=.7,markevery=max(1,sum(m)//13),label=rf'$u_{{0,\mathrm{{cmd}}}}={r["row"]["u_cmd_mean"]:.3f}$')
    rep=next(r for r in selected if r['row']['nominal_reference_load_N']==20)
    b.axvspan(0,rep['t90']-rep['t10'],color='.95',zorder=-3)
    b.axvline(0,color='.65',ls=':',lw=.7)
    b.axhline(0,color='.15',ls='--',lw=.7)
    for y in [-5,5]: b.axhline(y,color='.45',ls='--',lw=.7,zorder=1)
    ys=np.concatenate([r['delta'][mask(r['tau'],-3,xmax)] for r in selected]+[[-5,5]])
    lo=min(ys);hi=max(ys);padding=(hi-lo)*.10
    b.set_ylim(lo-padding,hi+padding);b.set_xlim(-3,xmax)
    b.yaxis.set_major_locator(MultipleLocator(5));b.xaxis.set_major_locator(MultipleLocator(1))
    b.set_xlabel(r'$\tau=t-t_{10}$ (s)',labelpad=2)
    b.set_ylabel(r'转速相对变化 $\delta n$ (%)')
    style.panel_label(b,'(b) 固定控制量，名义 1 s 加速',y=.97)
    b.legend(loc='lower right',frameon=False,ncol=3,columnspacing=.75,handlelength=2.5,fontsize=7)
    twin=b.twinx();m=mask(rep['ct']-rep['t10'],-3,xmax)
    twin.plot(rep['ct'][m]-rep['t10'],rep['v'][m],color='.64',ls='--',lw=.6,zorder=0)
    twin.set_ylim(-1,13);twin.yaxis.set_major_locator(MultipleLocator(5));twin.set_ylabel(r'来流速度 $V_\infty$ (m/s)',color='.45');twin.tick_params(axis='y',colors='.45')
    for ax in [a,b]: style.style_grid(ax)
    fig.subplots_adjust(left=.105,right=.90,top=.982,bottom=.085,hspace=.33)
    save(fig,'static_rpm_mapping_dynamic_inflow',[a,b,twin])

def sensor_data():
    """Before/after from each compensated record; preserve separate-file audit.

    Known limitation: no matched online filter implementation is supplied.
    Therefore main paired display is explicitly raw converted versus online
    compensated+filtered; raw-compensated metrics are retained as a sensitivity
    check. No inferred delay, no re-zeroing and no fitted compensation terms.
    """
    runs=[];rows=[];audit=[];traces=[]
    for p in sorted((ROOT/CFG['sensor_dir']).glob('*.ulg')):
        record(p,'sensor motor-off file inventory and paired-channel analysis')
        u=ULog(str(p));w=topic(u,'vehicle_angular_velocity');wt=ts(w)
        v=abs(values(w,'xyz[2]'))*1.5
        sm,t10,t90,lo,hi=style.detect_ramp(wt,v,1/np.median(np.diff(wt)))
        r=topic(u,'rpm');rt=ts(r);rm=mask(rt,t10-3,t90+4);rpm=values(r,'rpm_raw')[rm]
        pwm=topic(u,'actuator_outputs');pt=ts(pwm);pm=mask(pt,t10-3,t90+4)
        nominal=int(re.search(r'(\d+)s',p.name).group(1))
        audit.append(dict(file=p.name,nominal_ramp_s=nominal,t10_s=t10,t90_s=t90,actual_10_90_s=t90-t10,v_low_m_s=lo,v_high_m_s=hi,pwm_min_us=np.min(pwm['output[0]'][pm]),pwm_max_us=np.max(pwm['output[0]'][pm]),rpm_samples=len(rpm),rpm_zero_samples=sum(rpm==0),rpm_nonzero_samples=sum(rpm!=0),rpm_min=np.min(rpm),rpm_max=np.max(rpm),rpm_state='PWM=disarmed1000; sparse encoder pulses present, no independently proven strictly zero shaft speed',firmware_sha=u.msg_info_dict.get('ver_sw','')))
        raw=topic(u,'pressure_force_sensor');t=ts(raw)
        force=values(raw,'sensor2')*CFG['sensor_conversion']['N_per_sensor_unit']
        ft=topic(u,'thrust_data');tf=ts(ft)
        filtered=values(ft,'thrust_kalman_filter_data_1');fraw=values(ft,'thrust_raw_data_1')
        signals=([('before_raw_converted',t,force),('after_online_filtered',tf,filtered),('after_online_raw',tf,fraw)]
                 if p.name.startswith('已') else [('separate_uncompensated_raw_converted',t,force)])
        for name,tt,yy in signals:
            ev=mask(tt,t10,t90+3);ss=stats(yy,ev);pre=stats(yy,mask(tt,t10-3,t10-.5));post=stats(yy,mask(tt,t90+2,t90+3))
            rows.append(dict(file=p.name,nominal_ramp_s=nominal,signal=name,t10_s=t10,t90_s=t90,actual_10_90_s=t90-t10,window_start_s=t10,window_end_s=t90+3,rmse_N=ss['rms'],max_abs_N=ss['peak_abs'],mean_bias_N=ss['bias'],samples=ss['samples'],pre_mean_N=pre['bias'],post_mean_N=post['bias'],zero_bias_processing='none offline; do not independently recenter signals',filter='logged online Kalman field' if name=='after_online_filtered' else 'no offline filter',conversion_status=CFG['sensor_conversion']['status']))
            vis=mask(tt,t10-3,t90+4)
            traces.extend(dict(file=p.name,signal=name,timestamp_s=ttt,tau_s=ttt-t10,force_N=y) for ttt,y in zip(tt[vis],yy[vis]))
        if p.name.startswith('已'):
            runs.append(dict(path=p,nominal=nominal,t10=t10,t90=t90,t=t,force=force,tf=tf,filtered=filtered,raw=fraw,wt=wt,v=v))
    csv('sensor_all_6_files_audit.csv',audit);csv('sensor_paired_metrics.csv',rows);csv('sensor_native_plot_data.csv',traces)
    return sorted(runs,key=lambda r:r['nominal']),rows

def plot_B(runs,rows):
    fig,axes=plt.subplots(2,3,figsize=(6.10,3.60),sharey=True)
    yy=[]
    for r in runs:
        end=r['t90']-r['t10']+4
        yy.extend([r['force'][mask(r['t']-r['t10'],-3,end)],r['filtered'][mask(r['tf']-r['t10'],-3,end)]])
    z=np.concatenate(yy);span=max(z)-min(z);low=min(z)-.1*span;high=max(z)+.17*span
    # Same rounded limits and major ticks on every one of the six axes.
    ticks=MaxNLocator(nbins=5).tick_values(low,high);limits=(ticks[0],ticks[-1])
    for j,r in enumerate(runs):
        ramp=r['t90']-r['t10'];end=ramp+4
        for i,(tt,y,key) in enumerate([(r['t'],r['force'],'before_raw_converted'),(r['tf'],r['filtered'],'after_online_filtered')]):
            ax=axes[i,j];tau=tt-r['t10'];m=mask(tau,-3,end)
            ax.plot(tau[m],y[m],color=COLORS[1-i],ls='-',lw=.85,marker=['s','o'][i],ms=2.7,mfc='white',mew=.7,markevery=max(1,sum(m)//13))
            ax.axhline(0,color='.12',ls='--',lw=.7,zorder=1)
            ax.axvline(0,color='.55',ls=':',lw=.7,zorder=1)
            ax.axvspan(0,ramp,color='.95',zorder=-3)
            ax.set_xlim(-3,end);ax.set_ylim(*limits);ax.set_yticks(ticks)
            ax.xaxis.set_major_locator(MultipleLocator(2 if r['nominal']<10 else 4))
            style.style_grid(ax)
            metric=next(x for x in rows if x['file']==r['path'].name and x['signal']==key)
            ax.text(.97,.14 if i==0 else .95,f'RMSE = {metric["rmse_N"]:.2f} N',transform=ax.transAxes,ha='right',va='bottom' if i==0 else 'top',fontsize=7.5)
            if i==0:
                mark='*' if r['nominal']==1 else ''
                style.panel_label(ax,f'({chr(97+j)}) 标称 {r["nominal"]} s{mark}',x=.035,y=.97)
                ax.tick_params(labelbottom=False)
            else: ax.set_xlabel(r'$\tau=t-t_{10}$ (s)',labelpad=2)
            if j>0: ax.tick_params(labelleft=False)
    axes[0,0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    axes[1,0].set_ylabel(r'补偿后滤波输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.095,right=.985,top=.975,bottom=.105,wspace=.10,hspace=.11)
    save(fig,'motor_off_force_sensor_compensation',list(axes.flat))

def main():
    record(STYLE_PATH,'latest plotting style and inflow detector for figures 8-12')
    record(CFG_PATH,'selection and processing configuration')
    record(ROOT/'data/旋转测试数据汇总表_升力标定实验残差.xlsx','evidence for project gram-force unit convention, not proof of these ULogs calibration')
    groups,spread=static_data()
    runs,selected,consistency=dynamic_data()
    plot_A(groups,spread,selected)
    if CFG['sensor_conversion'] is not None:
        sensors,metrics=sensor_data();plot_B(sensors,metrics)
    else:
        sensors=[];metrics=[]
    summary=dict(static=spread,dynamic_inflow=consistency,sensor_conversion=CFG['sensor_conversion'],sensor_main_files=[r['path'].name for r in sensors],limitations=['CSV plateau extraction cannot be re-audited without native static logs','Static CSV normalized command node is not recoverable from the two columns; u_cal and u_cmd are distinct labels','Nominal 1s compensated log actually has 4.083s 10-90% acceleration','Sensor-coordinate projection, gravity removal, zeroing, online filter and coefficient provenance are not source-verified at user direction','Before-raw versus after-filtered display is not an isolated compensation-only or filter-matched validation','Motor-off files contain sparse nonzero encoder readings despite fixed disarmed PWM; no RPM outliers removed or strict zero invented'])
    (OUT/'analysis_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'source_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'render_verification.json').write_text(json.dumps(geometry,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
