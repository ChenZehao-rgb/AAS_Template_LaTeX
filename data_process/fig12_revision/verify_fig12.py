"""Independent native-log verification of Figure 12 data and rendered artists."""
import csv
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
from pyulog import ULog
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
SOURCE = next((ROOT / 'data').glob('*/analyze_closed_loop.py'))
spec = importlib.util.spec_from_file_location('figure12_analysis', SOURCE)
a = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = a
spec.loader.exec_module(a)
OUT = a.OUTPUT_DIR
with (OUT / 'fig12_rpm_events.csv').open(encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))
audit = json.loads((OUT / 'fig12_signal_audit.json').read_text(encoding='utf-8'))
assert len(rows) == 9 and len(audit['trials']) == 2
assert audit['source_script_sha256'] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
runs = []
for trial in audit['trials']:
    path = a.DATA_DIR / trial['log']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == trial['sha256']
    run = a.load_run(path)
    runs.append(run)
    u = ULog(str(path))
    topics = {x.name: x.data for x in u.data_list if x.multi_id == 0}
    c, rpm = topics['thrust_control_data'], topics['rpm']
    tau = c['timestamp'].astype(float) / 1e6 - trial['t10_s']
    win = (tau >= -2) & (tau <= trial['tau_window_s'][1])
    assert np.array_equal(run.tau_s, tau)
    assert np.allclose(c['thrust_control_out[0]'][win],
                       c['thrust_feedforward_out[0]'][win] + c['thrust_feedback_out[0]'][win],
                       atol=1e-6, rtol=0)
    for row in (r for r in rows if r['method'] == trial['method']):
        if row['signal'] == 'measured_rpm':
            t = rpm['timestamp'].astype(float) / 1e6 - trial['t10_s']
            y = -rpm['rpm_raw'].astype(float)
        else:
            t, y = tau, c['motor_speed[0]'].astype(float)
        low = np.median(y[(t >= -2) & (t <= -0.5)])
        high = np.median(y[(t >= trial['t90_s'] - trial['t10_s'] + 2)
                            & (t <= trial['t90_s'] - trial['t10_s'] + 3)])
        threshold = low + float(row['fraction']) * (high - low)
        eligible = (t >= 0) & (t <= trial['t90_s'] - trial['t10_s'] + 3)
        crossing = np.flatnonzero(eligible & (y >= threshold))[0]
        assert float(row['event_tau_s']) == t[crossing]
        assert float(row['event_observed_rpm']) == y[crossing]
        assert float(row['baseline_rpm']) == low
        assert float(row['plateau_rpm']) == high

# Inspect the actual artists without replacing the published files.
a.configure_plotting()
figures = []
a.save_figure = lambda fig, stem: figures.append(fig)
a.OUTPUT_DIR = ROOT / 'tmp' / 'fig12_revision' / 'artist_check'
a.plot_mechanism(runs)
fig = figures[0]
axes = fig.axes
assert len(axes) == 2  # no inflow panel, zoom, or event table
b, c = axes
assert b.get_shared_x_axes().joined(b, c)
assert [len(ax.lines) for ax in (b, c)] == [6, 4]
for i, run in enumerate(runs):
    method = run.method
    line = next(l for l in c.lines if l.get_label() == method.upper().replace('_', '+') + '实测')
    rpm = next(d.data for d in ULog(str(run.path)).data_list if d.name == 'rpm')
    t = rpm['timestamp'].astype(float) / 1e6 - run.t10_s
    y = -rpm['rpm_raw'].astype(float)
    mask = (t >= c.get_xlim()[0]) & (t <= c.get_xlim()[1])
    assert np.array_equal(line.get_xdata(), t[mask])
    assert np.array_equal(line.get_ydata(), y[mask])
    assert line.get_color() == a.COLORS[method]
    total = next(l for l in b.lines if l.get_label().startswith(method.upper().replace('_', '+') + '总'))
    assert total.get_color() == a.COLORS[method] and total.get_linestyle() == '-'
assert b.get_ylim()[0] < 0
assert all(0.8 <= l.get_linewidth() <= 1.0 for l in b.lines[:2] + c.lines[:2])
assert b.lines[2].get_color() != a.COLORS['ff_fb']
assert b.lines[3].get_linestyle() == '-'
assert all(l.get_marker() == 'None' for ax in (b, c) for l in ax.lines)
ff = next(r for r in runs if r.method == 'ff_fb')
for ax in (b, c):
    assert len(ax.patches) == 1 and len(ax.tables) == 0
    span = ax.patches[0]
    assert np.isclose(span.get_x(), 0)
    assert np.isclose(span.get_width(), ff.t90_s - ff.t10_s)
    assert span.get_zorder() < min(l.get_zorder() for l in ax.lines)
assert b.get_position().x0 == c.get_position().x0
assert b.get_position().x1 == c.get_position().x1
assert len(b.get_xticklabels()) == 0
old_events = ROOT / 'data_process' / 'fig12_revision' / 'compact_before' / 'fig12_rpm_events.csv'
assert old_events.read_bytes() == (OUT / 'fig12_rpm_events.csv').read_bytes()
old_script = (ROOT / 'data_process' / 'fig12_revision' / 'compact_before' / 'analyze_closed_loop.py').read_text(encoding='utf-8')
new_script = SOURCE.read_text(encoding='utf-8')
assert old_script.split('def mechanism_data(', 1)[1].split('def plot_mechanism(', 1)[0] == new_script.split('def mechanism_data(', 1)[1].split('def plot_mechanism(', 1)[0]
plt.close(fig)
result = {'status': 'PASS', 'native_event_rows_verified': len(rows),
          'unaltered_native_rpm_samples_per_trial': [t['rpm_samples_plotted'] for t in audit['trials']],
          'main_panel_curve_counts': [4, 3],
          'acceleration_shading_tau_s': [0.0, ff.t90_s - ff.t10_s],
          'existing_event_csv_unchanged': True, 'data_and_statistics_code_unchanged': True,
          'shared_time_axes': True, 'raw_log_hashes_verified': True,
          'script_hash_verified': True, 'negative_feedback_visible': True}
(ROOT / 'data_process' / 'fig12_revision' / 'verification.json').write_text(
    json.dumps(result, indent=2) + '\n', encoding='utf-8')
print(json.dumps(result, indent=2))
