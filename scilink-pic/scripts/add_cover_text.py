#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在已叠好 PSD 的封面上加大字文案（MiSans-Heavy 纯白 + 高斯模糊灰阴影）。

用法: python add_cover_text.py in.png out.png "第一行/第二行" [--min-size 54]

换行规则（用户口径）：
  * 文案 ≤ 10 字（含空格）**一律单行**，不许为了「排版感」硬拆两行；
  * 传参里带 `/` 才分行，单行文案字号自适应到 ≤990px。
首行从 y=950 起，落在底部蓝渐变上。
"""
import argparse
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/Users/Jin/Library/Fonts/MiSans-Heavy.ttf"
MAXW = 990
TOP_Y = 950


def fit_size(lines, maxw, start=170, floor=54, step=2):
    size = start
    while size > floor:
        f = ImageFont.truetype(FONT, size)
        if max(f.getbbox(l)[2] - f.getbbox(l)[0] for l in lines) <= maxw:
            return size
        size -= step
    return floor


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("text")
    ap.add_argument("--min-size", type=int, default=54)
    ap.add_argument("--badge", default="", help='顶部居中专题标签，如 "ESMO2026专题"（画在 logo 下方 y≈112，字白底深蓝胶囊）')
    ap.add_argument("--subtitle", default="", help="副标题：画在主文案下方，字号默认主文案的 0.42 倍")
    ap.add_argument("--sub-size", type=int, default=0, help="副标题字号（0=自动 0.42×主字号）")
    a = ap.parse_args()
    lines = [s for s in a.text.split("/") if s.strip()]
    if not lines:
        raise SystemExit("文案为空")

    img = Image.open(a.src).convert("RGB")
    W, H = img.size

    # 专题标签：logo（y 26–89）下方居中，深蓝胶囊 + 白字。先画，再盖主文案
    if a.badge:
        bf = ImageFont.truetype(FONT, 34)
        bw = bf.getbbox(a.badge)[2] - bf.getbbox(a.badge)[0]
        pad_x, pad_y, by = 30, 13, 112
        x0, y0 = (W - bw) // 2 - pad_x, by
        x1, y1 = (W + bw) // 2 + pad_x, by + 34 + pad_y * 2
        d0 = ImageDraw.Draw(img)
        d0.rounded_rectangle([x0, y0, x1, y1], radius=(y1 - y0) // 2, fill=(18, 80, 161))
        d0.text(((W - bw) // 2, y0 + pad_y - 3), a.badge, font=bf, fill=(255, 255, 255))

    size = fit_size(lines, MAXW, floor=a.min_size)
    font = ImageFont.truetype(FONT, size)
    lh = int(size * 1.26)
    # 单行往下挪一行；两行及以上第一行留在 TOP_Y（用户 2026-10 口径）
    top = TOP_Y + lh if len(lines) == 1 else TOP_Y

    # 行表：主文案若干行 + 可选副标题（更小字号，紧随主文案下方）
    rows = [(l, font, lh) for l in lines]
    y = top
    for l, f, h in rows:
        y += h
    if a.subtitle:
        ssize = a.sub_size or max(40, int(size * 0.42))
        sfont = ImageFont.truetype(FONT, ssize)
        # 副标题过长时自动缩字号，直到整行 ≤ MAXW
        while ssize > 28 and (sfont.getbbox(a.subtitle)[2] - sfont.getbbox(a.subtitle)[0]) > MAXW:
            ssize -= 2
            sfont = ImageFont.truetype(FONT, ssize)
        rows.append((a.subtitle, sfont, int(ssize * 1.35)))

    sh = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sh)
    y = top
    for l, f, h in rows:
        w = f.getbbox(l)[2] - f.getbbox(l)[0]
        d.text(((W - w) // 2, y + 6), l, font=f, fill=255)
        y += h
    sh = sh.filter(ImageFilter.GaussianBlur(6))
    gray = Image.new("RGB", (W, H), (40, 60, 90))
    img = Image.composite(gray, img, sh.point(lambda v: int(v * 0.45)))

    d = ImageDraw.Draw(img)
    y = top
    for l, f, h in rows:
        w = f.getbbox(l)[2] - f.getbbox(l)[0]
        d.text(((W - w) // 2, y), l, font=f, fill=(255, 255, 255))
        y += h
    img.save(a.dst)
    print(f"{a.dst} {W}x{H} size={size} lines={len(lines)} sub={'y' if a.subtitle else 'n'} bottom_y={y}")


if __name__ == "__main__":
    main()
