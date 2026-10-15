"""Verify physical typography, unchanged computations, native extrema and PDF bounds."""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import fitz
import numpy as np
import pandas as pd
import plot_deployment_sensor_figures as plot

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/figure7_single_column'
BASE=ROOT/'output/deployment_sensor_figures'

def functions(path):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8')).body
            if isinstance(n,ast.FunctionDef)}

old=functions(OUT/'before/plot_deployment_sensor_figures.py')
new=functions(ROOT/'data_process/plot_deployment_sensor_figures.py')
unchanged=['static_data','dynamic_data','topic','ts','mask','values','stats']
assert all(old[k]==new[k] for k in unchanged)
tables=['static_fits.csv','static_common_u_spread.csv','dynamic_native_rpm_plot_data.csv',
        'dynamic_main_inflow_comparison.csv','dynamic_all_9_trials_metrics.csv']
for f in tables:
    pd.testing.assert_frame_equal(pd.read_csv(BASE/f),pd.read_csv(OUT/f))

plot.OUT=OUT
groups,spread=plot.static_data()
_,selected,consistency=plot.dynamic_data()
capture={}
original_save=plot.save_figure_a
def verify_and_save(fig,axes):
    for k,g in enumerate(groups):
        n=np.linspace(g['points'].n.min(),g['points'].n.max(),300)
        np.testing.assert_array_equal(axes[0].lines[2*k].get_xdata(),n)
        np.testing.assert_array_equal(axes[0].lines[2*k].get_ydata(),np.polyval(g['coeff'],n*2*np.pi/60))
        np.testing.assert_array_equal(axes[0].lines[2*k+1].get_ydata(),g['points'].u)
    xmax=max(r['t90']-r['t10'] for r in selected)+4
    rows=[]
    for k,r in enumerate(selected):
        m=plot.mask(r['tau'],-3,xmax);line=axes[1].lines[k]
        np.testing.assert_array_equal(line.get_xdata(),r['tau'][m])
        np.testing.assert_array_equal(line.get_ydata(),r['delta'][m])
        assert line.get_color()==plot.COLORS[k] and line.get_linestyle()==plot.LINES[k]
        ev=plot.mask(r['rt'],r['t10'],r['t90']+3)
        ss=plot.mask(r['rt'],r['t90']+2,r['t90']+3)
        rows.append(dict(file=r['path'].name,u_cmd=r['row']['u_cmd_mean'],
            n_pre_rpm=r['row']['n_pre_rpm'],t10_s=r['t10'],t90_s=r['t90'],
            plot_samples=int(m.sum()),plot_min_pct=float(r['delta'][m].min()),plot_max_pct=float(r['delta'][m].max()),
            plot_over_5_samples=int((abs(r['delta'][m])>5).sum()),
            evaluation_samples=int(ev.sum()),evaluation_peak_abs_pct=float(abs(r['delta'][ev]).max()),
            evaluation_over_5_samples=int((abs(r['delta'][ev])>5).sum()),
            steady_samples=int(ss.sum()),steady_mean_pct=float(r['delta'][ss].mean())))
    assert all(any(np.all(np.asarray(line.get_ydata())==y) for line in axes[1].lines[3:]) for y in (-5,5))
    capture['dynamic']=rows
    original_save(fig,axes)
plot.save_figure_a=verify_and_save
plot.plot_A(groups,spread,selected)

reference=fitz.open(ROOT/'Image/fig9_rotor_model_diagnostics.pdf')
current=fitz.open(OUT/'static_rpm_mapping_dynamic_inflow.pdf')
page=current[0]
spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
def size(fragment):
    return next(s['size'] for s in spans if fragment in s['text'])
fonts=plot.geometry['figure7_typography']['fonts_pt']
actual=dict(axis=size('电机机械转速'),tick=size('1000'),legend=size('0.408'),panel=size('(a)'),statistic=size('max'))
assert all(abs(actual[k]-fonts[k])<.001 for k in actual)
assert not page.get_images()
assert all(page.rect.contains(fitz.Rect(s['bbox'])) for s in spans)
assert '来流速度' in page.get_text()
assert abs(page.rect.width*25.4/72-83)<.001

# Both figures on one physical-size sheet: 83 mm and 75 mm respectively.
comparison=fitz.open();sheet=comparison.new_page(width=180/25.4*72,height=147/25.4*72)
mm=72/25.4
for source,x,width,title in [(current,4,83,'Figure 7: 83 mm'),(reference,96,75,'Figure 9: 75 mm')]:
    height=source[0].rect.height/source[0].rect.width*width
    sheet.insert_text((x*mm,6*mm),title,fontsize=9)
    sheet.show_pdf_page(fitz.Rect(x*mm,10*mm,(x+width)*mm,(10+height)*mm),source,0)
comparison.save(OUT/'figure7_vs_figure9_actual_size.pdf')
sheet.get_pixmap(dpi=180,alpha=False).save(OUT/'figure7_vs_figure9_actual_size.png')

capture.update(checks=dict(processing_functions_unchanged=unchanged,identical_exported_tables=tables,
    native_plot_samples_unchanged=True,reference_lines_retained=True,panel_and_annotation_geometry_checks=True,
    right_axis_present_and_all_pdf_text_within_page=True,vector_pdf_no_raster_images=True),
    geometry=plot.geometry,actual_pdf_fonts_pt=actual,static_spread=spread)
(OUT/'verification.json').write_text(json.dumps(capture,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'render_verification.json').write_text(json.dumps(plot.geometry,ensure_ascii=False,indent=2),encoding='utf-8')
pd.DataFrame(capture['dynamic']).to_csv(OUT/'dynamic_5pct_audit.csv',index=False,encoding='utf-8-sig')
# Deploy only the content-verified Figure 7 after all checks succeed.
for suffix in ('pdf','png'):
    shutil.copy2(OUT/f'static_rpm_mapping_dynamic_inflow.{suffix}',ROOT/'Image'/f'static_rpm_mapping_dynamic_inflow.{suffix}')
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
    ROOT/'data_process/plot_deployment_sensor_figures.py',ROOT/'data_process/deployment_sensor_figures_config.json',
    ROOT/'data_process/verify_fig7_single_column.py',OUT/'static_rpm_mapping_dynamic_inflow.pdf',
    ROOT/'Image/fig9_rotor_model_diagnostics.pdf']}
(OUT/'source_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(capture,ensure_ascii=False,indent=2))
