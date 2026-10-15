# 当前论文图11、图12、图13文字与数学排版更新

以 `template.tex` 中的实际图片引用及工况定位，未按旧文件图号定位。

| 当前图号 | 内容 | 绘图函数 | 正文引用的图片文件 | 交付文件 |
| --- | --- | --- | --- | --- |
| 图11 | 1 s来流加速，15、20、25 N期望升力响应 | `plot_representative` | `Image/fig10_representative_response.pdf` | `figure11.pdf`、`figure11.png` |
| 图12 | 20 N期望升力，1、5、10 s来流加速响应 | `plot_representative_ramp_times` | `Image/fig10_ramp_time_response_20N.pdf` | `figure12.pdf`、`figure12.png` |
| 图13 | 三种控制方法归一化绝对跟踪误差随来流速度变化 | `plot_speed_error` | `Image/fig12_speed_error.pdf` | `figure13.pdf`、`figure13.png` |

绘图脚本：`data/升力闭环测试/analyze_closed_loop.py`。

修改：图11期望升力改为数学格式的 T_d；图11、图12的纵轴改为“升力 T_m (N)”和“误差 T_e = T_d - T_m (N)”，变量均使用数学格式和下标。三幅图的固定控制量图例改为“固定控制量(Fixed input)”，FB及FF+FB名称不变。中文轴标签显式使用既有宋体，数学变量沿用既有Times字体。图12的工况标注移至图内空白处，避免与曲线重叠。

核验：使用28份原始日志重绘，对照修改前脚本逐一比较曲线数组、色彩、线型、标记、误差带、四分位带、坐标范围、图尺寸和子图位置，均一致；误差仍为期望升力减实测升力。数据读取、误差计算、分箱和统计函数未修改。原始日志、统计CSV、SQLite及正文文件的SHA-256在导出核验阶段保持不变。未运行全量统计或重写正文、表格。

图例字号保持图11、图12的7.5 pt和图13的7 pt，原有条目间距已能容纳新名称，无需缩小字号或修改布局。PDF检查确认无栅格图片嵌入，包含矢量绘图；PDF渲染预览已目视检查上下标、图例、重叠和裁切。`figure*_pdf_preview.png`为PDF实际渲染预览，`figure*.png`为400 dpi绘图导出。

已同步更新正文引用的Image目录PDF，以及原分析目录对应PDF/PNG。图12的旧别名`Image/fig14_ramp_time_response_20N.pdf`也保持同步。修改前脚本及被替换图片备份在`tmp/fig11_13_labels/before/`。核验记录见本目录`verification.json`。
