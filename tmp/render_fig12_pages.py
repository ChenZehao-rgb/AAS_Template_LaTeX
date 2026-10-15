import fitz
from pathlib import Path
p=Path('tmp/fig12_revision');p.mkdir(exist_ok=True)
d=fitz.open('template.pdf')
for i,page in enumerate(d):
 t=page.get_text()
 if 'Feedforward compensation' in t or '图12' in t:
  print(i+1, t[:180], t[-300:])
  page.get_pixmap(matrix=fitz.Matrix(1.7,1.7)).save(p/f'page-{i+1}.png')
