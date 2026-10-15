"""Compare matched measured-RPM response events, not phase or transport delays.

Run: python data_process/analyze_response_timing.py
Uses raw logged inflow for timing, and identical baseline/plateau rules.
Each trial is aligned at its own previously defined inflow t10.
"""

import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data_process" / "control_revision"


def write_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    source = next((ROOT / "data").glob("*/analyze_closed_loop.py"))
    spec = importlib.util.spec_from_file_location("timing_analysis", source)
    analysis = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = analysis
    spec.loader.exec_module(analysis)
    paths = sorted(analysis.DATA_DIR.glob("*.ulg"), key=lambda p: int(p.name.split("-")[0]))
    runs = [analysis.load_run(p) for p in paths
            if analysis.parse_filename(p)[1:3] == (20, 1)]
    rows = []
    summary = []
    for run in runs:
        if run.method == "static":
            continue
        base = (run.tau_s >= -2.0) & (run.tau_s <= -0.5)
        hold = ((run.timestamp_s >= run.t90_s + 2.0)
                & (run.timestamp_s <= run.t90_s + 3.0))
        times = {}
        for signal, values in (("raw_inflow", run.freestream_m_s),
                               ("model_rpm", run.model_rpm),
                               ("measured_rpm", run.measured_rpm)):
            low, high = float(np.median(values[base])), float(np.median(values[hold]))
            for fraction in (0.2, 0.5, 0.8):
                mask = ((run.tau_s >= 0.0) & (run.timestamp_s <= run.t90_s + 3.0)
                        & (values >= low + fraction * (high - low)))
                indices = np.flatnonzero(mask)
                assert len(indices)
                time = float(run.tau_s[indices[0]])
                times[signal, fraction] = time
                rows.append(dict(log=run.path.name, method=run.method, signal=signal,
                                 fraction=fraction, baseline_median=low,
                                 plateau_median=high, event_tau_s=time,
                                 interpretation="amplitude_event_time_not_phase_delay"))
        for fraction in (0.2, 0.5, 0.8):
            summary.append(dict(method=run.method, fraction=fraction,
                                inflow_event_tau_s=times["raw_inflow", fraction],
                                rpm_event_tau_s=times["measured_rpm", fraction],
                                rpm_minus_inflow_event_s=(times["measured_rpm", fraction]
                                                         - times["raw_inflow", fraction])))
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "response_timing_events_20N_1s.csv", rows)
    write_csv(OUT / "response_timing_comparison_20N_1s.csv", summary)
    for row in summary:
        print(row)
    analysis.configure_plotting()
    analysis.OUTPUT_DIR = OUT
    analysis.plot_mechanism(runs)
    print("Updated manuscript Figure 12 with the matched feedback-only RPM and inflow.")


if __name__ == "__main__":
    main()
