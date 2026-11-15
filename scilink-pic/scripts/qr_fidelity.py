#!/usr/bin/env python3
"""验「卡面二维码还能不能扫码」——与源二维码图做归一化互相关，不靠目测。

用法（x/y/side 都填**逻辑 px**，即按 1080/1620 宽的版面坐标算）：
    python3 qr_fidelity.py --card /tmp/qr_card/lead.png \
        --qr /Users/Jin/Documents/素材/刀客轻研小助手二维码.jpg \
        --side 540 --x 270 --y 598 [--scale 2] [--search 40]

为什么要它：成品裁完、缩完、压完字之后，"看着清楚"不等于能扫。与源码做归一化
互相关（各自减均值除 std 再取均值）能直接判定是否为像素级等比缩放：
  ≥ 0.99  像素级等比缩放，可扫性等同源码
  0.95–0.99 轻度重采样，能用但先别交付前不吱声
  < 0.95  被重采样/遮挡/压了字，重出

位置怎么来（不要靠扫暗像素找，正文和页脚会把范围拉满整张图）：
  按 CSS 逐项加：页 padding + 区 padding + qrbox padding 得 x；
  y = 页顶 + 天头高 + (主标 margin + 行高×行数) + 线 + 区间 margin + 区 padding + qrbox padding。
  估不准也没关系：脚本会在这点 ±search 内先粗搜再精搜，报出最佳偏移。
"""
import argparse

import numpy as np
from PIL import Image


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = (a - a.mean()) / (a.std() + 1e-6)
    b = (b - b.mean()) / (b.std() + 1e-6)
    return float((a * b).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", required=True, help="成品图（通常是 2x 出图）")
    ap.add_argument("--qr", required=True, help="源二维码图（素材库那张原图）")
    ap.add_argument("--side", type=int, required=True, help="卡面上二维码的逻辑边长 px")
    ap.add_argument("--x", type=int, required=True, help="二维码左上角逻辑 x")
    ap.add_argument("--y", type=int, required=True, help="二维码左上角逻辑 y")
    ap.add_argument("--scale", type=int, default=2, help="成品相对逻辑尺寸的倍率（默认 2）")
    ap.add_argument("--search", type=int, default=40, help="搜索半径（逻辑 px）")
    ap.add_argument("--min-corr", type=float, default=0.99, help="判合格阈值")
    a = ap.parse_args()

    card = np.array(Image.open(a.card).convert("L"), dtype=float)
    side = a.side * a.scale
    ref = np.array(
        Image.open(a.qr).convert("L").resize((side, side), Image.LANCZOS), dtype=float
    )

    def score(x: int, y: int) -> float:
        sub = card[y : y + side, x : x + side]
        if sub.shape != (side, side):
            return -1.0
        return corr(sub, ref)

    x0, y0 = a.x * a.scale, a.y * a.scale
    r = a.search * a.scale
    best = (-2.0, 0, 0)
    for dy in range(-r, r + 1, 8):          # 粗搜
        for dx in range(-r, r + 1, 8):
            c = score(x0 + dx, y0 + dy)
            if c > best[0]:
                best = (c, x0 + dx, y0 + dy)
    bx, by = best[1], best[2]
    for dy in range(-8, 9):                  # 精搜
        for dx in range(-8, 9):
            c = score(bx + dx, by + dy)
            if c > best[0]:
                best = (c, bx + dx, by + dy)

    c, x, y = best
    verdict = "OK" if c >= a.min_corr else ("WARN" if c >= 0.95 else "FAIL")
    print(f"图: {a.card}  二维码逻辑边长 {a.side}px（实际 {side}px）")
    print(f"最佳相关 {c:.4f} @ 逻辑({x / a.scale:.0f}, {y / a.scale:.0f})  偏移逻辑 "
          f"({(x - x0) / a.scale:+.0f}, {(y - y0) / a.scale:+.0f})")
    print(f"→ {verdict}（阈值 {a.min_corr}）")
    if verdict != "OK":
        print("  处理：重出该图并保证 (1) 二维码用源码原图 (2) 白底静区保留 "
              "(3) 不要在码上压任何文字；源图本身模糊就换更大尺寸的码")
    return 0 if verdict == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
