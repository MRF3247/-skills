#!/usr/bin/env python3
"""量「版面是否撑满」：内容最低行到页脚蓝条的间距（逻辑 px 与百分比）。

用法：
    python3 check_bottom_gap.py 成品.png
    python3 check_bottom_gap.py 成品.png --limit 10 --logical-h 1440

为什么需要脚本：1080×1440 的卡靠缩略图看不出到底空 5% 还是 20%，用户会直接说
「下半部分还有很多空白」。验收标准：内容底到页脚 ≤ 5%（尾页 ≤ 10%）；
超了就去拉间距 / 放大元素（二维码、卡片 padding），不要靠加内容块填。

页脚识别：自底向上找连续的深蓝块（品牌页脚条），块顶即页脚上沿。
非蓝底页脚时用 --footer-px <逻辑高度> 手动给。
"""
import argparse
import sys

import numpy as np
from PIL import Image


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--logical-w", type=int, default=1080)
    ap.add_argument("--logical-h", type=int, default=1440)
    ap.add_argument("--limit", type=float, default=5.0, help="允许的最大空白百分比")
    ap.add_argument("--footer-px", type=int, default=0, help="手给页脚逻辑高度（0=自动识别）")
    ap.add_argument("--footer-blue", dest="footer_blue", action="store_true", default=True)
    ap.add_argument("--no-footer-blue", dest="footer_blue", action="store_false")
    a = ap.parse_args()

    arr = np.array(Image.open(a.image).convert("RGB"))
    h, w, _ = arr.shape
    scale = w / a.logical_w

    if a.footer_px > 0:
        footer_top = h - int(a.footer_px * scale)
        mode = f"手动 footer_px={a.footer_px}"
    elif a.footer_blue:
        footer_top = 0
        for y in range(h - 1, -1, -1):
            r, g, b = arr[y, w // 2]
            if b > 90 and r < 70 and g < 130:
                footer_top = y
            else:
                break
        if footer_top == 0:
            print("没识别到页脚深色条；改用 --footer-px <逻辑高度>", file=sys.stderr)
            return 2
        mode = "自动识别深蓝页脚"
    else:
        print("--no-footer-blue 需要配 --footer-px", file=sys.stderr)
        return 2

    rows = [y for y in range(footer_top - 1, -1, -1)
            if (arr[y].sum(axis=1) < 735).any()]
    if not rows:
        print("页脚上方全是白底：整页没有内容？", file=sys.stderr)
        return 2
    content_bottom = rows[0]

    gap_px = (footer_top - content_bottom) / scale
    pct = gap_px / a.logical_h * 100
    verdict = "OK" if pct <= a.limit else f"空太多（限 {a.limit}%）→ 拉间距/放大元素"

    print(f"图: {a.image}  {w}x{h}（{scale:g}x） 页脚: {mode}")
    print(f"内容底 y={content_bottom / scale:.1f}  页脚上沿 y={footer_top / scale:.1f}（逻辑）")
    print(f"剩余空白 {gap_px:.1f} px = {pct:.1f}% of {a.logical_h}  → {verdict}")
    return 0 if pct <= a.limit else 1


if __name__ == "__main__":
    raise SystemExit(main())
