from pathlib import Path
p=Path('template.tex');s=p.read_text(encoding='utf-8')
s=s.replace('依次给出来流输入、控制输出及转速响应', '依次给出控制输出及转速响应')
start=s.index('{\\small 图12\\quad');end=s.index('\\end{center}',start)
s=s[:start]+r'''{\small 图12\quad 20 N期望升力、1 s来流加速工况下的前馈补偿过程：(a)两种方法的总控制输出及复合控制的前馈、反馈分量；(b)两种方法的实测转速与复合控制的前馈参考转速。两次试验分别以各自来流达到10\%增量的时刻对齐。灰色阴影为10\%—90\%加速段，两幅子图统一采用FF+FB试验的边界，$\tau\in[0,0.791]$ s。
\\ Fig.\,12 \quad Feedforward compensation at a desired thrust of 20 N with a 1 s inflow acceleration time: (a) total control outputs and the feedforward and feedback components of combined control; (b) measured rotor speeds and the feedforward rotor-speed reference. Each trial is aligned at its own 10\% inflow-increment instant. Gray shading indicates the 10\%--90\% acceleration segment; both panels use the FF+FB trial boundaries, $\tau\in[0,0.791]$ s.}
\vskip1mm
{\scriptsize\raggedright 注：(a)比较日志中同一控制器叠加节点的归一化输出，不代表最终PWM输出。加速段阴影不同于完整评价窗口$[t_{10},t_{90}+3\,\mathrm{s}]$。实测转速保留全部原始采样点。\par}}
''' + s[end:]
p.write_text(s,encoding='utf-8')
