"""Read-only source audit; writes only new evidence under output/table4_audit."""
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from pyulog import ULog
from scipy.ndimage import median_filter

ROOT = Path(__file__).resolve().parents[1]
OLD = {r['log']: r for r in csv.DictReader((ROOT / 'data_process/control_revision/trial_metrics.csv').open(encoding='utf-8-sig'))}
trials = []
groups = defaultdict(list)
for p in sorted((ROOT / 'data/升力闭环测试/90度攻角-纯轴向来流').glob('*.ulg'), key=lambda p: int(p.name.split('-')[0])):
    target = int(p.name.split('-')[1].rstrip('N'))
    ramp = int(re.search(r'-(\d+)s', p.name)[1])
    method = 'static' if '静态' in p.name else ('ff_fb' if '前馈' in p.name else 'fb')
    u = ULog(str(p), message_name_filter_list=['thrust_control_data', 'thrust_data'])
    c = next(d.data for d in u.data_list if d.name == 'thrust_control_data')
    thrust = next(d.data for d in u.data_list if d.name == 'thrust_data')
    t = np.asarray(c['timestamp'], float) / 1e6
    tt = np.asarray(thrust['timestamp'], float) / 1e6
    v = np.asarray(c['bet_freestream_m_s'], float)
    hz = 1 / np.median(np.diff(t))
    kernel = min(max(3, round(.35 * hz)), len(v) if len(v) % 2 else len(v) - 1)
    kernel = kernel if kernel % 2 else kernel + 1
    smooth = median_filter(v, size=kernel, mode='nearest')
    lo = np.median(smooth[t <= min(t[0] + 5, t[-1])])
    hi = np.median(smooth[smooth >= np.percentile(smooth, 90)])
    th10, th90 = lo + .1 * (hi - lo), lo + .9 * (hi - lo)
    above = smooth >= th90
    sustain = max(3, round(.25 * hz))
    confirmed = np.convolve(above.astype(int), np.ones(sustain, int), mode='same') >= sustain
    i90 = np.flatnonzero(confirmed)[0]
    i10 = np.flatnonzero(smooth[:i90] <= th10)[-1] + 1
    first10 = np.flatnonzero(smooth > th10)[0]
    assert first10 == i10, (p.name, t[first10], t[i10])
    first90 = np.flatnonzero((np.arange(len(t)) >= i10) & above)[0]
    sustained_start = i90
    while sustained_start > i10 and above[sustained_start - 1]:
        sustained_start -= 1
    assert sustained_start == first90, p.name
    desired = np.asarray(c['thrust_desired[0]'], float)
    measured = np.interp(t, tt, np.asarray(thrust['thrust_kalman_filter_data_1'], float))
    error = desired - measured
    masks = [(t >= t[i10]) & (t <= t[j] + 3) for j in (i90, first90)]
    rm = [math.sqrt(math.fsum(float(x) ** 2 for x in error[m]) / int(m.sum())) for m in masks]
    stored = OLD[p.name]
    assert math.isclose(t[i10], float(stored['t10_s']), abs_tol=1e-10)
    assert math.isclose(t[i90], float(stored['t90_s']), abs_tol=1e-10)
    assert int(masks[0].sum()) == int(stored['samples'])
    assert math.isclose(rm[0], float(stored['rmse_n']), rel_tol=1e-12)
    assert np.all(desired[masks[0]] == target) and np.isfinite(error[masks[0]]).all()
    assert np.all(np.diff(t) > 0) and np.all(np.diff(tt) > 0)
    assert t[masks[0]][0] >= tt[0] and t[masks[0]][-1] <= tt[-1]
    row = dict(log=p.name, target_n=target, nominal_ramp_s=ramp, method=method,
               t10_s=float(t[i10]), t90_implemented_s=float(t[i90]),
               t90_first_crossing_s=float(t[first90]), t90_sustained_start_s=float(t[sustained_start]),
               t90_offset_s=float(t[i90] - t[first90]),
               window_duration_implemented_s=float(t[i90] + 3 - t[i10]),
               window_duration_first_crossing_s=float(t[first90] + 3 - t[i10]),
               samples_implemented=int(masks[0].sum()), samples_first_crossing=int(masks[1].sum()),
               rmse_implemented_n=rm[0], nrmse_implemented_pct=100 * rm[0] / target,
               rmse_first_crossing_n=rm[1], nrmse_first_crossing_pct=100 * rm[1] / target,
               max_control_gap_in_window_s=float(np.diff(t[masks[0]]).max()),
               squared_error_sum=float(np.square(error[masks[0]]).sum()))
    trials.append(row)
    groups[target, ramp, method].append(row)

assert len(trials) == len(OLD) == 28
rows = []
old_table = list(csv.DictReader((ROOT / 'data_process/control_revision/table4_unified_window.csv').open(encoding='utf-8-sig')))
tex = (ROOT / 'template.tex').read_text(encoding='utf-8').split('Table\\,4', 1)[1].split('\\bottomrule', 1)[0]
printed = re.findall(r'^\d+\s*&.*$', tex, re.M)
for target in (15, 20, 25):
    for ramp in (1, 5, 10):
        index = len(rows)
        row = dict(target_n=target, nominal_ramp_s=ramp)
        for mode in ('implemented', 'first_crossing'):
            val = {m: float(np.mean([x[f'nrmse_{mode}_pct'] for x in groups[target, ramp, m]])) for m in ('static', 'fb', 'ff_fb')}
            row.update({f'{m}_{mode}_nrmse_pct': x for m, x in val.items()})
            row[f'fb_{mode}_reduction_pct'] = 100 * (1 - val['fb'] / val['static'])
            row[f'ff_fb_{mode}_reduction_pct'] = 100 * (1 - val['ff_fb'] / val['fb'])
        vals = [row[f'{m}_implemented_nrmse_pct'] for m in ('static', 'fb', 'ff_fb')]
        vals += [row[f'{m}_implemented_reduction_pct'] for m in ('fb', 'ff_fb')]
        fields = ['static_nrmse_pct', 'fb_nrmse_pct', 'ff_fb_nrmse_pct', 'fb_reduction_pct', 'ff_fb_reduction_pct']
        assert all(math.isclose(x, float(old_table[index][k]), rel_tol=1e-12) for x, k in zip(vals, fields))
        actual = [c.strip().rstrip('\\').strip() for c in printed[index].split('&')]
        expected = [str(target), str(ramp)] + [f'{x:.{2 if i < 3 else 1}f}' for i, x in enumerate(vals)]
        assert actual == expected, (actual, expected)
        row['matches_manuscript'] = True
        rows.append(row)

out = ROOT / 'output/table4_audit'
out.mkdir(exist_ok=True, parents=True)
for name, data in [('trial_window_audit.csv', trials), ('table4_recalculated.csv', rows)]:
    with (out / name).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
repeat = [x for items in groups.values() if len(items) > 1 for x in items]
summary = dict(trial_count=len(trials), condition_method_count=len(groups), table_rows=rows, repeats=repeat,
               t90_offset_range_s=[min(x['t90_offset_s'] for x in trials), max(x['t90_offset_s'] for x in trials)],
               example_20N_1s=[x for x in trials if x['target_n'] == 20 and x['nominal_ramp_s'] == 1],
               all_finite_and_covered=True)
(out / 'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False, indent=2))
