"""给目录加内部跳转链接 + 全书书签（篇/章/节三级）"""
import re
from pathlib import Path

import pymupdf

BOOK = Path("/Users/Jin/Documents/Open Programs/funasr/sskt_book/book")
PDF = Path("/Users/Jin/Desktop/《放养硕博自救指南——从起步到发表》.pdf")
CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
      "十一":11,"十二":12,"十三":13,"十四":14,"十五":15}

# 收集篇/章/节标题（按文档顺序）
files = []
for p in BOOK.glob("*.md"):
    if p.name.startswith("_") or p.name == "全书.md":
        continue
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^## 第([一二三四五六七八九十]+)章", t, re.M)
    if m:
        files.append((CN.get(m.group(1), 99), t))
files.sort(key=lambda x: x[0])

heads = []   # (level, text)
for _, t in files:
    for line in t.split("\n"):
        if line.startswith("### "):
            heads.append((3, line[4:].strip()))
        elif line.startswith("## "):
            heads.append((2, line[3:].strip()))
        elif line.startswith("# ") and not line.startswith("## "):
            heads.append((1, line[2:].strip()))

doc = pymupdf.open(PDF)
n_cover = 1
n_toc = 2          # 目录页数（由合并脚本决定）
body_start = n_cover + n_toc    # 0-based 索引

print(f"总页数 {doc.page_count} | 目录页索引 {n_cover}~{body_start-1} | 正文从索引 {body_start}")

# 1) 定位每个标题在正文里的页码
loc = {}
for lvl, text in heads:
    key = text[:14]
    for i in range(body_start, doc.page_count):
        hits = doc[i].search_for(key)
        if hits:
            loc[text] = i
            break
    else:
        print(f"  ⚠️ 未定位: {text[:26]}")

print(f"定位成功 {len(loc)}/{len(heads)}")

# 2) 写书签
toc = [[1, "封面", 1], [1, "目录", n_cover + 1]]
for lvl, text in heads:
    pg = loc.get(text)
    if pg is None:
        continue
    toc.append([lvl, text, pg + 1])
toc.append([1, "封底", doc.page_count])
doc.set_toc(toc)

# 3) 目录页加跳转
added = 0
missed = []
for pi in range(n_cover, body_start):
    page = doc[pi]
    for lvl, text in heads:
        target = loc.get(text)
        if target is None:
            continue
        # 目录里条目可能被截断显示，用前 12 字匹配
        probe = text[:12]
        rects = page.search_for(probe)
        for r in rects:
            page.insert_link({
                "kind": pymupdf.LINK_GOTO,
                "from": r,
                "page": target,
                "to": pymupdf.Point(0, 0),
                "zoom": 0,
            })
            added += 1
            break

doc.saveIncr()
print(f"✓ 书签 {len(toc)} 条 | 目录可点条目 {added} 个")
