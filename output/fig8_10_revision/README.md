# 图8–10绘图修订

本目录的 `figure8.pdf`、`figure9.pdf`、`figure10.pdf` 为矢量文件；同名 PNG 为400 dpi预览。`*_pdf_render.png` 为直接渲染矢量PDF得到的检查图。

绘图源脚本：`data/升力闭环测试/analyze_closed_loop.py`（相对项目根目录）。仅重绘这三张图，不写统计文件：

```powershell
python "data/升力闭环测试/analyze_closed_loop.py" --figures8-10-only
```

复现数值与绘图对象核验、更新本目录输出：

```powershell
python data_process/verify_fig8_10_revision.py
```

- 图8使用20 N、FF+FB的11、17、23号记录，保留既有中值滤波数据，按各自`t10`对齐，横轴为真实秒数。1 s样式保持原样；5 s为橙色虚线，10 s为青绿色点划线。同色圆点分别标记`t90`，不使用共同加速段阴影。显示范围为−2至11.933987 s。
- 图9、图10上排曲线、坐标范围、背景、样式及整图共享图例与修订前逐项核验一致；下排删除Static，仅保留FB、FF+FB，方法样式跨图一致。图9下排三列统一−3.0至5.5 N，图10统一−2.5至5.5 N，包含原显示时间范围内全部误差峰值。
- 原始ULog、CSV、SQLite文件校验值在重绘前后相同。数据载入、滤波、检测、统计等原有函数的AST未变，表4文本未变，全部9组结果独立复算与表4一致。详情见`verification.json`。
- `template.tex`已同步中英文图注；编译两遍并检查论文中第10、11、12页的图与图注，无新增文字裁切或图例遮挡。
- 已检查PNG及PDF渲染。图10上排10 s子图原有面板标注与曲线交叠；按上排全部保持不变的要求保留原状。

脚本保留原输出文件名，并同步论文引用的`Image/fig10_ramp_time_response_20N.pdf`。原始数据、评价窗口`[t10, t90+3 s]`和表4结果均未修改，也未增加平滑。
