from pathlib import Path
p=Path('data_process/fig12_revision/README_zh.md')
s=p.read_text(encoding='utf-8-sig')
if not s.startswith('> 当前版本'):
 p.write_text('> 当前版本已按后续要求改为上下两幅紧凑子图，详见 [compact_revision.md](compact_revision.md)。以下为首次三层图修订的历史核对记录；原始信号与事件计算仍适用。\n\n'+s,encoding='utf-8')
