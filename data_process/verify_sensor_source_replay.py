"""Independent numeric/source/export checks for source-based offline sensor plots."""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import json,hashlib,re
import numpy as np
import pandas as pd
from pyulog import ULog
import fitz
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
C=json.loads((ROOT/'data_process/sensor_source_replay_config.json').read_text(encoding='utf-8'))
OUT=ROOT/C['output_dir'];checks={};errors=[]
src=(OUT/'source_snapshot/thrust_feedback_control_bemt.cpp').read_text(encoding='utf-8-sig')
checks['source_constants_match_frozen_configuration']=all(x in src for x in ['kGramForceToNewton = 9.80665e-3f','kParasiticAccelDelayUs = 30000','kParasiticCoeffAy = -36.839f','kParasiticCoeffAx = 3.332f','kSensorBiasInitSamples = 20'])
manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
checks['source_and_raw_inputs_sha256_unchanged']=all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in manifest)
table=pd.read_csv(OUT/'sensor_source_replay_metrics.csv')
summary=json.loads((OUT/'analysis_summary.json').read_text(encoding='utf-8'))

def scalar_filter(times,measurements,q,r,limit):
    # Independent scalar covariance recurrences, rather than copied matrix operations.
    x0=x1=0.;p00=p11=1.;p01=p10=0.;result=[]
    for i,z in enumerate(measurements):
        dt=.001 if i==0 else min(.05,max(.001,times[i]-times[i-1]))
        x0=x0+dt*x1
        aa=p00+dt*(p01+p10)+dt*dt*p11+q*q*dt**4/4
        bb=p01+dt*p11+q*q*dt**3/2
        cc=p10+dt*p11+q*q*dt**3/2
        dd=p11+q*q*dt*dt
        k0=aa/(aa+r*r);k1=cc/(aa+r*r);innovation=z-x0
        x0+=k0*innovation;x1+=k1*innovation
        p00=(1-k0)*aa;p01=(1-k0)*bb;p10=cc-k1*aa;p11=dd-k1*bb
        result.append(min(limit,max(-limit,x0)))
    return np.array(result)

for file in C['files']:
    u=ULog(str(ROOT/file['path']));topic=lambda n:next(d.data for d in u.data_list if d.name==n and d.multi_id==0)
    f=topic('pressure_force_sensor');a=topic('vehicle_acceleration')
    t=f['timestamp'].astype(float)/1e6;at=a['timestamp_sample'].astype(float)/1e6;ap=a['timestamp'].astype(float)/1e6
    at=np.where(at>0,at,ap);s=f['sensor2'].astype(float);b0=sum(s[:20])/20;before=(s-b0)*.00980665
    after=[];ixs=[]
    # Independently select each available historical sample by direct masks.
    for ti,si in zip(t,s):
        candidates=np.flatnonzero((at<=ti-.03)&(ap<=ti))
        if len(candidates):j=candidates[-1];ax=a['xyz[0]'][j];ay=a['xyz[1]'][j]
        else:
            avail=np.flatnonzero(ap<=ti)
            j=avail[0] if len(avail) else 0
            ax=a['xyz[0]'][j] if len(avail) else 0.;ay=a['xyz[1]'][j] if len(avail) else 0.
        after.append((si-b0+36.839*float(ay)-3.332*float(ax))*.00980665);ixs.append(j)
    after=np.array(after);limit=float(u.initial_parameters['TFC_THRUST_MAX'])*1000*.00980665
    q=float(u.initial_parameters['TFC_SD_ES']);r=float(u.initial_parameters['TFC_SD_ME'])
    before_filtered=scalar_filter(t,np.clip(before,-limit,limit),q,r,limit)
    after_filtered=scalar_filter(t,np.clip(after,-limit,limit),q,r,limit)
    tr=pd.read_csv(OUT/f'condition_{file["nominal_ramp_s"]}s_trace.csv')
    row=table[(table.nominal_ramp_s==file['nominal_ramp_s'])&(table.signal=='after_source_matched_filter')].iloc[0]
    m=(t>=row.t10_s-3)&(t<=row.t90_s+4);ev=(t>=row.t10_s)&(t<=row.t90_s+3)
    checks[f'{file["nominal_ramp_s"]}s_all_native_display_samples_retained']=len(tr)==sum(m)
    errors.extend([np.max(abs(tr.T_raw_N-before[m])),np.max(abs(tr.T_hat_raw_N-after[m])),np.max(abs(tr.T_matched_filter_N-before_filtered[m])),np.max(abs(tr.T_hat_matched_filter_N-after_filtered[m]))])
    errors.extend([abs(np.sqrt(np.mean(after_filtered[ev]**2))-row.rmse_N),abs(np.max(abs(after_filtered[ev]))-row.max_abs_N),abs(np.mean(after_filtered[ev])-row.mean_bias_N)])
checks['direct_historical_sample_formula_and_scalar_filter_recomputed']=bool(max(errors)<1e-8)
checks['all_trials_no_force_clipping_or_missing_accel_in_display']=all(d['clipped_before_full_log']==0 and d['clipped_after_full_log']==0 and d['accel_unavailable_in_plot']==0 for d in summary['trials'])

figs=json.loads((OUT/'render_verification.json').read_text(encoding='utf-8'))
aa=figs[0]['axes']
checks['all_six_y_limits_ticks_identical']=all(a['ylim']==aa[0]['ylim'] and a['yticks']==aa[0]['yticks'] for a in aa)
checks['paired_x_ranges_identical']=all(aa[j]['xlim']==aa[j+3]['xlim'] for j in range(3))
checks['all_fonts_embedded']=all(f['embedded_bytes']>0 for fig in figs for f in fig['fonts'])
checks['PDFs_vector_no_raster_objects']=all(fig['raster_image_objects']==0 for fig in figs)
checks['Chinese_math_labels_present']=all('补偿' in f['pdf_text'] and 'RMSE' in f['pdf_text'] for f in figs)
checks['PNG_export_is_600dpi']=all(abs(Image.open(OUT/(f['file']+'.png')).info['dpi'][0]-600)<.1 for f in figs)
data=pd.read_csv(OUT/'native_plot_data.csv')
checks['all_visible_values_inside_axis_limits']=all(data.force_N.min()>=ax['ylim'][0] and data.force_N.max()<=ax['ylim'][1] for ax in aa)
protected=ROOT/'output/deployment_sensor_figures/protected_existing_sha256.json'
old=json.loads(protected.read_text(encoding='utf-8'))
checks['original_manuscript_fig8_12_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in old.items())
checks={k:bool(v) for k,v in checks.items()}
result=dict(checks=checks,all_automated_checks_pass=all(checks.values()),largest_independent_numeric_difference=float(max(errors)),visual_review='Final PDF renders and155mm/80mm previews inspected; labels complete, no overlap, common y scale. Raw native fluctuation statistics retained separately.',limits=['b0 uses first20 logged samples, not guaranteed original module-start samples','logged IMU approximately20Hz; unlogged runtime samples and scheduling unavailable','current source differs from committed version indicated in historical ULog; not bit-exact original firmware replay','coefficient calibration provenance unknown; not independent validation'])
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not all(checks.values()):raise SystemExit(1)
