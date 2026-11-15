"""成品体检：质量闸门 + 目录跳转反查 + 分页核查

用法：python check_book.py <书.pdf>
只依赖 pymupdf。不过闸门的项会标 ✗，全部 ✓ 才算过。
"""
import re
import sys
from pathlib import Path

import pymupdf

p = Path(sys.argv[1])
d = pymupdf.open(p)
flat = re.sub(r"\s", "", "".join(pg.get_text() for pg in d))

print(f"文件 {p.name}")
print(f"页数 {d.page_count} | 书签 {len(d.get_toc())} | 汉字 {len(re.findall('[\u4e00-\u9fff]', flat))}")

# --- 目录跳转反查 ---
# 目录页假定为第 2 页起；若目录多页，按书签“目录”条目找
ok = bad = 0
for pi in range(1, min(4, d.page_count)):
    pg = d[pi]
    if "目" not in pg.get_text()[:40]:
        break
    for l in pg.get_links():
        if l["kind"] != pymupdf.LINK_GOTO:
            continue
        label = pg.get_textbox(l["from"]).strip()[:10].replace(" ", "")
        if label and label in d[l["page"]].get_text().replace(" ", ""):
            ok += 1
        else:
            bad += 1
            print(f"  ✗ 错跳 p{pi + 1} 「{label}」→ p{l['page'] + 1}")
print(f"目录跳转 对 {ok} / 错 {bad}")

# --- 质量闸门 ---
GATES = {
    "不是…而是": r"不是[^，。]{2,20}，?而是",
    "破折号": "——",
    "提示性冒号": r"一句话总结[:：]|关键点[:：]|关键是[:：]",
    "命令式记住": r"要记住|记住这|请记住|牢记",
    "品牌痕迹": "解螺旋|尤里卡|周志瑞|helix",
}
print("\n质量闸门:")
fail = 0
for name, pat in GATES.items():
    n = len(re.findall(pat, flat))
    fail += n > 0
    print(f"  {'✓' if n == 0 else '✗'} {name}: {n}")

# --- 分页核查 ---
chs = [pg for lv, _t, pg in d.get_toc() if lv == 2]
if len(chs) > 1:
    gaps = [chs[i + 1] - chs[i] for i in range(len(chs) - 1)]
    single = [g for g in gaps if g < 2]
    print(f"\n章起始页 {chs}")
    print(f"  章间格 {gaps}")
    print(f"  {'✓ 每章独立成页' if not single else f'✗ 有 {len(single)} 处章连载同页'}")

print(f"\n{'全过' if fail == 0 and bad == 0 else '有未过项，逐条修'}")
sys.exit(0 if fail == 0 and bad == 0 else 1)
