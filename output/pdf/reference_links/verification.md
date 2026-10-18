# 图片与参考文献引用修复记录

日期：2026-10-18

## 修改范围

- 论文源码仅修改根目录 `template.tex`；重建根目录 `template.pdf` 及相应辅助文件。
- 本目录 `template.pdf` 是重建 PDF 的交付副本。
- 已读取主文件、`aas.cls`、`aas.cfg`、模板示例 `correct.tex` 和构建配置。主文件没有通过 `input` 或 `include` 引入其他正文文件；未修改历史备份和独立数据处理片段。
- 保留 `aas.cls`、`aas.cfg`、所有图片文件、图片尺寸、数学表达式和完整参考文献条目；保留双栏及通栏结构。

## 宏包与写法

`aas.cls` 没有加载 cite、natbib 或 hyperref，但重定义了上标式 `\@cite` 和不带方括号的文献表编号。当前稿件原先手写的是行内 `[n]`，且导言区已选择 natbib 的 numbers 模式，因此沿用稿件的行内数字格式。移除 `cite`，保留 `natbib[numbers,sort&compress]`，显式设置 `numbers,square,comma`。文献表仍使用原有 `thebibliography` 和 20 个 `\bibitem`，没有启用 BibTeX，也没有改动条目内容或引用键。

`hyperref` 仍在其他宏包之后加载一次，保留 `bookmarksnumbered=true`，增加 `hidelinks`。链接跟随所在正文的颜色，无彩色边框，没有新增图目录或文献反向链接。

稿件原本没有 figure/figure* 浮动体或实际的 subfigure 命令，所有图题都是 center/vbox 内的手排中英双语文字。为保持排版，新增两个辅助宏：

- `\aasfigurestart` 在图片顶部递增真实 figure 计数器并建立锚点；图题用 `\thefigure`，整图 `\label` 放在图题之后。
- `\aassubfigurelabel{...}` 使用已加载 subfigure 宏包的 subfigure 计数器及主图号加 `(a)` 的格式，并恢复整图锚点，防止整图标签误指向最后一个子图。

正文整图示例：`图 \ref{fig:quadrotor_frames}`。

正文子图示例：`图 \ref{fig:thrust_responses:b}`，输出为“图 11(b)”，不再另写括号或字母。边界空格保留 xeCJK 原有中西文间距及换行行为。

文献示例：`\cite{3}`、`\cite{6,7}`、`\cite{4,19,20}`。

图 4、图 6 的子图分别锚定到独立图片；其余子图已合成在同一个图片文件中，子图链接定位到该组合图顶部。没有拆分或修改图片。

## 编译与验证

采用工程原有 XeLaTeX 引擎，以 latexmk 执行必要的多轮编译并收敛：

```powershell
latexmk -xelatex -synctex=1 -interaction=nonstopmode -file-line-error -halt-on-error template.tex
```

另在 `_build_check/reference_links` 完成独立多轮编译；已确认根目录交付 PDF 与独立构建的页面文字、书签和全部链接坐标/目标一致。

- 共 14 幅整图、22 个子图标签；替换正文 27 处图片引用及 23 处文献引用命令。
- 整图编号为 1 至 14；子图编号如 3(a)、6(b)、11(b)，无字母或括号重复。
- PDF 含 13 个整图链接、14 个子图链接、28 个文献编号链接、29 个公式链接；全部内部链接目标可解析，指向有效页码，链接边框为零。
- 20 个引用键均唯一且全部有对应条目；所有文献目标均存在。
- 页数保持 13 页；原有 16 个 PDF 书签的标题、层级及页码与修改前完全一致；原有公式编号保持一致。
- 独立兼容性样例验证了单篇引用、乱序多篇引用和连续编号压缩：`\cite{7,3,1,6,2,5}` 输出 `[1–3, 5–7]`；可见端点编号均带正确的文献链接。
- 最终日志没有未定义引用、未定义文献引用、重复标签、重复超链接目标或宏包选项冲突。原有 ctex 弃用提示和 21 条 Overfull 提示仍在；图片导入时原有 PDF 版本/标签提示也仍在，本次没有调整模板版式或图片以消除这些提示。
- 已渲染全部 13 页为总览，并查看第 5、8、13 页的放大图，检查图题、子图字母、通栏图和参考文献排版。

验证使用 PDF 链接注释、命名目标及页面渲染，未在桌面 PDF 阅读器中进行鼠标实点测试。

## 待确认引用

无。现有手写图片编号和文献编号均能明确匹配；数学区间 `$[0,1]$` 及算法行号选项 `[1]` 保持不变。

机器可读核验记录：本目录 `verification.json`。修改前快照、编译日志和兼容性样例保存在 `_build_check/reference_links_revision`。
