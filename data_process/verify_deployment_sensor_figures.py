"""Checks source preservation, independent selected metrics, exported geometry/fonts.

Run after the plotting script; methodology limitations are explicit, not PASS.
"""
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from pyulog import ULog
import fitz

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/deployment_sensor_figures'
checks={}
manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
checks['all_used_sources_match_recorded_sha256']=all(hashlib.sha256(Path(r['path']).read_bytes()).hexdigest()==r['sha256'] for r in manifest)
geo=json.loads((OUT/'render_verification.json').read_text(encoding='utf-8'))
ga=geo['static_rpm_mapping_dynamic_inflow']['axes'];gb=geo['motor_off_force_sensor_compensation']['axes']
checks['A_primary_axes_left_right_aligned']=bool(np.allclose(np.array(ga[0]['position'])[[0,2]],np.array(ga[1]['position'])[[0,2]],atol=1e-12))
checks['B_all_six_y_limits_and_ticks_identical']=all(a['ylim']==gb[0]['ylim'] and a['yticks']==gb[0]['yticks'] for a in gb)
checks['B_paired_x_ranges_identical']=all(gb[j]['xlim']==gb[j+3]['xlim'] for j in range(3))
checks['all_pdf_fonts_embedded']=all(f['embedded_bytes']>0 for g in geo.values() for f in g['fonts'])
checks['PDFs_are_vector_without_raster_image_objects']=all(not fitz.open(OUT/f'{n}.pdf')[0].get_images() for n in geo)
checks['pdf_contains_expected_chinese']=all('转速' in geo[n]['text'] if n.startswith('static') else '补偿' in geo[n]['text'] for n in geo)

# Recompute the headline spread at the maximum comparison row using individual
# source group CSVs, not the output spread columns or plotted curves.
spread=pd.read_csv(OUT/'static_common_u_spread.csv')
j=spread.D_pct.idxmax();uj=spread.loc[j,'u_cal'];ns=[]
for group in ['up_1','down_1','up_2','down_2']:
    pt=pd.read_csv(OUT/f'static_points_{group}.csv').sort_values('u')
    ns.append(np.interp(uj,pt.u,pt.n))
d=(max(ns)-min(ns))/(sum(ns)/4)*100
checks['headline_static_spread_recomputed']=bool(abs(d-spread.loc[j,'D_pct'])<1e-8)

# Re-open native ULogs and independently recompute metrics with explicitly
# written time bounds for the three principal dynamic trials.
cfg=json.loads((ROOT/'data_process/deployment_sensor_figures_config.json').read_text(encoding='utf-8'))
table=pd.read_csv(OUT/'dynamic_all_9_trials_metrics.csv')
checks['all_9_dynamic_trials_included']=len(table)==9 and set(table.nominal_ramp_s)=={1,5,10}
errors=[]
for _,row in table[table.nominal_ramp_s==1].iterrows():
    u=ULog(str(Path(cfg['dynamic_dir'])/row['file']))
    r=next(ds.data for ds in u.data_list if ds.name=='rpm' and ds.multi_id==0)
    t=r['timestamp'].astype(float)/1e6;n=-r['rpm_raw'].astype(float)
    npre=np.mean(n[(t>=row.t10_s-3)&(t<=row.t10_s-.5)])
    z=(n-npre)/npre*100
    ev=(t>=row.t10_s)&(t<=row.t90_s+3)
    post=(t>=row.t90_s+2)&(t<=row.t90_s+3)
    errors.extend([abs(np.mean(z[post])-row.steady_mean_delta_pct),abs(np.sqrt(np.mean(z[ev]**2))-row.disturbance_rms_delta_pct),abs(np.max(abs(z[ev]))-row.disturbance_max_abs_delta_pct)])
checks['main_dynamic_native_metrics_independently_recomputed']=bool(max(errors)<1e-7)
checks['no_whole_process_below_5percent_claim']=bool((table.steady_mean_delta_pct.abs()<5).all() and (table.disturbance_max_abs_delta_pct>5).all())

sens=pd.read_csv(OUT/'sensor_native_plot_data.csv')
metrics=pd.read_csv(OUT/'sensor_paired_metrics.csv')
inside=[]
for j,nom in enumerate([1,5,10]):
    for i,key in enumerate(['before_raw_converted','after_online_filtered']):
        mm=(metrics.nominal_ramp_s==nom)&(metrics.signal==key)
        m=metrics[mm].iloc[0]
        pts=sens[(sens.file==m['file'])&(sens.signal==key)]
        a=gb[3*i+j]
        inside.append(pts.force_N.min()>=a['ylim'][0] and pts.force_N.max()<=a['ylim'][1])
        yy=pts[(pts.timestamp_s>=m.t10_s)&(pts.timestamp_s<=m.t90_s+3)].force_N.to_numpy()
        inside.append(abs(np.sqrt(np.mean(yy**2))-m.rmse_N)<1e-9)
checks['all_B_native_visible_data_inside_common_y_limits_and_RMSE_recomputed']=bool(all(inside))

protected=OUT/'protected_existing_sha256.json'
if protected.exists():
    old=json.loads(protected.read_text(encoding='utf-8'))
    checks['manuscript_and_existing_fig8_12_files_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in old.items())
limitations={
 'static_native_stable_segment_reextraction':'UNAVAILABLE: CSV only contains exported means; user confirmed four sweeps',
 'static_and_dynamic_control_node_equivalence':'UNCONFIRMED: distinct labels u_cal/u_cmd retained',
 'true_1s_compensation_pair':'UNAVAILABLE: compensated file-labeled1s has 4.083s acceleration',
 'filter_matched_compensation_effect':'UNAVAILABLE: online filter implementation absent, raw vs online-filtered display disclosed',
 'equation23_coordinate_gravity_bias_and_coeff_provenance':'UNVERIFIED: user instructed direct provided-data plotting without source investigation',
 'sensor2_conversion_for_these_ULogs':'CONDITIONAL: 0.0098 N/unit from project workbook convention, not these firmware versions',
 'strictly_zero_mechanical_rpm':'UNCONFIRMED: fixed1000us PWM with sparse nonzero encoder samples',
 'visual_review':'performed on PDF renders and 155mm previews; see README and final delivery'
}
result=dict(checks=checks,all_automated_checks_pass=all(checks.values()),maximum_native_dynamic_metric_difference=float(max(errors)),static_Dmax_recomputed_pct=float(d),methodology_limits=limitations)
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not all(checks.values()):raise SystemExit(1)
