"""Reconstruct the user-confirmed compensation formula without force clipping.

Run: python data_process/plot_sensor_new_1s_reconstruction.py
The log does not record module-start b0, so use its first 20 force samples.
This is an offline reconstruction, not recovery of exact firmware states.
"""
from pathlib import Path
import sys
sys.dont_write_bytecode = True
import importlib.util
import json
import hashlib
import shutil
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from pyulog import ULog

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/sensor_new_1s_reconstruction'
OUT.mkdir(parents=True, exist_ok=True)
DEPLOY = ROOT / 'output/deployment_sensor_figures'
spec = importlib.util.spec_from_file_location('source_replay', Path(__file__).with_name('plot_sensor_source_replay.py'))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)
P = R.P
P.OUT = OUT
SOURCE = ROOT / 'data/传感器补偿/补偿-rawdate显示限幅.ulg'
G = R.C['N_per_g']
manifest = []


def record(path, role):
    manifest.append(dict(path=str(path), role=role, sha256=hashlib.sha256(path.read_bytes()).hexdigest()))


def metric(t, y, t10, t90):
    return P.stats(y, P.mask(t, t10, t90 + 3))


def reconstruct():
    u = ULog(str(SOURCE))
    raw = P.topic(u, 'pressure_force_sensor')
    t = P.tt(raw)
    sensor = P.val(raw, 'sensor2')
    b0 = float(np.mean(sensor[:20]))
    before = (sensor - b0) * G
    a = P.topic(u, 'vehicle_acceleration')
    ax, ay, ix, usable, ats = R.delayed_accel(a, t)
    axial = 36.839 * ay * G
    radial = -3.332 * ax * G
    after_raw = before + axial + radial
    q = float(u.initial_parameters['TFC_SD_ES'])
    r = float(u.initial_parameters['TFC_SD_ME'])
    assert not any(key in ['TFC_SD_ES', 'TFC_SD_ME'] for _, key, _ in u.changed_parameters)
    # Infinite bound removes both input and output clipping. Filter state is
    # replayed through the entire log before selecting the displayed window.
    after = R.filter_source(t, after_raw, q, r, np.inf)
    before_filtered = R.filter_source(t, before, q, r, np.inf)
    w = P.topic(u, 'vehicle_angular_velocity')
    wt = P.tt(w)
    v = abs(P.val(w, 'xyz[2]')) * 1.5
    _, t10, t90, low, high = P.S.detect_ramp(wt, v, 1 / np.median(np.diff(wt)))
    vis = P.mask(t, t10 - 3, t90 + 4)
    assert usable[vis].all()
    f = P.topic(u, 'thrust_data')
    ft = P.tt(f)
    fm = P.mask(ft, t10 - 3, t90 + 4)
    d = pd.DataFrame(dict(timestamp_s=t, tau_s=t-t10, sensor2_g=sensor,
                         b0_g=b0, before_raw_N=before, before_matched_filter_N=before_filtered,
                         ax_delayed_m_s2=ax, ay_delayed_m_s2=ay,
                         accel_timestamp_sample_s=ats[ix], effective_accel_age_s=t-ats[ix],
                         axial_compensation_N=axial, radial_compensation_N=radial,
                         after_unclipped_raw_N=after_raw, after_unclipped_filtered_N=after,
                         in_plot=vis, in_evaluation=P.mask(t, t10, t90+3)))
    d.to_csv(OUT/'reconstructed_1s_full_log.csv', index=False, encoding='utf-8-sig', float_format='%.12g')
    d.loc[vis].to_csv(OUT/'reconstructed_1s_plot_data.csv', index=False, encoding='utf-8-sig', float_format='%.12g')
    pd.DataFrame(dict(timestamp_s=ft[fm], tau_s=ft[fm]-t10,
                      logged_clipped_raw_N=f['thrust_raw_data_1'][fm],
                      logged_clipped_filtered_N=f['thrust_kalman_filter_data_1'][fm])).to_csv(
                          OUT/'logged_clipped_reference.csv', index=False, encoding='utf-8-sig')
    details = dict(source=str(SOURCE), formula='T_hat=(sensor2-b0+36.839*ay(t-0.030)-3.332*ax(t-0.030))*0.00980665',
                   formula_provenance='User confirmed this formula in the current conversation',
                   b0_g=b0, b0_method='first 20 logged sensor2 samples, same bias for both traces; module-start bias is not logged',
                   t10_s=t10, t90_s=t90, actual_10_90_s=t90-t10, inflow_low_m_s=low, inflow_high_m_s=high,
                   filter_q_std=q, filter_r_std=r, clipping='none, before or after filtering',
                   firmware_sha=u.msg_info_dict.get('ver_sw'),
                   visible_logged_raw_zero_samples=int(sum(f['thrust_raw_data_1'][fm] == 0)),
                   visible_logged_raw_samples=int(sum(fm)),
                   visible_unclipped_raw_range_N=[float(after_raw[vis].min()), float(after_raw[vis].max())],
                   before_raw=metric(t,before,t10,t90), before_matched_filter=metric(t,before_filtered,t10,t90),
                   after_unclipped_raw=metric(t,after_raw,t10,t90), after_unclipped_filtered=metric(t,after,t10,t90),
                   startup_dropouts=[dict(timestamp_s=x.timestamp/1e6, duration_ms=x.duration) for x in u.dropouts],
                   plot_window_s=[t10-3,t90+4], evaluation_window_s=[t10,t90+3])
    run = dict(path=SOURCE, nominal=1, t10=t10, t90=t90, t=t, force=before,
               tf=t, filtered=after, before_metric=details['before_raw'], after_metric=details['after_unclipped_filtered'])
    return run, details


def old_run(nom):
    name = '已补偿--5s加速-无转速测试.ulg' if nom==5 else '已补偿-10s加速-无转速测试.ulg'
    path = ROOT/'data/传感器补偿'/name
    record(path, 'preserved 5s/10s original online comparison')
    u = ULog(str(path))
    w = P.topic(u, 'vehicle_angular_velocity'); wt=P.tt(w)
    _,t10,t90,_,_=P.S.detect_ramp(wt, abs(P.val(w,'xyz[2]'))*1.5,1/np.median(np.diff(wt)))
    raw=P.topic(u,'pressure_force_sensor');t=P.tt(raw);before=P.val(raw,'sensor2')*.0098
    f=P.topic(u,'thrust_data');ft=P.tt(f);after=P.val(f,'thrust_kalman_filter_data_1')
    return dict(path=path,nominal=nom,t10=t10,t90=t90,t=t,force=before,tf=ft,filtered=after,
                before_metric=metric(t,before,t10,t90),after_metric=metric(ft,after,t10,t90))


def draw(ax,r,row,limits,ticks,standalone=False):
    t,y=(r['t'],r['force']) if row==0 else (r['tf'],r['filtered'])
    m=P.mask(t,r['t10']-3,r['t90']+4)
    ax.plot(t[m]-r['t10'],y[m],color=P.ORANGE if row==0 else P.BLUE,lw=.85,
            marker='s' if row==0 else 'o',ms=2.7,mfc='white',mew=.7,markevery=max(1,sum(m)//13))
    ax.axhline(0,color='.12',ls='--',lw=.7)
    ax.axvline(0,color='.55',ls=':',lw=.7)
    ax.axvspan(0,r['t90']-r['t10'],color='.95',zorder=-3)
    ax.set_xlim(-3,r['t90']-r['t10']+4);ax.set_ylim(*limits);ax.set_yticks(ticks)
    ax.xaxis.set_major_locator(MultipleLocator(1 if r['nominal']==1 else (2 if r['nominal']==5 else 4)))
    P.S.style_grid(ax)
    met=r['before_metric'] if row==0 else r['after_metric']
    ax.text(.97,.08 if row==0 else .95,f'RMSE = {met["rmse_N"]:.2f} N',transform=ax.transAxes,
            ha='right',va='bottom' if row==0 else 'top',fontsize=7.5)
    if row==0:
        P.S.panel_label(ax, f'({chr(97+[1,5,10].index(r["nominal"]))}) {r["nominal"]} s',x=.035,y=.97)
        ax.tick_params(labelbottom=False)
    else:
        ax.set_xlabel(r'$\tau=t-t_{10}$ (s)',labelpad=2)


def main():
    for p,role in [(SOURCE,'new true 1s source log'),(Path(__file__),'reconstruction and rendering'),
                   (Path(R.__file__),'fixed delay and Kalman helpers'),
                   (ROOT/'data_process/sensor_source_replay_config.json','frozen source formula and filter settings'),
                   (P.SP,'existing chart style and inflow detector'),
                   (ROOT/'output/sensor_offline_1s/source_snapshot/thrust_feedback_control_bemt.cpp','provided source formula snapshot')]:record(p,role)
    run,summary=reconstruct()
    runs=[run,old_run(5),old_run(10)]
    row_limits=[(-6,4),(-6,4)]
    row_ticks=[np.arange(-6.,5.,2.),np.arange(-6.,5.,2.)]
    fig,aa=plt.subplots(2,1,figsize=(3.2,3.75),sharex=True)
    for row in [0,1]:draw(aa[row],run,row,row_limits[row],row_ticks[row],True)
    aa[0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    aa[1].set_ylabel(r'离线补偿滤波输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.16,right=.98,top=.97,bottom=.105,hspace=.12)
    rendered=[P.save(fig,'motor_off_force_sensor_1s_reconstructed',list(aa),width_mm=80)]
    fig,aa=plt.subplots(2,3,figsize=(6.10,3.60),sharey='row')
    for j,r in enumerate(runs):
        for row in [0,1]:
            draw(aa[row,j],r,row,row_limits[row],row_ticks[row])
            if j>0:aa[row,j].tick_params(labelleft=False)
    aa[0,0].set_ylabel(r'未补偿输出 $T$ (N)',labelpad=3)
    aa[1,0].set_ylabel(r'补偿后滤波输出 $\hat{T}$ (N)',labelpad=3)
    fig.subplots_adjust(left=.095,right=.985,top=.975,bottom=.105,wspace=.10,hspace=.11)
    rendered.append(P.save(fig,'motor_off_force_sensor_compensation',list(aa.flat)))
    summary['limitations']=[
        'Offline source-formula reconstruction, not exact experimental firmware replay: actual module-start b0 and full-rate acceleration history were not logged.',
        'The formula was confirmed by the user; it does not exactly reproduce the unclipped logged channel. No coefficient or time shift fitted to reduce residuals.',
        '1s uses one shared first20 bias and 0.00980665 N/g; original 5s/10s retain their previous uncentered 0.0098 N/unit convention.',
        'Top row raw versus bottom row filtered is retained from original layout; matched-filter metrics are also exported.',
        'All raw samples are retained without force clipping. Acceleration synchronization uses latest available sample at or before t-30ms, no linear extrapolation.'
    ]
    backup=DEPLOY/'before_new_true_1s'
    backup.mkdir(exist_ok=True)
    stem='motor_off_force_sensor_compensation'
    for suffix in ['.pdf','.png','_pdf_check.png','_155mm_preview.png']:
        original=DEPLOY/(stem+suffix)
        if original.exists() and not (backup/original.name).exists():shutil.copy2(original,backup/original.name)
        shutil.copy2(OUT/(stem+suffix),original)
    for name,obj in [('analysis_summary.json',summary),('source_manifest.json',manifest),('render_verification.json',rendered)]:
        (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
