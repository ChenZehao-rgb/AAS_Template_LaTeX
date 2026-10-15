# 图7与表3交付

本版对原工作簿231组CT配对保持不变，统一误差定义、统计层级与图形。**上游空气密度/尺寸/实际转速理论修正和传感器噪声资料尚未闭合核实**；本版不声称已完成这些物理输入的一致性修正，具体证据及敏感性结果见audit_report_zh.md。

从项目根目录运行：

```powershell
python data_process/revise_fig7_table3.py
python data_process/verify_fig7_table3_revision.py
```

这两个入口不运行旧脚本的main。请使用上述新入口重现本版；直接运行旧绘图脚本仍会生成旧口径图表。依赖版本见audit.json。

如需重建表格预览：

```powershell
xelatex -interaction=nonstopmode -halt-on-error -output-directory=data_process/fig7_table3_revision data_process/fig7_table3_revision/table3_preview.tex
```

| 文件 | 内容 |
| --- | --- |
| fig7_revised.pdf / .svg | 图7矢量文件 |
| fig7_revised.png | 600dpi预览 |
| table3_revised.tex / .md | 新表3，展示两位小数 |
| table3_revised_unrounded.csv | 新表3全部计算精度，另含RMSE、CT均值、N及中位数 |
| table3_old_new_comparison.md / .csv | 新旧并排对照，CSV含未舍入差值 |
| condition_details.csv | 逐工况输入、CT、全部误差、实际转速/来流范围及来源行号 |
| source_record_lineage.csv | 877条已有记录到231点的对应关系；仅用于追溯 |
| paper_text_and_caption_zh.md | 简短中文指标说明及图注 |
| chat_summary_zh.md | 可直接贴回聊天的结果摘要 |
| audit_report_zh.md / audit.json | 数据、旧指标、CT定义与未解决问题核查 |
| sensitivity_existing_rpmcorr_NOT_primary.csv | 已有转速修正列的敏感性，不是主表 |
| theory_density_audit.csv | 原始理论力/CT反算密度的逐行证据 |
| signal_spread_review_NOT_noise_test.csv | CT与分支离散比，不是传感器噪声测量 |
| relative_error_unusable_conditions.csv | 已知非正/非有限CT问题清单；本次零行，不代表噪声核查通过 |
| verification.json | 独立复算与受保护文件校验结果 |
| before_20261013/ | 修改前图表、脚本、工作簿和正文快照及SHA256 |

同名Image/fig9_rotor_model_diagnostics.pdf和.png已更新为新图7，data_process/model_validation_table.tex已更新。template.tex仅替换图7图注块和内联表3块，两块之外逐字节保持不变；现有template.pdf未重编译，其他图表未修改。主目录其他model_validation*.csv/json仍属于旧版，保留用于比较，新版数值只取本目录文件。
