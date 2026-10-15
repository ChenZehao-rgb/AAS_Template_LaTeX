"""Verify source preservation, reconstructed values, native data and exports."""
from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd
import fitz
from pyulog import ULog

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/sensor_new_1s_reconstruction'
s=json.loads((OUT/'analysis_summary.json').read_text(encoding='utf-8'))
d=pd.read_csv(OUT/'reconstructed_1s_full_log.csv')
v=d[d.in_plot];ev=d[d.in_evaluation]
geo=json.loads((OUT/'render_verification.json').read_text(encoding='utf-8'))
manifest=json.loads((OUT/'source_manifest.json').read_text(encoding='utf-8'))
u=ULog(s['source'])
raw=next(x.data for x in u.data_list if x.name=='pressure_force_sensor' and x.multi_id==0)
a=next(x.data for x in u.data_list if x.name=='vehicle_acceleration' and x.multi_id==0)
ats=a['timestamp_sample'].astype(float)/1e6
ap=a['timestamp'].astype(float)/1e6
native_t=raw['timestamp'].astype(float)/1e6
availability=np.searchsorted(ap,native_t,side='right')-1
idx=np.minimum(np.searchsorted(ats,native_t-.03,side='right')-1, availability)
idx=np.maximum(idx,0)
expected_ax=np.where(availability>=0,a['xyz[0]'][idx],0.)
expected_ay=np.where(availability>=0,a['xyz[1]'][idx],0.)
expected=(d.sensor2_g-s['b0_g']+36.839*d.ay_delayed_m_s2-3.332*d.ax_delayed_m_s2)*.00980665
checks={
    'sources_unchanged':all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['sha256'] for x in manifest),
    'all_native_force_samples_preserved':len(d)==len(raw['timestamp']) and np.array_equal(d.sensor2_g,raw['sensor2']),
    'shared_bias_first20_verified':s['b0_g']==float(np.mean(raw['sensor2'][:20])),
    'unclipped_formula_verified':bool(np.max(abs(expected-d.after_unclipped_raw_N))<1e-9),
    'source_delay_sample_selection_verified':bool(np.max(abs(expected_ax-d.ax_delayed_m_s2))<1e-8 and np.max(abs(expected_ay-d.ay_delayed_m_s2))<1e-8),
    'true_1s_ramp':.6<s['actual_10_90_s']<1.1,
    'negative_values_present_before_and_after_filter':v.after_unclipped_raw_N.min()<0 and v.after_unclipped_filtered_N.min()<0,
    'rmse_recomputed':abs(np.sqrt(np.mean(ev.after_unclipped_filtered_N**2))-s['after_unclipped_filtered']['rmse_N'])<1e-10,
    'all_fonts_embedded':all(f['embedded_bytes']>0 for g in geo for f in g['fonts']),
    'all_figures_vector':all(not fitz.open(OUT/(g['file']+'.pdf'))[0].get_images() for g in geo),
    'requested_annotation_removed':all('离线重建' not in g['pdf_text'] for g in geo),
    'standalone_y_range_preserved':all(ax['ylim']==[-6.,4.] for ax in geo[0]['axes']),
    'figure8_row_specific_y_ranges':all(ax['ylim']==([-6.,4.] if i<3 else [-2.,1.]) for i,ax in enumerate(geo[1]['axes'])),
    'all_1s_plotted_samples_inside_axes':all(v[col].min()>=-6 and v[col].max()<=4 for col in ['before_raw_N','after_unclipped_filtered_N']),
}
for suffix in ['.pdf','.png','_pdf_check.png','_155mm_preview.png']:
    name='motor_off_force_sensor_compensation'+suffix
    checks['deployed_matches_'+suffix]=hashlib.sha256((OUT/name).read_bytes()).hexdigest()==hashlib.sha256((ROOT/'output/deployment_sensor_figures'/name).read_bytes()).hexdigest()
result=dict(checks={k:bool(v) for k,v in checks.items()},all_pass=bool(all(checks.values())),
            formula_max_abs_difference_N=float(np.max(abs(expected-d.after_unclipped_raw_N))),
            visual_review='Standalone and combined previews inspected: full traces visible, labels readable, no overlap.',
            qualification='User-confirmed offline formula with first20 logged bias; not exact recovery of module startup states.')
(OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
if not result['all_pass']:raise SystemExit(1)
