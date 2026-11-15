"""
PPT 页截图 → OCR 文字，合并进 slide json
=========================================
用 macOS Vision 框架（先编译：swiftc -O ocr_vision.swift -o ocr_vision）

用法：
  python ocr_slides.py <逐字稿目录>

清洗规则：
  - 单节内出现频率 >= 一半页数 的短行 = 页眉/页脚/水印/logo，剔除
  - 纯符号、单字符碎片、置信度 < 0.3 的行剔除
结果写回每个 slide 的 `text`（空格拼接的整页文字）和 `lines`（逐行）。
"""

import glob
import json
import os
import re
import subprocess
import sys
from collections import Counter

D = sys.argv[1] if len(sys.argv) > 1 else "."
BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr_vision")
JPUNK = re.compile(r"^[\s\W_]+$", re.UNICODE)


def ocr(img_path):
    try:
        r = subprocess.run([BIN, img_path], capture_output=True, text=True, timeout=60)
        return json.loads(r.stdout or "{}").get("lines", [])
    except Exception as e:
        print(f"    OCR 失败 {os.path.basename(img_path)}: {e}")
        return []


def drop_by_position(lines):
    """按位置丢页眉页脚：底部 7% 和顶部 4% 基本都是模板元素（版权行/logo/页码）"""
    out = []
    for l in lines:
        y = l.get("y", 0)
        h = l.get("h", 0)
        if y + h > 0.94:      # 页脚
            continue
        if y < 0.035:         # 顶栏 logo
            continue
        out.append(l)
    return out


for p in sorted(glob.glob(os.path.join(D, "*_slides.json"))):
    short = os.path.basename(p).replace("_slides.json", "")
    d = json.load(open(p, encoding="utf-8"))
    slides = d.get("slides") or []
    if not slides:
        continue

    per_page = []
    for sl in slides:
        img = os.path.join(D, sl["img"])
        lines = drop_by_position(ocr(img)) if os.path.exists(img) else []
        keep = []
        for l in lines:
            t = (l.get("text") or "").strip()
            if not t or len(t) < 2 or l.get("conf", 0) < 0.3 or JPUNK.match(t):
                continue
            keep.append(t)
        per_page.append(keep)

    # 模板行统计：在多页重复的行 = 页眉/页脚/水印/logo
    # 注意别设长度上限——"上海尤里卡信息科技有限公司 版权所有"这类页脚有 18 字以上
    freq = Counter()
    for lines in per_page:
        for t in set(lines):
            freq[t] += 1
    threshold = max(2, int(len(slides) * 0.4))
    repeated = {t for t, c in freq.items() if c >= threshold}
    # 重复行分两类：页脚/水印直接丢；其它（如统一章节标题）留作 header，不占正文
    FOOTER = re.compile(r"版权|www\.|\.com|公司|讲师|解螺旋|®|®|版权所有")
    boiler = {t for t in repeated if FOOTER.search(t)}
    header = next((t for t, c in freq.most_common() if t in repeated and t not in boiler), "")

    total_chars = 0
    for sl, lines in zip(slides, per_page):
        clean = [t for t in lines if t not in repeated]
        # 去掉行首残留的项目符号/箭头
        clean = [re.sub(r"^[>•·\-–—\u2022]+\s*", "", t).strip() for t in clean]
        clean = [t for t in clean if t]
        sl["header"] = header
        sl["text"] = " ".join(clean)
        sl["lines"] = clean
        total_chars += len(sl["text"])

    d["ocr"] = "macos-vision"
    json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{short}: {len(slides)} 页 OCR 完成 | 剔除模板行 {len(boiler)} 种 | 共 {total_chars} 字")
