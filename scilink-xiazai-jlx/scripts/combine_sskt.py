"""合并全书 md（按章号排序）"""
import re
from pathlib import Path

BOOK = Path("/Users/Jin/Documents/Open Programs/funasr/sskt_book/book")
CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
      "十一":11,"十二":12,"十三":13,"十四":14,"十五":15}

files = []
for p in BOOK.glob("*.md"):
    if p.name.startswith("_") or p.name == "全书.md":
        continue
    t = p.read_text(encoding="utf-8")
    m = re.search(r"^## 第([一二三四五六七八九十]+)章", t, re.M)
    if m:
        files.append((CN.get(m.group(1), 99), p, t))
files.sort(key=lambda x: x[0])

parts = []
for i, (n, p, t) in enumerate(files):
    if i > 0:
        parts.append("\n\n---\n\n")
    parts.append(t.strip())

merged = "".join(parts)
out = BOOK / "全书.md"
out.write_text(merged, encoding="utf-8")

cn = len(re.findall(r"[\u4e00-\u9fff]", merged))
imgs = len(re.findall(r"!\[", merged))
print(f"✓ {out}  {len(files)} 章 {cn} 汉字 {imgs} 张图")
