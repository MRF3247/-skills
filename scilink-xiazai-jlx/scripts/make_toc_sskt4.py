"""目录：Python 加权装箱，静态 HTML，2 页填满，篇标题不孤立"""
import json
import re
from pathlib import Path

BOOK = Path("/Users/Jin/Documents/Open Programs/funasr/sskt_book/book")
CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
      "十一":11,"十二":12,"十三":13,"十四":14,"十五":15}

NOISE = {"泛读","精读","关键词","判断标准很简单","正确的顺序是三层","为什么","做法","自检",
         "错误写法","正确写法","注意","结论","要点","区别","定义","例子","示例"}


def subsections(body):
    out = []
    for m in re.finditer(r"\*\*(第[一二三四五六七八九十]+[步层条类阶段维度][^*\n]{0,28})\*\*", body):
        t = m.group(1).strip().rstrip("：:")
        if t not in out:
            out.append(t)
    if len(out) < 3:
        for m in re.finditer(r"\*\*([^*\n：:]{6,20})[：:]\*\*", body):
            t = m.group(1).strip()
            if t not in out and t not in NOISE:
                out.append(t)
    return out[:6]


files = []
for p in BOOK.glob("*.md"):
    if p.name.startswith("_") or p.name == "全书.md":
        continue
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^## 第([一二三四五六七八九十]+)章", t, re.M)
    if m:
        files.append((CN.get(m.group(1), 99), t))
files.sort(key=lambda x: x[0])

entries = []
cur_sec, sec_buf = None, []

def flush():
    global cur_sec, sec_buf
    if cur_sec and entries and entries[-1][0] == "sec":
        entries[-1] = ("sec", cur_sec, subsections("\n".join(sec_buf)))
    cur_sec, sec_buf = None, []

for _, t in files:
    for line in t.split("\n"):
        if line.startswith("### "):
            flush()
            cur_sec = line[4:].strip()
            entries.append(("sec", cur_sec, []))
            sec_buf = []
        elif line.startswith("## "):
            flush()
            entries.append(("ch", line[3:].strip(), None))
        elif line.startswith("# ") and not line.startswith("## "):
            flush()
            entries.append(("part", line[2:].strip(), None))
        elif cur_sec:
            sec_buf.append(line)
flush()

n_part = sum(1 for e in entries if e[0] == "part")
n_ch = sum(1 for e in entries if e[0] == "ch" and "结语" not in e[1])
n_sec = sum(1 for e in entries if e[0] == "sec")
n_sub = sum(len(e[2] or []) for e in entries if e[0] == "sec")

flat = []
for kind, txt, subs in entries:
    flat.append((kind, txt))
    for s in subs or []:
        flat.append(("sub", s))

W = {"part": 2.0, "ch": 1.7, "sec": 1.0, "sub": 0.92}
total = sum(W[k] for k, _ in flat)
HEAD = 2.8          # 首页表头占高（单位）
COLS_PER_PAGE = 2
n_cols = 4
per_col = (total + HEAD) / n_cols
caps = [per_col] * n_cols
caps[0] = per_col - HEAD

# 贪心装箱
cols = [[] for _ in range(n_cols)]
ci, used = 0, 0.0
for item in flat:
    k, _ = item
    w = W[k]
    if ci < n_cols - 1 and used + w > caps[ci] + 0.01:
        ci += 1
        used = 0.0
    cols[ci].append(item)
    used += w

# 篇/章标题不能落在栏末
for i in range(n_cols - 1):
    while cols[i] and cols[i][-1][0] in ("part", "ch") and len(cols[i]) > 1:
        cols[i + 1].insert(0, cols[i].pop())

def render(col):
    out = []
    for k, t in col:
        cls = k
        out.append(f'<div class="{cls}">{t}</div>')
    return "".join(out)

pages = []
for p in range(0, n_cols, COLS_PER_PAGE):
    chunk = cols[p:p + COLS_PER_PAGE]
    head = (f'<div class="head"><h1>目　录</h1>'
            f'<div class="meta">全书 {n_part} 篇 · {n_ch} 章 · {n_sec} 节</div></div>') if p == 0 else ""
    cols_html = "".join(f'<div class="col">{render(c)}</div>' for c in chunk)
    pages.append(f'<div class="page">{head}<div class="cols">{cols_html}</div></div>')

HTML = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><style>
  @page { size:A4; margin:13mm 12mm; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { font-family:"Songti SC","STSong",serif; color:#1c1c1c; }
  .page { break-after:page; }
  .page:last-child { break-after:auto; }
  .head { border-bottom:1.4pt solid #12202e; padding-bottom:1.8mm; margin-bottom:3mm; }
  .head h1 { font-family:"PingFang SC"; font-size:20pt; letter-spacing:3pt; color:#12202e; }
  .head .meta { font-family:"PingFang SC"; font-size:8.6pt; color:#8a96a3; margin-top:1.2mm; }
  .cols { display:flex; gap:6.5mm; align-items:flex-start; }
  .col { flex:1; }
  .part { font-family:"PingFang SC"; font-size:11pt; font-weight:700; color:#fff;
          background:#12202e; padding:1.5mm 2.6mm; margin:3mm 0 1.8mm; }
  .ch { font-family:"PingFang SC"; font-size:10pt; font-weight:700; color:#16202a;
        margin:2.4mm 0 1mm; padding-left:2mm; border-left:2.2pt solid #2f5f8f; }
  .sec { font-size:8.9pt; color:#2a3947; margin:1.1mm 0 0.4mm; font-weight:600; line-height:1.35; }
  .sub { font-size:8.1pt; color:#7b8794; margin:0 0 0.3mm 3.6mm; line-height:1.32; }
  .sub::before { content:"– "; color:#c2cbd4; }
</style></head>
<body>
""" + "".join(pages) + """
</body></html>"""

out = BOOK / "_toc.html"
out.write_text(HTML, encoding="utf-8")
print(f"{n_part} 篇 / {n_ch} 章 / {n_sec} 节 / {n_sub} 子标题")
print(f"权重总量 {total:.1f} → {n_cols} 栏 = {n_cols//COLS_PER_PAGE} 页")
for i, c in enumerate(cols):
    print(f"  栏{i+1}: {len(c)} 条 ({sum(W[k] for k,_ in c):.1f})")
print(f"✓ {out}")
