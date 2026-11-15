"""OCR 后按页面文字去重：同一页 PPT 的微动帧（打字/光标/动画）只留第一张"""
import glob
import json
import os
import re
import sys
from difflib import SequenceMatcher

D = sys.argv[1] if len(sys.argv) > 1 else "."


def norm(t):
    return re.sub(r"\s+", "", t or "")


total_before = total_after = 0
for p in sorted(glob.glob(os.path.join(D, "*_slides.json"))):
    short = os.path.basename(p).replace("_slides.json", "")
    d = json.load(open(p, encoding="utf-8"))
    slides = d.get("slides") or []
    if not slides:
        continue

    kept = [slides[0]]
    dropped_imgs = []
    for sl in slides[1:]:
        prev = kept[-1]
        a, b = norm(prev.get("text")), norm(sl.get("text"))
        # 两页都几乎没文字时，不能判同页（可能都是空镜/纯图页）
        if len(a) < 6 or len(b) < 6:
            kept.append(sl)
            continue
        same = a == b or SequenceMatcher(None, a, b).ratio() > 0.92
        # 章节标题变了就保留（不同章节的页不能合并）
        if same and (prev.get("header") or "") == (sl.get("header") or ""):
            prev["end"] = sl["end"]
            dropped_imgs.append(sl.get("img"))
        else:
            kept.append(sl)

    if not dropped_imgs:
        continue

    # 重编号 + 改名
    renamed = []
    for i, sl in enumerate(kept, 1):
        old = sl.get("img")
        new_name = f"{short}_{i:03d}.jpg"
        old_path = os.path.join(D, old) if old else None
        new_path = os.path.join(D, "slides", new_name)
        if old_path and os.path.exists(old_path) and old_path != new_path:
            os.replace(old_path, new_path)
        sl["idx"] = i
        sl["img"] = f"slides/{new_name}"
        renamed.append(sl)

    for img in dropped_imgs:
        if not img:
            continue
        f = os.path.join(D, img)
        if os.path.exists(f):
            os.remove(f)

    d["slides"] = renamed
    # 重新挂每句的 slide 号
    for s in d.get("segments", []):
        mid = (s.get("start", 0) + s.get("end", 0)) / 2
        s["slide"] = next((sl["idx"] for sl in renamed if sl["start"] <= mid < sl["end"]), len(renamed))

    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  {short}: {len(slides)} → {len(renamed)} 页（删 {len(dropped_imgs)}）")
    total_before += len(slides)
    total_after += len(renamed)

print(f"\n合计 {total_before} → {total_after} 页（-{total_before-total_after}）")
