#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文档页整齐拼图（无设计感）：多页 PDF 或一组 PNG → 一张等大等距网格图。

跑法（本机必须清掉 PYTHONPATH，否则加载到 venv 里 3.11 编译的 PIL）：
  env -u PYTHONPATH /usr/bin/python3 doc_pages_grid.py --pdf a.pdf --pages 2-5 \
      --cols 2 --canvas 3:4 --trim --out out.png
  env -u PYTHONPATH /usr/bin/python3 doc_pages_grid.py --glob 'shots/*.png' \
      --cols 4 --canvas 3:4 --out grid.png

要点（踩过的坑都写在代码里）：
  * --canvas 3:4  固定 1080x1440；--canvas fit  画布高 = 网格高 + 2*margin（紧贴内容）
  * --single     只拼第 1 页并等比铺满画布（大纲版/框架版内容太少时用，比双页拼图饱满）
  * --ratio 0.68 强制卡片宽高比：批量出多张图时用它锁死版式，别让每批自己取中位数
  * --trim       裁掉纸张白边（只留 --pad 保护边），文字面积约放大 1.6 倍
  * 裁边后各页比例不一致时用“补白”对齐（不是缩小），否则内容少的页会明显偏小
  * 卡宽先按宽度算，再按高度反算取 min，否则多行会溢出画布
"""
import argparse
import glob as globmod

import numpy as np
from PIL import Image, ImageDraw

BG = (255, 255, 255)
BORDER = (230, 235, 242)


def trim_page(im, pad=10):
    """按非白像素包围盒裁掉页边距。"""
    g = np.array(im.convert("L"))
    mask = g < 246
    if not mask.any():
        return im
    rows, cols = np.where(mask.any(axis=1))[0], np.where(mask.any(axis=0))[0]
    box = (max(0, cols.min() - pad), max(0, rows.min() - pad),
           min(im.width, cols.max() + pad), min(im.height, rows.max() + pad))
    return im.crop(box)


def pad_to_ratio(im, ratio):
    """补白到统一宽高比（绝不缩小内容）。"""
    r = im.size[0] / im.size[1]
    if r > ratio:                       # 太宽 → 上下补
        h = int(round(im.size[0] / ratio))
        cv = Image.new("RGB", (im.size[0], h), BG)
        cv.paste(im, (0, (h - im.size[1]) // 2))
    elif r < ratio:                     # 太高 → 左右补
        w = int(round(im.size[1] * ratio))
        cv = Image.new("RGB", (w, im.size[1]), BG)
        cv.paste(im, ((w - im.size[0]) // 2, 0))
    else:
        return im
    return cv


def load_pages(args):
    if args.pdf:
        import fitz  # PyMuPDF
        doc = fitz.open(args.pdf)
        idx = list(range(len(doc)))
        if args.pages:
            a, _, b = args.pages.partition("-")
            idx = list(range(int(a) - 1, int(b) if b else int(a)))
        out = []
        for i in idx:
            pix = doc[i].get_pixmap(dpi=args.dpi)
            out.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
        return out
    paths = sorted(globmod.glob(args.glob))
    if args.limit:
        paths = paths[:args.limit]
    return [Image.open(p).convert("RGB") for p in paths]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf")
    ap.add_argument("--glob")
    ap.add_argument("--pages", help='PDF 页码范围（1 基），如 "2-5"')
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--canvas", choices=["3:4", "fit"], default="3:4")
    ap.add_argument("--trim", action="store_true")
    ap.add_argument("--single", action="store_true", help="只拼第 1 页并等比铺满画布")
    ap.add_argument("--ratio", type=float, default=0,
                    help="强制卡片宽高比（如 0.68）；批量出图时锁死版式用")
    ap.add_argument("--pad", type=int, default=10)
    ap.add_argument("--gap", type=int, default=14)
    ap.add_argument("--margin", type=int, default=20)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--card-w", type=int, default=240, help="--canvas fit 时每格卡宽")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    pages = load_pages(a)
    if a.trim:
        before = sum(p.size[0] * p.size[1] for p in pages)
        pages = [trim_page(p, a.pad) for p in pages]
        after = sum(p.size[0] * p.size[1] for p in pages)
        print(f"裁边：页面面积减少 {100 - 100 * after / before:.0f}%")

    # 统一比例：补白而非缩小，保证每格字号一致
    ratios = sorted(p.size[0] / p.size[1] for p in pages)
    ratio = a.ratio if a.ratio else ratios[len(ratios) // 2]
    if a.single:
        pages = pages[:1]
    pages = [pad_to_ratio(p, ratio) for p in pages]

    cols = 1 if a.single else a.cols
    rows = (len(pages) + cols - 1) // cols
    if a.canvas == "3:4":
        W, H = 1080, 1440
        if a.single:
            # 单页铺满：等比缩到画布内（不裁内容），居中
            cw = int(min(W - 2 * a.margin, (H - 2 * a.margin) * ratio))
            ch = int(round(cw / ratio))
            grid_h = ch
        else:
            cw_w = (W - 2 * a.margin - (cols - 1) * a.gap) // cols
            cw_h = int((H - 2 * a.margin - (rows - 1) * a.gap) / (rows / ratio))
            cw = min(cw_w, cw_h)
            ch = int(round(cw / ratio))
            grid_h = rows * ch + (rows - 1) * a.gap
            assert grid_h <= H - 2 * a.margin, f"网格高 {grid_h} 溢出画布"
    else:
        cw = a.card_w
        ch = int(round(cw / ratio))
        grid_h = rows * ch + (rows - 1) * a.gap
        grid_w = cols * cw + (cols - 1) * a.gap
        W, H = grid_w + 2 * a.margin, grid_h + 2 * a.margin

    cv = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(cv)
    x0 = (W - (cols * cw + (cols - 1) * a.gap)) // 2
    y0 = (H - (rows * ch + (rows - 1) * a.gap)) // 2
    for i, p in enumerate(pages):
        im = p.resize((cw, ch), Image.LANCZOS)
        x = x0 + (i % cols) * (cw + a.gap)
        y = y0 + (i // cols) * (ch + a.gap)
        cv.paste(im, (x, y))
        d.rectangle([x - 1, y - 1, x + cw, y + ch], outline=BORDER, width=1)
    cv.save(a.out)
    print(f"{a.out}  {len(pages)}页 {cols}列{rows}行 卡{cw}x{ch} "
          f"占高{grid_h / H:.0%} 画布{cv.size[0]}x{cv.size[1]}")


if __name__ == "__main__":
    main()
