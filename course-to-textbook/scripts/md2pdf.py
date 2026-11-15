"""
Markdown → 教材版式 HTML（供 Chrome headless 打印成 A4 PDF）

用法（必须在 md 所在目录运行，否则 figs/ 相对路径断开）：
    python md2pdf.py 第一篇.md ./_tmp.html
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless --disable-gpu \
      --no-pdf-header-footer --print-to-pdf="$HOME/Desktop/书名_第一篇.pdf" \
      "file://$(pwd)/_tmp.html"

依赖：uv pip install markdown pymupdf

要点：
  - 正文宋体（长文衬线耐久读），标题黑体，1.95 行高
  - 图注（图片后的斜体段）自动变居中 9.5pt 灰字
  - 表格 break-inside:avoid，避免跨页劈开
  - 英文直引号在 md 阶段就该换掉（见同目录 SKILL.md 的硬要求第 3 条）
"""
import sys

import markdown

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "_tmp.html"

md = open(SRC, encoding="utf-8").read()
html_body = markdown.markdown(
    md, extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
)

CSS = """
@page { size: A4; margin: 20mm 18mm 18mm 18mm; }
* { box-sizing: border-box; }
body {
  font-family: "Songti SC", "STSong", "SimSun", serif;
  font-size: 11.5pt; line-height: 1.95; color: #1c1c1c;
  text-align: justify; hyphens: none;
}
h1, h2, h3, h4 {
  font-family: "PingFang SC", "Hiragino Sans GB", "Heiti SC", sans-serif;
  color: #12202e; break-after: avoid; page-break-after: avoid;
}
h1 {
  font-size: 20pt; margin: 0 0 6pt; padding-bottom: 8pt;
  border-bottom: 2.5pt solid #12202e; letter-spacing: .5pt;
}
h2 { font-size: 15pt; margin: 22pt 0 9pt; padding-left: 9pt; border-left: 4pt solid #2f5f8f; }
h3 { font-size: 12.5pt; margin: 15pt 0 6pt; color: #1f3a55; }
p { margin: 0 0 8.5pt; }
strong { font-weight: 700; color: #0d1620; }
em { font-style: normal; color: #4a5560; }

img { max-width: 100%; display: block; margin: 10pt auto 4pt; }
/* 图注：图片后紧跟的斜体段 → 居中灰字 */
p > img + em, p em:only-child {
  display: block; text-align: center; font-size: 9.5pt; color: #6b7885;
  margin-top: 4pt; font-family: "PingFang SC", sans-serif;
}

blockquote {
  margin: 9pt 0; padding: 9pt 12pt; background: #f7f8fa;
  border-left: 3pt solid #b8c4d0; color: #33414f; font-size: 10.8pt;
}
blockquote p { margin: 0 0 5pt; }
blockquote p:last-child { margin-bottom: 0; }

table {
  width: 100%; border-collapse: collapse; margin: 10pt 0 12pt;
  font-size: 10pt; font-family: "PingFang SC", sans-serif;
  break-inside: avoid; page-break-inside: avoid;
}
th, td { border: 0.6pt solid #d5dbe2; padding: 5pt 7pt; text-align: left; vertical-align: top; line-height: 1.6; }
th { background: #eef2f6; font-weight: 700; color: #12202e; }
td:first-child { white-space: nowrap; }

ul, ol { margin: 0 0 9pt; padding-left: 17pt; }
li { margin-bottom: 4pt; }
li > p { margin-bottom: 3pt; }

code {
  font-family: "SF Mono", Menlo, monospace; font-size: 9.5pt;
  background: #f0f3f6; padding: 1pt 3.5pt; border-radius: 2pt; color: #1f3a55;
}
hr { border: none; border-top: 0.8pt solid #dfe4ea; margin: 16pt 0; }
h1, h2, h3 { break-inside: avoid; }
"""

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>{SRC}</title>
<style>{CSS}</style></head>
<body>{html_body}</body></html>"""

open(OUT, "w", encoding="utf-8").write(HTML)
print(f"HTML 已写：{OUT}")
print("下一步：用绝对路径 file:// 调 Chrome 打印；图必须在同目录的 figs/ 下")
