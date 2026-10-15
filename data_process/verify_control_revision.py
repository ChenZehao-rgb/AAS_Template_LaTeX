"""Recompute revised Table 4 from ULog records using one window definition.

Run from the project root: python data_process/verify_control_revision.py
The original loader supplies active-channel signals and detected speed
crossings. RMSE and reductions below are calculated independently of its
trial_metrics/aggregate_conditions/comparison_conditions helpers.
"""

import csv
import importlib.util
import math
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "升力闭环测试" / "analyze_closed_loop.py"
OUT = ROOT / "data_process" / "control_revision"


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("control_analysis", SOURCE)
    analysis = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analysis
    spec.loader.exec_module(analysis)
    paths = sorted(analysis.DATA_DIR.glob("*.ulg"), key=lambda p: int(p.name.split("-")[0]))
    runs = [analysis.load_run(p) for p in paths]
    grouped = defaultdict(list)
    trials = []
    for run in runs:
        # Inclusive endpoints, uncorrected tracking error; no baseline removal.
        mask = (run.timestamp_s >= run.t10_s) & (run.timestamp_s <= run.t90_s + 3.0)
        errors = (run.desired_n - run.measured_n)[mask]
        assert len(errors) and np.isfinite(errors).all()
        assert np.allclose(run.desired_n[mask], run.target_n)
        rmse = math.sqrt(math.fsum(float(e) ** 2 for e in errors) / len(errors))
        normalized = 100.0 * rmse / run.target_n
        original = analysis.trial_metrics(run)
        assert math.isclose(rmse, original["disturbance_rmse_n"], rel_tol=1e-10)
        grouped[(run.target_n, run.nominal_ramp_s, run.method)].append(rmse)
        trials.append(dict(log=run.path.name, target_n=run.target_n,
                           nominal_ramp_s=run.nominal_ramp_s, method=run.method,
                           t10_s=run.t10_s, t90_s=run.t90_s,
                           window_end_s=run.t90_s + 3.0, samples=len(errors),
                           rmse_n=rmse, nrmse_pct=normalized))
    rows = []
    for target in (15, 20, 25):
        for ramp in (1, 5, 10):
            values = {m: math.fsum(grouped[target, ramp, m]) / len(grouped[target, ramp, m])
                      for m in analysis.METHOD_ORDER}
            assert values["ff_fb"] < values["fb"] < values["static"]
            rows.append(dict(target_n=target, nominal_ramp_s=ramp,
                             static_rmse_n=values["static"], fb_rmse_n=values["fb"],
                             ff_fb_rmse_n=values["ff_fb"],
                             static_nrmse_pct=100 * values["static"] / target,
                             fb_nrmse_pct=100 * values["fb"] / target,
                             ff_fb_nrmse_pct=100 * values["ff_fb"] / target,
                             fb_reduction_pct=100 * (1 - values["fb"] / values["static"]),
                             ff_fb_reduction_pct=100 * (1 - values["ff_fb"] / values["fb"])))
    write_csv(OUT / "trial_metrics.csv", trials)
    write_csv(OUT / "table4_unified_window.csv", rows)
    manuscript = (ROOT / "template.tex").read_text(encoding="utf-8")
    table = manuscript.split("Table\\,4", 1)[1].split("\\bottomrule", 1)[0]
    rendered_rows = re.findall(r"^\d+\s*&.*$", table, flags=re.MULTILINE)
    assert len(rendered_rows) == len(rows)
    fields = ("static_nrmse_pct", "fb_nrmse_pct", "ff_fb_nrmse_pct",
              "fb_reduction_pct", "ff_fb_reduction_pct")
    for line, row in zip(rendered_rows, rows):
        cells = [c.strip().rstrip("\\").strip() for c in line.split("&")]
        expected = [str(row["target_n"]), str(row["nominal_ramp_s"])]
        expected += [f"{row[k]:.{2 if i < 3 else 1}f}" for i, k in enumerate(fields)]
        assert cells == expected, (cells, expected)
    representative = analysis.representative_runs(runs)["ff_fb"]
    base = (representative.tau_s >= -2.0) & (representative.tau_s <= -0.5)
    hold = ((representative.timestamp_s >= representative.t90_s + 2.0)
            & (representative.timestamp_s <= representative.t90_s + 3.0))
    phase_rows = []
    for name, values in (("freestream", representative.freestream_smooth_m_s),
                         ("model_rpm", representative.model_rpm),
                         ("measured_rpm", representative.measured_rpm)):
        low, high = float(np.median(values[base])), float(np.median(values[hold]))
        crossing = np.flatnonzero((representative.tau_s >= 0.0)
                                 & (values >= low + 0.5 * (high - low)))[0]
        phase_rows.append(dict(signal=name, baseline_median=low,
                               plateau_median=high,
                               t50_tau_s=float(representative.tau_s[crossing])))
    for row in phase_rows:
        row["interpretation"] = "amplitude_event_time_not_phase_or_computation_delay"
    write_csv(OUT / "representative_timing.csv", phase_rows)
    event_offset = phase_rows[1]["t50_tau_s"] - phase_rows[0]["t50_tau_s"]
    # Cross-check the pre-existing CSV as well as the raw-log recomputation.
    with (analysis.OUTPUT_DIR / "condition_metrics.csv").open(encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            key = (int(row["target_n"]), int(row["nominal_ramp_s"]), row["method"])
            mean_rmse = math.fsum(grouped[key]) / len(grouped[key])
            assert math.isclose(mean_rmse, float(row["disturbance_rmse_n"]), rel_tol=1e-10)
    analysis.configure_plotting()
    analysis.OUTPUT_DIR = OUT
    analysis.IMAGE_DIR = OUT
    analysis.plot_representative_ramp_times(runs)
    shutil.copy2(OUT / "fig14_ramp_time_response_20N.pdf",
                 ROOT / "Image" / "fig10_ramp_time_response_20N.pdf")
    for row in rows:
        print(f"{row['target_n']} & {row['nominal_ramp_s']} & "
              f"{row['static_nrmse_pct']:.2f} & {row['fb_nrmse_pct']:.2f} & "
              f"{row['ff_fb_nrmse_pct']:.2f} & {row['fb_reduction_pct']:.1f} & "
              f"{row['ff_fb_reduction_pct']:.1f}")
    print(f"Verified {len(trials)} trials, {len(grouped)} cells, {len(rows)} comparisons.")
    print(f"Model-vs-inflow half-amplitude event offset (NOT a delay estimate): {event_offset:.6f} s")


if __name__ == "__main__":
    main()
