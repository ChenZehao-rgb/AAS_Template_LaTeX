"""Replot and verify manuscript Figures 8-10; never write metrics or raw data.

Run from the repository root: python data_process/verify_fig8_10_revision.py
The before snapshot is local to this revision and preserves pre-existing edits.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys

os.environ.setdefault("MPLBACKEND", "Agg")
sys.dont_write_bytecode = True
import fitz
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "升力闭环测试" / "analyze_closed_loop.py"
BEFORE = ROOT / "data_process" / "fig8_10_revision" / "before"
OUT = ROOT / "output" / "fig8_10_revision"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def functions(path):
    return {node.name: ast.dump(node) for node in ast.parse(path.read_text(encoding="utf-8")).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def compare_axis(old, new):
    assert old.get_xlim() == new.get_xlim()
    assert old.get_ylim() == new.get_ylim()
    assert old.get_position().bounds == new.get_position().bounds
    assert len(old.lines) == len(new.lines)
    for a, b in zip(old.lines, new.lines):
        np.testing.assert_array_equal(a.get_xydata(), b.get_xydata())
        for getter in ("get_color", "get_linestyle", "get_linewidth", "get_marker",
                       "get_markersize", "get_markevery", "get_markerfacecolor"):
            assert getattr(a, getter)() == getattr(b, getter)()
    assert len(old.patches) == len(new.patches)
    for a, b in zip(old.patches, new.patches):
        np.testing.assert_array_equal(a.get_path().vertices, b.get_path().vertices)
        assert a.get_facecolor() == b.get_facecolor()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current = load_module(SOURCE, "current_fig8_10")
    previous = load_module(BEFORE / "analyze_closed_loop.py", "before_fig8_10")
    old_functions, new_functions = functions(BEFORE / "analyze_closed_loop.py"), functions(SOURCE)
    changed = {name for name in old_functions if old_functions[name] != new_functions[name]}
    assert changed == {"plot_freestream_ramp", "plot_representative",
                       "plot_representative_ramp_times", "main"}, changed
    old_tex = (BEFORE / "template.tex").read_text(encoding="utf-8")
    new_tex = (ROOT / "template.tex").read_text(encoding="utf-8")
    table = lambda text: text.split("Table\\,4", 1)[1].split("\\end{center}", 1)[0]
    assert table(old_tex) == table(new_tex), "Table 4 changed"
    paths = sorted(current.DATA_DIR.glob("*.ulg"), key=lambda p: int(p.name.split("-")[0]))
    protected = paths + list(current.OUTPUT_DIR.glob("*.csv")) + list(current.OUTPUT_DIR.glob("*.sqlite"))
    protected += list((ROOT / "data_process" / "control_revision").glob("*.csv"))
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in protected}
    runs = [current.load_run(path) for path in paths]
    # Recompute all nine Table 4 conditions independently, without writing them.
    table_rows = re.findall(r"^\d+\s*&.*$", table(new_tex), re.MULTILINE)
    for row in table_rows:
        cells = [cell.strip().rstrip("\\").strip() for cell in row.split("&")]
        target, ramp = map(int, cells[:2])
        nrmse = {}
        for method in current.METHOD_ORDER:
            values = []
            for run in runs:
                if (run.target_n, run.nominal_ramp_s, run.method) != (target, ramp, method):
                    continue
                mask = (run.timestamp_s >= run.t10_s) & (run.timestamp_s <= run.t90_s + 3)
                error = run.desired_n[mask] - run.measured_n[mask]
                values.append(float(np.sqrt(np.mean(np.square(error)))) / target * 100)
            nrmse[method] = float(np.mean(values))
        expected = [f"{nrmse[m]:.2f}" for m in current.METHOD_ORDER]
        expected += [f"{100 * (1 - nrmse['fb'] / nrmse['static']):.1f}",
                     f"{100 * (1 - nrmse['ff_fb'] / nrmse['fb']):.1f}"]
        assert cells[2:] == expected, (cells, expected)

    current.configure_plotting()
    old_figures, new_figures = {}, {}
    previous.save_figure = lambda fig, stem: old_figures.setdefault(stem, fig)
    previous.IMAGE_DIR = OUT / "unused_no_write"
    save = current.save_figure
    def save_and_capture(fig, stem):
        new_figures[stem] = fig
        save(fig, stem)
    current.save_figure = save_and_capture
    for module in (previous, current):
        module.plot_freestream_ramp(runs)
        module.plot_representative(runs)
        module.plot_representative_ramp_times(runs)

    report = {"raw_and_metrics_sha256": hashes, "table4_conditions_verified": len(table_rows),
              "unchanged_signal_and_metric_functions": True, "figures": {}}
    for number, stem in ((8, "fig9_freestream_ramp"), (9, "fig10_representative_response"),
                         (10, "fig14_ramp_time_response_20N")):
        fig = new_figures[stem]
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        record = {}
        if number > 8:
            original = old_figures[stem]
            for old_axis, new_axis in zip(original.axes[:3], fig.axes[:3]):
                compare_axis(old_axis, new_axis)
            original_legend = [t.get_text() for t in original.legends[0].texts]
            assert [t.get_text() for t in fig.legends[0].texts] == original_legend
            assert fig.legends[0].get_window_extent(renderer).y0 > max(
                ax.get_window_extent(renderer).y1 for ax in fig.axes)
            limits = [ax.get_ylim() for ax in fig.axes[3:]]
            assert len(set(limits)) == 1
            peaks = []
            for old_axis, axis in zip(original.axes[3:], fig.axes[3:]):
                assert axis.get_xlim() == old_axis.get_xlim()
                curves = [line for line in axis.lines if line.get_color() in current.COLORS.values()
                          and line.get_marker() in ("s", "o", "^")]
                assert [line.get_color() for line in curves] == [current.COLORS[m] for m in ("fb", "ff_fb")]
                original_curves = [line for line in old_axis.lines if line.get_marker() in ("s", "o")]
                for old_line, line in zip(original_curves, curves):
                    np.testing.assert_array_equal(old_line.get_xydata(), line.get_xydata())
                    assert old_line.get_linestyle() == line.get_linestyle()
                    low, high = float(np.min(line.get_ydata())), float(np.max(line.get_ydata()))
                    assert axis.get_ylim()[0] < low <= high < axis.get_ylim()[1]
                    peaks.append([low, high])
            record.update(upper_row_exactly_preserved=True, shared_error_ylim_n=limits[0],
                          error_peak_ranges_n=peaks, shared_legend_preserved_and_clear=True)
        else:
            axis = fig.axes[0]
            assert not axis.patches, "Figure 8 still has acceleration shading"
            assert [t.get_text() for t in axis.get_legend().texts] == ["1 s", "5 s", "10 s"]
            references = [current.representative_runs(runs, 20, ramp)["ff_fb"] for ramp in (1, 5, 10)]
            assert len(axis.lines) == 7  # 3 curves + 3 t90 markers + tau=0
            provenance = []
            legend_box = axis.get_legend().get_window_extent(renderer)
            for index, run in enumerate(references):
                curve, marker = axis.lines[2 * index:2 * index + 2]
                visible = (run.tau_s >= axis.get_xlim()[0]) & (run.tau_s <= axis.get_xlim()[1])
                np.testing.assert_array_equal(curve.get_ydata(), run.freestream_smooth_m_s[visible])
                np.testing.assert_array_equal(curve.get_xdata(), (run.timestamp_s - run.t10_s)[visible])
                assert abs(marker.get_xdata()[0] - (run.t90_s - run.t10_s)) < 1e-8
                display = axis.transData.transform(curve.get_xydata())
                assert not any(legend_box.contains(x, y) for x, y in display)
                assert run.tau_s[visible].min() < -1.9
                assert run.tau_s[visible].max() > run.t90_s - run.t10_s + 3
                provenance.append(dict(log=run.path.name, t10_s=run.t10_s, t90_s=run.t90_s))
            record.update(xlim_s=axis.get_xlim(), records=provenance, legend_clear=True)
        for extension in ("pdf", "png"):
            shutil.copy2(current.OUTPUT_DIR / f"{stem}.{extension}", OUT / f"figure{number}.{extension}")
        with fitz.open(OUT / f"figure{number}.pdf") as pdf:
            assert len(pdf) == 1 and not pdf[0].get_images(), "PDF contains raster images"
            assert len(pdf[0].get_drawings()) > 0
            pdf[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(OUT / f"figure{number}_pdf_render.png")
        record["vector_pdf_verified"] = True
        report["figures"][str(number)] = record
    assert all(digest(ROOT / name) == sha for name, sha in hashes.items())
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    plt.close("all")
    print(json.dumps({n: {k: v for k, v in item.items() if k != "records"}
                      for n, item in report["figures"].items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
