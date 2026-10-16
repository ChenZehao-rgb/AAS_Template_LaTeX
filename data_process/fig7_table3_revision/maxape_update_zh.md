# 表3改用MaxAPE（2026-10-16）

本次采用作者指定的NRMSE、MaxAPE、MAPE三个指标，直接从 `data/理论-实验对比结果.xlsx` 的231组既有实测/理论升力系数配对复算。各攻角33个工况，各工况等权；总体直接统计全部231点，不对分组NRMSE取平均。

设残差为 `e_i = CT_exp,i - CT_theory,i`，统计组G中实测均值为 `mean_G(CT_exp)`：

- `NRMSE_G (%) = 100 * sqrt(mean_G(e_i^2)) / mean_G(CT_exp)`。
- `MaxAPE_G (%) = max_G(100 * abs(e_i) / abs(CT_exp,i))`。
- `MAPE_G (%) = mean_G(100 * abs(e_i) / abs(CT_exp,i))`。

NRMSE沿用组实测均值归一化，MaxAPE和MAPE采用逐工况实测值为分母。NRMSE和MAPE与变更前一致；MaxAPE替换展示表中的归一化最大绝对误差。总体最大值19.5554605685%位于30°、3000 rpm档、J=0.421437的工况。

当前展示结果见 `table3_revised.md`、`table3_revised.tex`、论文 `template.tex`。未舍入数值见 `table3_revised_unrounded.csv` 的 `MaxAPE_pct`；其中旧的 `normalized_max_abs_error_pct` 仅保留为独立历史诊断，不是新表3的最大误差列。此前核查文档中22.18%的记录对应旧定义，本文件及新表为本次更新后的口径。

复算命令：`python data_process/update_table3_maxape.py`。该脚本验证231个原有配对未变，并以独立stdlib公式核对全部8行数据、显示舍入及正文修改范围。验证结果见 `maxape_verification.json`。

本次只变更统计指标，不重新配对工况、不修改实测或理论数据、不拟合模型。既有上游密度/转速一致性问题不在此次重算范围内。
