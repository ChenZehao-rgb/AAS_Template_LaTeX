# 图 1(a)：真实 1 s 补偿日志，无限幅离线重建

数据源：`data/传感器补偿/补偿-rawdate显示限幅.ulg`。用户确认使用公式：

`T_hat=(sensor2-b0+36.839*ay(t-0.030)-3.332*ax(t-0.030))*0.00980665`。

原日志 `thrust_data.thrust_raw_data_1` 中负值被截为 0，不能直接从截断曲线反演。现从完整的原始 sensor2 和 vehicle_acceleration 重算，计算前、滤波前后均不做力值限幅，也不对截断曲线插值。保留所有原始力样本；加速度采用已发布且采样时间不晚于目标时刻的最新样本，沿用 30 ms 固定延迟，无拟合时间平移或系数调整。使用原有二阶 Kalman 滤波器和日志参数 Q 标准差 5、R 标准差 0.05，在整段日志上递推后截取绘图区间。

日志未记录模块启动时的 b0，因此用前 20 个已记录 sensor2 样本均值 −17 g；前后曲线使用同一个零偏。该曲线是按确认公式进行的离线重建，不能宣称逐点恢复了当时固件的真实无限幅输出。未限幅的在线片段与现有源码规则不能逐点复现，完整加速度历史、启动零偏及固件运行状态也未完全记录。

来流 10%–90% 上升时间：0.839708 s。绘图区间为相对 t10 的 −3 至 4.839708 s；RMSE 区间为 t10 至 t90+3 s。

| 信号 | RMSE (N) | 最大绝对值 (N) |
|---|---:|---:|
| 未补偿原始输出，共用零偏 | 2.5971 | 4.1972 |
| 未补偿，同样滤波（附加核对） | 2.6884 | 4.4919 |
| 无限幅补偿，未滤波 | 0.5221 | 2.2002 |
| 无限幅补偿，滤波后 | 0.4125 | 1.3797 |

图中沿用“上：原始未补偿，下：补偿后滤波”的布局，图示两行的 RMSE 差异同时包含滤波影响。完整 CSV 另含相同滤波下的前后输出。5 s/10 s 的原始曲线保持原数据处理方式（0.0098 N/unit、无额外零偏），上下排纵轴均恢复为 −6 至 4 N。按用户要求删除图内“离线重建（无限幅）”标注。1 s 使用源码 0.00980665 N/g 及共用零偏，处理差异已保留在记录中。

- `motor_off_force_sensor_1s_reconstructed.pdf/.png`：单独图 1(a)。
- `motor_off_force_sensor_compensation.pdf/.png`：替换 (a) 后的完整三列图。
- `reconstructed_1s_full_log.csv`：全部原始力样本及各补偿项、未限幅输出。
- `reconstructed_1s_plot_data.csv`：图示区间的数据。
- `logged_clipped_reference.csv`：原始在线限幅输出，仅作对照。
- `analysis_summary.json`、`source_manifest.json`、`verification.json`：计算设置、来源哈希与检查结果。

生成：`python data_process/plot_sensor_new_1s_reconstruction.py`。

校验：`python data_process/verify_sensor_new_1s_reconstruction.py`。

完整图已同步至 `output/deployment_sensor_figures/` 同名文件；旧图片备份在该目录的 `before_new_true_1s/`。旧 `plot_deployment_sensor_figures.py` 和该目录原有分析 JSON/CSV 属于原先图的历史计算，本次图的当前依据是本目录的记录与上述新脚本。
