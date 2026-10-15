from pathlib import Path
p=Path('template.tex');s=p.read_text(encoding='utf-8')
s=s.replace('分别约为0.300 s和0.410 s，即复合控制提前约0.11 s', '分别约为0.277 s和0.415 s，即复合控制提前约0.14 s')
s=s.replace('提前约0.11 s', '提前约0.14 s')
p.write_text(s,encoding='utf-8')
