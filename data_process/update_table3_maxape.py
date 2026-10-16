"""Update only Table 3 and its metric definitions from the 231 workbook pairs.

Run from the project root: python data_process/update_table3_maxape.py
NRMSE uses the measured group mean; MaxAPE/MAPE use measured point values.
The old normalized maximum remains an explicitly separate CSV diagnostic.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import revise_fig7_table3 as analysis

ROOT, OUT = analysis.ROOT, analysis.OUT


def main():
    sheets = analysis.legacy.load_sheets(analysis.legacy.DEFAULT_WORKBOOK)
    curves = sheets['curves']
    assert len(curves) == 231
    assert not curves.duplicated(['rpm_nom', 'alpha_deg', 'J']).any()
    assert curves[['C_T_exp', 'C_T_theory']].notna().all().all()
    assert (curves.C_T_exp > 0).all()
    detail = analysis.pd.read_csv(OUT / 'condition_details.csv')
    keys = ['rpm_nom', 'alpha_deg', 'J']
    pairs = ['C_T_exp', 'C_T_theory']
    for name in keys + pairs:
        assert analysis.np.allclose(curves[name], detail[name], rtol=0, atol=1e-14), name
    old_table = analysis.pd.read_csv(OUT / 'table3_revised_unrounded.csv')
    new = analysis.metrics(analysis.errors(curves))
    for field in ['NRMSE_pct', 'MAPE_pct', 'normalized_max_abs_error_pct']:
        assert analysis.np.allclose(new[field], old_table[field], rtol=1e-12, atol=1e-12), field

    # Independent stdlib calculation: do not call production metrics helpers.
    verified = []
    for angle, row in zip([0, 15, 30, 45, 60, 75, 90, None], new.to_dict('records')):
        group = curves if angle is None else curves.loc[curves.alpha_deg == angle]
        measured = [float(x) for x in group.C_T_exp]
        predicted = [float(x) for x in group.C_T_theory]
        errors = [y - yh for y, yh in zip(measured, predicted)]
        ape = [100 * abs(e) / abs(y) for e, y in zip(errors, measured)]
        expected = dict(NRMSE_pct=100 * math.sqrt(math.fsum(e * e for e in errors) / len(errors)) / statistics.fmean(measured),
                        MaxAPE_pct=max(ape), MAPE_pct=statistics.fmean(ape))
        assert len(group) == (231 if angle is None else 33)
        for key, value in expected.items():
            assert math.isclose(row[key], value, rel_tol=1e-12, abs_tol=1e-12), (angle, key)
        verified.append(dict(group=row['group'], N=len(group), **expected))
    assert math.isclose(new.iloc[-1].MaxAPE_pct, new.iloc[:-1].MaxAPE_pct.max(), rel_tol=1e-12)

    analysis.csv(new, 'table3_revised_unrounded.csv')
    analysis.write_table(new, analysis.legacy.build_angle_metrics(sheets['points']))
    markdown = analysis.markdown_table(new, [('group', '攻角/°'), ('N', 'N'), ('NRMSE_pct', 'NRMSE/%'),
                                               ('MaxAPE_pct', 'MaxAPE/%'), ('MAPE_pct', 'MAPE/%')])
    (OUT / 'table3_revised.md').write_text(markdown + '\n', encoding='utf-8')
    summary_path = OUT / 'summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    summary['overall'] = new.iloc[-1].drop(labels=['alpha_deg']).to_dict()
    summary['table3_display_metrics'] = ['NRMSE_pct', 'MaxAPE_pct', 'MAPE_pct']
    summary['metric_definitions'] = dict(NRMSE='100 * RMSE(CT_exp - CT_theory) / mean(CT_exp) within group',
                                         MaxAPE='max(100 * abs(CT_exp - CT_theory) / abs(CT_exp)) within group',
                                         MAPE='mean(100 * abs(CT_exp - CT_theory) / abs(CT_exp)) within group',
                                         normalized_max_abs_error_pct='retained historical diagnostic; not displayed in Table 3')
    analysis.save_json(summary_path, summary)

    path = ROOT / 'template.tex'
    original = path.read_bytes()
    nl = b'\r\n' if b'\r\n' in original else b'\n'
    anchor = '{\\small 表3\\quad'.encode('utf-8')
    assert original.count(anchor) == 1
    pos = original.index(anchor)
    start = original.rfind(b'\\begin{center}', 0, pos)
    end = original.index(b'\\end{center}', pos) + len(b'\\end{center}')
    block = original[start:end]
    block = block.replace(b'MaxErr$_{\\mathrm{norm}}$', b'MaxAPE')
    table_start = block.index(b'\\midrule')
    table_end = block.index(b'\\bottomrule')
    body = '\n'.join(f"{r.group} & {r.NRMSE_pct:.2f} & {r.MaxAPE_pct:.2f} & {r.MAPE_pct:.2f} \\\\" for r in new.itertuples())
    block = block[:table_start] + b'\\midrule' + nl + body.encode('utf-8').replace(b'\n', nl) + nl + block[table_end:]
    updated = original[:start] + block + original[end:]
    old = r'分攻角进行统计,采用归一化均方根误差(NRMSE)、归一化最大误差(MaxErr)和平均绝对百分比误差(MAPE)评价模型精度.前两项指标分别将升力系数的均方根误差和最大绝对误差除以对应统计组的实测升力系数均值;MAPE则为各工况相对误差绝对值的算术平均.'
    author_sentence = r'分攻角统计,使用对$C_{T,\mathrm{exp}}$的归一化均方根误差(NRMSE)、逐工况的最大绝对百分比误差(MaxAPE)和平均绝对百分比误差(MAPE)评价模型精度.'
    if old.encode('utf-8') not in updated:
        old = author_sentence
    prose = r'分攻角统计,使用对$C_{T,\mathrm{exp}}$的归一化均方根误差(NRMSE)、逐工况的最大绝对百分比误差(MaxAPE)和平均绝对百分比误差(MAPE)评价模型精度.NRMSE为升力系数的均方根误差除以对应统计组的实测升力系数均值;MaxAPE和MAPE分别为各工况绝对百分比误差的最大值和算术平均值,逐工况百分比误差以对应实测升力系数为分母.各攻角包含33个工况,总体统计直接使用全部231个工况,各工况等权.'
    old_b, prose_b = old.encode('utf-8'), prose.encode('utf-8')
    assert updated.count(old_b) == 1 or updated.count(prose_b) == 1
    if prose_b not in updated:
        updated = updated.replace(old_b, prose_b)
    # Explicitly tie the existing <20% statement to the new pointwise metric.
    claim_old = '在所有工况点下的最大误差小于$20\\%$'.encode('utf-8')
    claim_new = '在所有工况点下的最大绝对百分比误差为$19.56\\%$'.encode('utf-8')
    assert updated.count(claim_old) == 1 or updated.count(claim_new) == 1
    updated = updated.replace(claim_old, claim_new)

    # Verify all displayed cells, including their rounding, from the source.
    displayed = re.findall(rb'^([^\r\n&]+)\s*&([^\r\n]+)\\\\', block[block.index(b'\\midrule'):block.index(b'\\bottomrule')], re.M)
    assert len(displayed) == 8
    for (label, cells), row in zip(displayed, verified):
        assert label.decode('utf-8').strip() == row['group']
        assert [c.strip() for c in cells.decode().split('&')] == [f"{row[k]:.2f}" for k in ['NRMSE_pct', 'MaxAPE_pct', 'MAPE_pct']]
    # Current working-tree backup, not Git HEAD: unrelated user edits survive.
    backup = OUT / 'before_maxape_20261016/template.tex'
    if backup.exists():
        previous = backup.read_bytes()
        bpos = previous.index(anchor)
        bstart = previous.rfind(b'\\begin{center}', 0, bpos)
        bend = previous.index(b'\\end{center}', bpos) + len(b'\\end{center}')
        upos = updated.index(anchor)
        ustart = updated.rfind(b'\\begin{center}', 0, upos)
        current = updated[:ustart] + updated[updated.index(b'\\end{center}', upos) + len(b'\\end{center}'):]
        expected = (previous[:bstart] + previous[bend:]).replace(old_b, prose_b).replace(claim_old, claim_new)
        assert current == expected, 'Unexpected manuscript changes outside requested Table 3 definitions and claim'
    path.write_bytes(updated)
    analysis.save_json(OUT / 'maxape_verification.json', dict(status='PASS', source=str(analysis.legacy.DEFAULT_WORKBOOK.relative_to(ROOT)),
        source_sha256=analysis.sha256(analysis.legacy.DEFAULT_WORKBOOK), N=231, rows=verified,
        source_pairs_unchanged=True, independent_stdlib_recalculation=True, NRMSE_and_MAPE_unchanged=True,
        manuscript_scope='Table 3, metric definitions, and explicit MaxAPE wording of existing maximum-error claim',
        manuscript_sha256=hashlib.sha256(updated).hexdigest(), limitation='Frozen workbook-pair arithmetic; does not resolve upstream density/rpm consistency.'))
    print(markdown)
    print('PASS: 231 source pairs, 8 table rows, independent recomputation and manuscript scope.')


if __name__ == '__main__':
    main()
