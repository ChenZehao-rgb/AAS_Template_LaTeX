"""Audit current Fig. 8 against the preserved pre-layout source and artifacts.

Run after: python data_process/plot_sensor_new_1s_reconstruction.py
"""
from pathlib import Path
import ast
import hashlib
import json
import shutil
import sys
sys.dont_write_bytecode = True
import fitz
import numpy as np
import pandas as pd
import plot_sensor_new_1s_reconstruction as p

ROOT = p.ROOT
OUT = ROOT/'output/figure8_compact'
BEFORE = OUT/'before'
STEM = 'motor_off_force_sensor_compensation'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    old_source = (BEFORE/'data_process/plot_sensor_new_1s_reconstruction.py').read_text(encoding='utf-8')
    new_source = Path(p.__file__).read_text(encoding='utf-8')
    old_funcs = {n.name:n for n in ast.parse(old_source).body if isinstance(n, ast.FunctionDef)}
    new_funcs = {n.name:n for n in ast.parse(new_source).body if isinstance(n, ast.FunctionDef)}
    checks = {'processing_function_AST_unchanged': all(
        ast.dump(old_funcs[name]) == ast.dump(new_funcs[name]) for name in ['metric', 'reconstruct', 'old_run'])}
    runs = [p.reconstruct()[0], p.old_run(5), p.old_run(10)]
    baseline = json.loads((OUT/'baseline_data_audit.json').read_text(encoding='utf-8'))
    legacy_globals = dict(p.__dict__)
    exec(compile(ast.Module(body=[old_funcs['draw']], type_ignores=[]), '<preserved draw>', 'exec'), legacy_globals)
    old_fig, old_aa = p.plt.subplots(2, 3, figsize=(6.10, 3.60), sharey='row')
    for j, run in enumerate(runs):
        for row in [0, 1]:
            legacy_globals['draw'](old_aa[row,j], run, row, (-6,4), np.arange(-6.,5.,2.))
    old_fig.subplots_adjust(left=.095,right=.985,top=.975,bottom=.105,wspace=.10,hspace=.11)
    fig, aa = p.figure8(runs)
    for ax in aa.flat:
        ax.yaxis.label.set_fontfamily('SimSun')
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    audit, traces = [], []
    for j, (run, prior) in enumerate(zip(runs, baseline)):
        checks[f'{run["nominal"]}s_metrics_identical'] = (
            run['before_metric']==prior['before_rmse'] and run['after_metric']==prior['after_rmse'])
        shade_pixels = []
        for row in [0,1]:
            ax, old_ax = aa[row,j], old_aa[row,j]
            line, old_line = ax.lines[0], old_ax.lines[0]
            x,y = line.get_data()
            key = f'{run["nominal"]}s_row{row}'
            checks[key+'_all_samples_and_times_identical'] = np.array_equal(x,old_line.get_xdata()) and np.array_equal(y,old_line.get_ydata())
            checks[key+'_line_style_identical'] = all(getattr(line, method)()==getattr(old_line, method)() for method in
                ['get_color','get_linewidth','get_linestyle','get_marker','get_markersize','get_markerfacecolor','get_markeredgewidth','get_markevery'])
            checks[key+'_every_sample_in_axes'] = bool(np.isfinite(y).all() and min(y)>ax.get_ylim()[0] and max(y)<ax.get_ylim()[1]
                                                        and min(x)>=ax.get_xlim()[0] and max(x)<=ax.get_xlim()[1])
            checks[key+'_rmse_text_identical'] = ax.texts[0].get_text()==old_ax.texts[0].get_text()
            if row==1:
                bbox = ax.texts[0].get_window_extent(renderer)
                display = ax.transData.transform(np.column_stack([x,y]))
                # Include line width/marker radius in the collision clearance.
                checks[key+'_rmse_clear_of_trace'] = not bool(np.any(
                    (display[:,0]>bbox.x0-3)&(display[:,0]<bbox.x1+3)&(display[:,1]>bbox.y0-3)&(display[:,1]<bbox.y1+3)))
                checks[key+'_rmse_clear_of_zero'] = bool(bbox.y1 < ax.transData.transform((0,0))[1]-3)
                checks[key+'_common_y_limits_ticks'] = list(ax.get_ylim())==[-2.,1.] and list(ax.get_yticks())==[-2.,-1.,0.,1.]
            shade_pixels.append(ax.transData.transform([(0,0),(run['t90']-run['t10'],0)])[:,0])
            transient = (x>=0)&(x<=run['t90']-run['t10'])
            extrema = {}
            for label, idx in [('min',np.argmin(y)),('max',np.argmax(y)),('peak_abs',np.argmax(abs(y)))]:
                extrema[label] = dict(force_N=float(y[idx]),tau_s=float(x[idx]))
            audit.append(dict(nominal_s=run['nominal'],row=row,samples=len(y),extrema=extrema,
                              transient_range_N=[float(y[transient].min()),float(y[transient].max())],
                              xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),yticks=list(ax.get_yticks()),
                              rmse_N=(run['before_metric'] if row==0 else run['after_metric'])['rmse_N'],
                              evaluation_window_s=[run['t10'],run['t90']+3]))
            traces.extend(dict(nominal_s=run['nominal'],row=row,tau_s=xi,force_N=yi) for xi,yi in zip(x,y))
        checks[f'{run["nominal"]}s_column_time_axes_and_shading_aligned'] = (
            aa[0,j].get_shared_x_axes().joined(aa[0,j],aa[1,j]) and
            aa[0,j].get_xlim()==aa[1,j].get_xlim() and np.array_equal(shade_pixels[0],shade_pixels[1]))
    checks['row_y_axes_independent'] = not aa[0,0].get_shared_y_axes().joined(aa[0,0],aa[1,0])
    ratio = aa[1,0].get_position().height/aa[0,0].get_position().height
    checks['actual_height_ratio_0_7'] = abs(ratio-.7)<1e-12
    checks['three_columns_share_y_within_each_row'] = all(aa[row,0].get_shared_y_axes().joined(aa[row,0],aa[row,j]) for row in [0,1] for j in [1,2])
    checks['native_1s_export_identical'] = sha(p.OUT/'reconstructed_1s_plot_data.csv')==sha(BEFORE/'output/sensor_new_1s_reconstruction/reconstructed_1s_plot_data.csv')
    checks['1s_summary_and_processing_identical'] = sha(p.OUT/'analysis_summary.json')==sha(BEFORE/'output/sensor_new_1s_reconstruction/analysis_summary.json')
    old_pdf = fitz.open(BEFORE/'Image'/(STEM+'.pdf'))
    new_pdf = fitz.open(ROOT/'Image'/(STEM+'.pdf'))
    page = new_pdf[0]
    checks['vector_pdf_no_raster_objects'] = len(page.get_images())==0
    checks['all_pdf_fonts_embedded'] = all(len(new_pdf.extract_font(f[0])[3])>0 for f in page.get_fonts(full=True))
    checks['pdf_text_inside_page'] = all(page.rect.contains(fitz.Rect(line['bbox'])) for block in page.get_text('dict')['blocks']
        if block['type']==0 for line in block['lines'])
    for suffix in ['.pdf','.png']:
        checks['paper_image_matches_render_'+suffix] = sha(ROOT/'Image'/(STEM+suffix))==sha(p.OUT/(STEM+suffix))
    for suffix in ['.pdf','.png','_155mm_preview.png','_pdf_check.png']:
        shutil.copy2(p.OUT/(STEM+suffix), OUT/(STEM+suffix))
    shutil.copy2(Path(p.__file__), OUT/Path(p.__file__).name)
    pd.DataFrame(traces).to_csv(OUT/'all_six_native_plot_traces.csv',index=False,encoding='utf-8-sig',float_format='%.17g')
    mm = lambda doc: [float(doc[0].rect.width*25.4/72),float(doc[0].rect.height*25.4/72)]
    result = dict(all_pass=bool(all(checks.values())),checks={k:bool(v) for k,v in checks.items()},
        before=dict(canvas_inches=[6.10,3.60],pdf_mm=mm(old_pdf),height_ratio=1.,lower_ylim=[-6,4]),
        after=dict(canvas_inches=list(p.FIG8_SIZE_IN),pdf_mm=mm(new_pdf),height_ratio=float(ratio),lower_ylim=[-2,1],
                   lower_yticks=[-2,-1,0,1],paper_width_mm=155.,paper_height_mm=155*page.rect.height/page.rect.width,
                   actual_axes_height_mm=[aa[row,0].get_position().height*fig.get_figheight()*25.4 for row in [0,1]],
                   major_tick_font_pt=aa[1,0].get_xticklabels()[0].get_fontsize(),label_font_pt=aa[1,0].yaxis.label.get_fontsize()),
        traces=audit)
    (OUT/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='traces'},ensure_ascii=False,indent=2))
    p.plt.close('all')
    if not result['all_pass']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
