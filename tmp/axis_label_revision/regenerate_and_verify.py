"""Run only the four current manuscript plots; compare artists before/after."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import types
import warnings

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import _tight_bbox
from matplotlib.transforms import Bbox
import numpy as np
import fitz

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BEFORE = OUT / 'before'
sys.path.insert(0, str(ROOT / 'data_process'))
SOURCES = [ROOT/'data_process/plot_deployment_sensor_figures.py',
           ROOT/'data_process/plot_sensor_new_1s_reconstruction.py',
           next((ROOT/'data').glob('*/analyze_closed_loop.py'))]
STEMS = ['static_rpm_mapping_dynamic_inflow', 'motor_off_force_sensor_compensation',
         'fig9_freestream_ramp', 'fig13_feedforward_mechanism']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def backup():
    for source in SOURCES:
        dst = BEFORE/source.relative_to(ROOT)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            dst.write_bytes(subprocess.check_output(
                ['git', 'show', 'HEAD:'+source.relative_to(ROOT).as_posix()], cwd=ROOT))
    hashes = {str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'Image').iterdir() if p.is_file()}
    if not (OUT/'image_hashes_before.json').exists():
        (OUT/'image_hashes_before.json').write_text(json.dumps(hashes,indent=2),encoding='utf-8')
    locations = [ROOT/'Image', ROOT/'output/figure7_single_column',
                 ROOT/'output/sensor_new_1s_reconstruction', ROOT/'output/deployment_sensor_figures',
                 ROOT/'output/figure8_compact', SOURCES[2].parent/'analysis_current_90deg']
    for directory in locations:
        for stem in STEMS:
            for path in directory.glob(stem+'*'):
                if path.is_file():
                    dst = BEFORE/path.relative_to(ROOT)
                    dst.parent.mkdir(parents=True,exist_ok=True)
                    if not dst.exists():
                        shutil.copy2(path,dst)

def load(source, name, old=False):
    module = types.ModuleType(name)
    module.__file__ = str(source)
    sys.modules[name] = module
    text = (BEFORE/source.relative_to(ROOT) if old else source).read_text(encoding='utf-8')
    exec(compile(text,str(source),'exec'), module.__dict__)
    return module

def processing_check():
    for source in SOURCES:
        old = ast.parse((BEFORE/source.relative_to(ROOT)).read_text(encoding='utf-8'))
        new = ast.parse(source.read_text(encoding='utf-8'))
        class StripLabels(ast.NodeTransformer):
            def visit_Expr(self,node):
                if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute):
                    if node.value.func.attr in ('set_xlabel','set_ylabel'):
                        return None
                return self.generic_visit(node)
        assert ast.dump(StripLabels().visit(old)) == ast.dump(StripLabels().visit(new)), source

def arr(value):
    a = np.asarray(value)
    return dict(shape=list(a.shape),dtype=str(a.dtype),sha256=hashlib.sha256(a.tobytes()).hexdigest())

def snapshot(fig):
    fig.canvas.draw()
    axes=[]
    for ax in fig.axes:
        lines=[dict(x=arr(l.get_xdata()),y=arr(l.get_ydata()),color=l.get_color(),ls=l.get_linestyle(),
                    lw=l.get_linewidth(),marker=l.get_marker(),ms=l.get_markersize(),
                    mfc=l.get_markerfacecolor(),mec=l.get_markeredgecolor(),mew=l.get_markeredgewidth(),
                    markevery=l.get_markevery(),label=l.get_label(),zorder=l.get_zorder()) for l in ax.lines]
        patches=[dict(vertices=arr(p.get_path().vertices),face=p.get_facecolor(),edge=p.get_edgecolor(),
                      lw=p.get_linewidth(),ls=p.get_linestyle(),zorder=p.get_zorder(),alpha=p.get_alpha()) for p in ax.patches]
        texts=[dict(text=t.get_text(),position=t.get_position(),size=t.get_fontsize(),
                    family=t.get_fontfamily(),color=t.get_color()) for t in ax.texts]
        legend=ax.get_legend()
        axes.append(dict(position=list(ax.get_position().bounds),xlim=list(ax.get_xlim()),ylim=list(ax.get_ylim()),
                         xticks=list(ax.get_xticks()),yticks=list(ax.get_yticks()),
                         xlabel=ax.get_xlabel(),ylabel=ax.get_ylabel(),
                         label_sizes=[ax.xaxis.label.get_fontsize(),ax.yaxis.label.get_fontsize()],
                         lines=lines,patches=patches,texts=texts,
                         legend=[t.get_text() for t in legend.get_texts()] if legend else None))
    return dict(figsize=list(fig.get_size_inches()),dpi=fig.dpi,axes=axes)

def capture(module, save_name, function, *args, fixed_boxes=None):
    original=getattr(module,save_name)
    results=[]
    boxes={}
    def wrapped(fig,*a,**kw):
        savefig=fig.savefig
        adjust_bbox=_tight_bbox.adjust_bbox
        def save_with_bounds(filename,*save_args,**save_kw):
            suffix=Path(filename).suffix
            if fixed_boxes is not None:
                save_kw.update(bbox_inches=Bbox.from_extents(*fixed_boxes[suffix]),pad_inches=0)
            def record_bounds(figure,bbox,*adjust_args,**adjust_kw):
                boxes[suffix]=list(bbox.extents)
                return adjust_bbox(figure,bbox,*adjust_args,**adjust_kw)
            _tight_bbox.adjust_bbox=record_bounds
            try:
                return savefig(filename,*save_args,**save_kw)
            finally:
                _tight_bbox.adjust_bbox=adjust_bbox
        fig.savefig=save_with_bounds
        try:
            original(fig,*a,**kw)
        finally:
            fig.savefig=savefig
        results.append(snapshot(fig))
        plt.close(fig)
    setattr(module,save_name,wrapped)
    try:
        function(*args)
    finally:
        setattr(module,save_name,original)
    assert len(results)==1
    return results[0],boxes

def compare(old,new,key,expected):
    actual={}
    for index,(a,b) in enumerate(zip(old['axes'],new['axes'])):
        for label in ('xlabel','ylabel'):
            if a[label]!=b[label]:
                actual[f'{index}.{label}']=[a[label],b[label]]
            a[label]=b[label]='<label>'
    assert actual==expected,(key,actual)
    assert old==new,(key,'non-label artists or geometry changed')
    return dict(label_changes=actual,all_samples_styles_ticks_layout_identical=True,
                figsize=new['figsize'],axes_positions=[a['position'] for a in new['axes']])

def copy_exports(source_dir,dest_dir,stem):
    dest_dir.mkdir(parents=True,exist_ok=True)
    for path in source_dir.glob(stem+'*'):
        if path.suffix in ('.pdf','.png'):
            if dest_dir==ROOT/'Image' and path.stem!=stem:
                continue
            shutil.copy2(path,dest_dir/path.name)

def main():
    backup()
    processing_check()
    report={}
    old7=load(SOURCES[0],'axis_old7',True); new7=load(SOURCES[0],'axis_new7')
    old7.OUT=OUT/'old7'; old7.OUT.mkdir(exist_ok=True)
    groups,spread=old7.static_data(); _,selected,_=old7.dynamic_data()
    old,boxes=capture(old7,'save_figure_a',old7.plot_A,groups,spread,selected)
    new7.OUT=ROOT/'output/figure7_single_column'
    new,_=capture(new7,'save_figure_a',new7.plot_A,groups,spread,selected,fixed_boxes=boxes)
    report['figure7']=compare(old,new,'figure7',{
        '0.xlabel':[r'电机机械转速 $n$ (rpm)',r'电机转速 $\Omega$ (rpm)'],
        '0.ylabel':[r'归一化控制量 $u_{\mathrm{cal}}$',r'归一化控制量 $u_c$'],
        '1.xlabel':[r'$\tau=t-t_{10}$ (s)','时间 (s)'],
        '1.ylabel':[r'转速相对变化 $\delta n$ (%)',r'转速相对变化率 $\delta\Omega$ (%)']})
    copy_exports(new7.OUT,ROOT/'Image',STEMS[0])
    print('Figure 7 regenerated; curves, axes geometry, ticks and styles identical.',flush=True)

    old8=load(SOURCES[1],'axis_old8',True); new8=load(SOURCES[1],'axis_new8')
    old8.OUT=OUT/'old8'; old8.OUT.mkdir(exist_ok=True); old8.P.OUT=old8.OUT
    run,_=old8.reconstruct(); runs=[run,old8.old_run(5),old8.old_run(10)]
    def draw8(module):
        fig,aa=module.figure8(runs)
        module.P.save(fig,STEMS[1],list(aa.flat))
    old,boxes=capture(old8.P,'save',draw8,old8)
    new8.P.OUT=new8.OUT
    new,_=capture(new8.P,'save',draw8,new8,fixed_boxes=boxes)
    report['figure8']=compare(old,new,'figure8',{
        f'{i}.xlabel':[r'$\tau=t-t_{10}$ (s)','时间 (s)'] for i in (3,4,5)})
    for destination in (ROOT/'Image',ROOT/'output/deployment_sensor_figures',ROOT/'output/figure8_compact'):
        copy_exports(new8.OUT,destination,STEMS[1])
    print('Figure 8 regenerated; all six curves and existing label locations preserved.',flush=True)

    oldc=load(SOURCES[2],'axis_oldclosed',True); newc=load(SOURCES[2],'axis_newclosed')
    oldc.configure_plotting(); newc.configure_plotting()
    oldc.OUTPUT_DIR=OUT/'oldclosed'; oldc.OUTPUT_DIR.mkdir(exist_ok=True)
    oldc.IMAGE_DIR=OUT/'oldclosed_images'; oldc.IMAGE_DIR.mkdir(exist_ok=True)
    paths=[p for p in sorted(oldc.DATA_DIR.glob('*.ulg')) if oldc.parse_filename(p)[1]==20]
    assert len(paths)==9,paths
    runs=[oldc.load_run(p) for p in paths]
    for number,function,expected in [
        (10,'plot_freestream_ramp',{'0.xlabel':[r'$\tau=t-t_{10}$ (s)','时间 (s)']}),
        (14,'plot_mechanism',{'1.xlabel':[r'$\tau=t-t_{10}$ (s)','时间 (s)'],
                              '1.ylabel':['转速 (rpm)',r'电机转速 $\Omega$ (rpm)']})]:
        old,boxes=capture(oldc,'save_figure',getattr(oldc,function),runs)
        new,_=capture(newc,'save_figure',getattr(newc,function),runs,fixed_boxes=boxes)
        report[f'figure{number}']=compare(old,new,f'figure{number}',expected)
        print(f'Figure {number} regenerated; data, styles and layout identical.',flush=True)

    pdf_checks={}
    for stem in STEMS:
        path=ROOT/'Image'/(stem+'.pdf'); doc=fitz.open(path); page=doc[0]
        spans=[s for b in page.get_text('dict')['blocks'] if 'lines' in b for l in b['lines'] for s in l['spans']]
        outside=[s['text'] for s in spans if not page.rect.contains(fitz.Rect(s['bbox']))]
        assert not outside,(stem,outside)
        assert '\ufffd' not in page.get_text()
        assert '时间' in page.get_text(),(stem,page.get_text())
        if stem in (STEMS[0],STEMS[3]):
            assert 'Ω' in page.get_text(),(stem,page.get_text())
        embedded=[dict(name=f[3],bytes=len(doc.extract_font(f[0])[3])) for f in page.get_fonts(full=True)]
        assert all(f['bytes']>0 for f in embedded)
        page.get_pixmap(dpi=180,alpha=False).save(OUT/(stem+'_after.png'))
        olddoc=fitz.open(BEFORE/'Image'/(stem+'.pdf'))
        assert list(page.rect)==list(olddoc[0].rect),(stem,page.rect,olddoc[0].rect)
        pdf_checks[stem]=dict(text=page.get_text(),all_text_inside_page=True,fonts=embedded,
                             old_pdf_size=list(olddoc[0].rect),new_pdf_size=list(page.rect))
    before_hashes=json.loads((OUT/'image_hashes_before.json').read_text())
    allowed={str((Path('Image')/(s+suffix))) for s in STEMS for suffix in ('.pdf','.png','_83mm_preview.png','_pdf_check.png','_155mm_preview.png')}
    unexpected=[p for p,h in before_hashes.items() if sha(ROOT/p)!=h and p not in allowed]
    assert not unexpected,unexpected
    report['processing_AST_unchanged_except_axis_labels']=True
    report['other_Image_files_unchanged']=True
    report['pdf_checks']=pdf_checks
    (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PASS: only specified axis labels differ; every PDF font embedded and text within page.',flush=True)

if __name__=='__main__':
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        main()
        messages=sorted({str(w.message) for w in caught})
        (OUT/'render_warnings.json').write_text(json.dumps(messages,ensure_ascii=False,indent=2),encoding='utf-8')
        assert not any('Glyph' in m and 'missing' in m for m in messages),messages
        print('Missing-glyph warnings: 0',flush=True)
