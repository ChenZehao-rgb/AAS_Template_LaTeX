"""Export only current manuscript Figures 11-13 and verify display-only edits."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
sys.dont_write_bytecode = True
import fitz
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(__file__).resolve().parent
OUT = ROOT / "output" / "pdf" / "fig11_13_labels"
SOURCE = ROOT / "data" / "升力闭环测试" / "analyze_closed_loop.py"
SPECS = (
    (11, "plot_representative", "fig10_representative_response"),
    (12, "plot_representative_ramp_times", "fig14_ramp_time_response_20N"),
    (13, "plot_speed_error", "fig12_speed_error"),
)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compare_axes(a, b):
    for getter in ("get_xlim", "get_ylim", "get_xscale", "get_yscale"):
        assert getattr(a, getter)() == getattr(b, getter)(), getter
    assert a.get_position().bounds == b.get_position().bounds
    assert len(a.lines) == len(b.lines)
    for x, y in zip(a.lines, b.lines):
        np.testing.assert_array_equal(x.get_xydata(), y.get_xydata())
        for getter in ("get_color", "get_linestyle", "get_linewidth", "get_marker",
                       "get_markersize", "get_markevery", "get_markerfacecolor",
                       "get_markeredgecolor", "get_markeredgewidth", "get_alpha"):
            assert getattr(x, getter)() == getattr(y, getter)(), getter
    assert len(a.patches) == len(b.patches)
    for x, y in zip(a.patches, b.patches):
        np.testing.assert_array_equal(x.get_path().vertices, y.get_path().vertices)
        assert x.get_facecolor() == y.get_facecolor()
    assert len(a.collections) == len(b.collections)
    for x, y in zip(a.collections, b.collections):
        for px, py in zip(x.get_paths(), y.get_paths()):
            np.testing.assert_array_equal(px.vertices, py.vertices)
        np.testing.assert_array_equal(x.get_facecolor(), y.get_facecolor())
        assert x.get_alpha() == y.get_alpha()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = load(WORK / "before" / "analyze_closed_loop.py", "labels_before")
    new = load(SOURCE, "labels_after")
    trees = [{n.name: ast.dump(n) for n in ast.parse(p.read_text(encoding="utf-8")).body
              if isinstance(n, ast.FunctionDef)} for p in
             (WORK / "before" / "analyze_closed_loop.py", SOURCE)]
    changed = [name for name in trees[0] if trees[0][name] != trees[1][name]]
    assert set(changed) == {"plot_representative", "plot_representative_ramp_times"}, changed
    paths = sorted(new.DATA_DIR.glob("*.ulg"), key=lambda p: int(p.name.split("-")[0]))
    protected = paths + list(new.OUTPUT_DIR.glob("*.csv")) + list(new.OUTPUT_DIR.glob("*.sqlite"))
    protected += [ROOT / "template.tex", ROOT / "template.pdf"]
    target_images = {f"{stem}.pdf" for _, _, stem in SPECS} | {"fig10_ramp_time_response_20N.pdf"}
    protected += [p for p in new.IMAGE_DIR.glob("*") if p.is_file() and p.name not in target_images]
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    runs = [new.load_run(p) for p in paths]
    for run in runs:
        np.testing.assert_array_equal(run.error_n, run.desired_n - run.measured_n)
    new.configure_plotting()
    captures = []
    for module in (old, new):
        figures = {}
        module.save_figure = lambda fig, stem, figures=figures: figures.setdefault(stem, fig)
        module.IMAGE_DIR = WORK / "disabled_image_copy"
        for _, function, _ in SPECS:
            getattr(module, function)(runs)
        captures.append(figures)
    report = {"logs": len(runs), "changed_functions": changed,
              "protected_sha256": hashes, "figures": {}}
    for number, _, stem in SPECS:
        a, b = (figs[stem] for figs in captures)
        assert tuple(a.get_size_inches()) == tuple(b.get_size_inches())
        assert len(a.axes) == len(b.axes)
        for x, y in zip(a.axes, b.axes):
            compare_axes(x, y)
        b.canvas.draw()
        renderer = b.canvas.get_renderer()
        legend = b.legends[0] if b.legends else b.axes[0].get_legend()
        old_legend = a.legends[0] if a.legends else a.axes[0].get_legend()
        expected = [t.get_text().replace("固定控制量(Static)", "固定控制量(Fixed input)")
                    for t in old_legend.texts]
        assert [t.get_text() for t in legend.texts] == expected
        assert [t.get_fontsize() for t in legend.texts] == [t.get_fontsize() for t in old_legend.texts]
        if number in (11, 12):
            assert b.axes[0].get_ylabel() == r"升力 $T_m$ (N)"
            assert b.axes[3].get_ylabel() == r"误差 $T_e = T_d - T_m$ (N)"
            assert not any("T_c" in t.get_text() or "Tc" in t.get_text()
                           for t in b.findobj(plt.Text))
            assert legend.get_window_extent(renderer).y0 > max(
                ax.get_window_extent(renderer).y1 for ax in b.axes)
            assert not b.axes[0].yaxis.label.get_window_extent(renderer).overlaps(
                b.axes[3].yaxis.label.get_window_extent(renderer))
        boxes = [t.get_window_extent(renderer) for t in legend.texts]
        assert not any(x.overlaps(y) for i, x in enumerate(boxes) for y in boxes[i+1:])
        for extension in ("pdf", "png"):
            b.savefig(OUT / f"figure{number}.{extension}")
        with fitz.open(OUT / f"figure{number}.pdf") as pdf:
            page = pdf[0]
            assert len(pdf) == 1 and not page.get_images()
            assert len(page.get_drawings()) > 0
            for block in page.get_text("dict")["blocks"]:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        box = fitz.Rect(span["bbox"])
                        assert page.rect.contains(box), (number, span["text"], box)
            page.get_pixmap(matrix=fitz.Matrix(3, 3), alpha=False).save(
                OUT / f"figure{number}_pdf_preview.png")
            report["figures"][str(number)] = {
                "source_function": dict((n, f) for n, f, _ in SPECS)[number],
                "manuscript_image": "fig10_ramp_time_response_20N" if number == 12 else stem,
                "curve_data_style_limits_layout_unchanged": True,
                "vector_pdf": True, "legend_font_sizes": [t.get_fontsize() for t in legend.texts],
                "pdf_size_pt": list(page.rect),
            }
    assert all(digest(ROOT / p) == h for p, h in hashes.items())
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    plt.close("all")
    print(json.dumps({"output": str(OUT), "logs": len(runs), "figures": report["figures"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
