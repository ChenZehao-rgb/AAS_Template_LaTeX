# 当前传感器补偿图

`motor_off_force_sensor_compensation` 的 PDF、PNG 与预览现已使用新日志重绘图 (a)。

当前计算脚本：`data_process/plot_sensor_new_1s_reconstruction.py`。

当前数据、方法说明及检查结果：`output/sensor_new_1s_reconstruction/README.md` 及同目录 CSV/JSON。图 (a) 按用户确认公式进行无限幅离线重建；按用户要求删除图内“离线重建（无限幅）”标注。独立1 s图仍使用 −6～4 N；当前论文图8上排保持 −6～4 N，下排三幅图统一为 −2～1 N，上下排高度比为1:0.7。

旧图片已备份至 `before_new_true_1s/`。本目录原有分析 JSON/CSV 和旧生成脚本属于修改前的历史计算，请使用新重建目录的数据复查当前图 (a)。

当前图8的紧凑排版、完整曲线极值和RMSE不变核对见 `output/figure8_compact/README_zh.md` 与 `verification.json`。
