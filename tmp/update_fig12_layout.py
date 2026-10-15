from pathlib import Path
p=Path('template.tex');s=p.read_text(encoding='utf-8')
s=s.replace('转速对照进一步显示，复合控制较早建立了补偿所需的转速增量。以两种方法各自的扰动前、后平台确定转速增量，', '转速对照以两种方法各自的扰动前、后平台确定转速增量，')
s=s.replace('在相同PID参数下，该工况的升力NRMSE由9.06\\%降至3.87\\%，降低57.3\\%。', '上述时刻由原始采样序列首次越阈确定，保留实测波动，不能将其解释为统一的相位或传输延迟。在相同PID参数下，图9(b)和表4显示该工况的升力NRMSE由9.06\\%降至3.87\\%，降低57.3\\%。')
# Keep the discussion of Fig. 11 with Fig. 11, and fill the left column with
# the Fig. 12 discussion before the indivisible tall Fig. 12 occupies the right.
start=s.index('\\begin{center}\n\\vbox{\n\\centerline{\\includegraphics[width=8cm]{Image/fig13_feedforward_mechanism.pdf}}')
end=s.index('\\end{center}',start)+len('\\end{center}')
figure=s[start:end];s=s[:start]+s[end:]
idx=s.index('\\section{结论}')
s=s[:idx]+figure+'\n\n'+s[idx:]
p.write_text(s,encoding='utf-8')
