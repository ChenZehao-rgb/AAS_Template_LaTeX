# 当前图8：第二排坐标与紧凑排版修改

根据正文内容定位为 `Image/motor_off_force_sensor_compensation.pdf`，绘图入口是 `data_process/plot_sensor_new_1s_reconstruction.py`。保留当前1 s重建方法、5 s/10 s原有日志通道及数据处理方式。

## 尺寸与版式

| 项目 | 修改前 | 修改后 |
|---|---:|---:|
| Matplotlib画布（宽×高，英寸） | 6.10×3.60 | 6.10×3.10 |
| 画布（mm） | 154.94×91.44 | 154.94×78.74 |
| 紧边界矢量PDF（mm） | 147.45×90.09 | 149.77×78.26 |
| 论文插入宽度155 mm时的图高 | 94.71 mm | 80.99 mm |
| 上下排实际绘图区高度比 | 1:1 | 1:0.70 |
| 上排纵轴范围（N） | [−6, 4] | [−6, 4] |
| 下排纵轴范围（N） | [−6, 4] | [−2, 1] |
| 下排主刻度（N） | −6, −4, −2, 0, 2, 4 | −2, −1, 0, 1 |
| 上下排间距hspace | 0.11 | 0.08 |

插入宽度保持155 mm，图像占用高度减少13.72 mm（14.5%）。轴标题9 pt、刻度及RMSE文字7.5 pt，均保持原值。新的实际绘图区高度为38.30/26.81 mm。紧边界裁白及两行纵轴标题使PDF尺寸与名义画布不同，故分别报告。

## 完整数据与RMSE核对

范围来自完整绘图区间的全部原生样本，未按分位数截取、未增滤波、未删点或裁尖峰。1 s使用原有无限幅补偿滤波输出，5 s/10 s使用原有在线滤波通道。

| 工况 | 下排点数 | 完整曲线最小/最大值（N） | 加速段最大绝对峰值（N） | 上排RMSE（N） | 下排RMSE（N） |
|---|---:|---:|---:|---:|---:|
| 1 s | 784 | −1.379734 / 0.421617 | 1.379734 | 2.597092771490 | 0.412480936284 |
| 5 s | 1109 | −0.367565 / 0.110776 | 0.367565 | 1.451836972786 | 0.153366970942 |
| 10 s | 1496 | −0.294687 / 0.101382 | 0.294687 | 1.193832506500 | 0.091658879599 |

三条完整曲线均位于[−2,1] N内，统一范围上下分别至少保留0.620/0.578 N边距。整段日志的下排输出极值也已预查，见`baseline_data_audit.json`。图外未滤波补偿量未用于限制当前滤波曲线的纵轴。

全部6条曲线的数据和时间坐标与修改前逐点相同，配色、线型和标记设置相同，6个RMSE及计算窗口均未变。窗口继续使用t10至t90+3 s。滤波和重建函数的语法树与修改前一致，1 s绘图CSV及计算摘要哈希相同。

三列上下排分别共享横轴，范围依次为[−3,4.839708]、[−3,8.092967]、[−3,11.959712] s。各列阴影左右边界通过显示坐标完全相等检查。下排RMSE统一移至右下角，文字不覆盖曲线或零线。

保留零线、阴影和(a)(b)(c)；纵轴改为“未补偿传感器输出/补偿后传感器输出”，符号与正文一致为T_{m,i}/hat T_{m,i}，单位N。修正正文图号引用及错配英文图题，中英文均明确上下排纵轴范围不同。

## 文件与复现

- `motor_off_force_sensor_compensation.pdf`：纯矢量PDF，字体全部嵌入，无栅格对象。
- `motor_off_force_sensor_compensation.png`：600 dpi预览。
- `motor_off_force_sensor_compensation_155mm_preview.png`：论文155 mm宽度下的180 dpi预览。
- `plot_sensor_new_1s_reconstruction.py`：源代码快照；复现请使用项目内data_process目录的原入口，保留相对路径和同目录依赖。
- `all_six_native_plot_traces.csv`：全部6条实际绘图曲线，17位有效数字。
- `verification.json`：逐点、RMSE、线型、极值、坐标对齐、几何和矢量检查结果，全部通过。
- `before/`：此次修改前的源代码、图件、论文源文件及相关数据。
- `manuscript_figure8_page.png`：论文编译后的图8所在页预览。

在项目根目录运行：

```powershell
python data_process/plot_sensor_new_1s_reconstruction.py
python data_process/verify_figure8_compact.py
python data_process/verify_sensor_new_1s_reconstruction.py
```

正式论文插入路径`Image/motor_off_force_sensor_compensation.pdf`以及原输出目录均已同步。论文编译检查位于`tmp/figure8_compact_build/template.pdf`。
