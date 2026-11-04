#!/usr/bin/env python3
"""从整页截图里按「黄色高亮包围盒」重新构图 P3，保证重点段完整入画。

用途：P3 的关键段（如 PubMed 的 Findings）很长，固定 3:4 窗口容易把头尾切掉。
做法：整页截图（已打黄条）→ 找黄色像素包围盒 → 带边距裁出 → 缩放居中放到 1080×1440 → 顶部加题录带。

用法：
    python3 crop_highlight.py /tmp/shots/xxx-full.png /tmp/shots/xxx-p3.png \
        --masthead "PubMed · The Lancet · 2026-10-26 · PMID 42933458 · KEYNOTE-C93"
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W_OUT, H_OUT = 1080, 1440
BAND = 52

FONT_CANDIDATES = (
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    ("/System/Library/Fonts/Supplemental/Songti.ttc", 0),
)


def load_font(size=22):
    for path, idx in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size, index=idx)
        except Exception:
            continue
    return ImageFont.load_default()


def highlight_box(im: Image.Image):
    """返回黄色高亮像素的包围盒；没有高亮返回 None。"""
    a = np.asarray(im.convert("RGB")).astype(np.int16)
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mask = (r > 200) & (g > 170) & (b < 170) & (r + g - 2 * b > 90)
    if mask.sum() < 500:                       # 高亮太少，当失败
        return None
    ys, xs = np.where(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def build(im, box, mode="context", pad=0.03):
    """返回 3:4 裁切结果（未缩放）。
    context：以高亮段为锚，带上下上下文填满 3:4 窗口（默认，看起来像真实页面截图）
    tight：只留高亮段本身（信息最纯，但大片留白）
    """
    x0, y0, x1, y1 = box
    hh = y1 - y0
    cw = (x1 - x0)
    col_w = int(cw * (1 + pad * 2))
    col_x = max(0, x0 - int(cw * pad))

    if mode == "tight":
        pad_y = int(hh * 0.012)
        return im.crop((col_x, max(0, y0 - pad_y), col_x + col_w, min(im.height, y1 + pad_y)))

    # context：3:4 窗口，高亮段最多占 ~72% 高，其余是上下文
    win_h = int(col_w * 4 / 3)
    if hh > win_h * 0.72:
        k = (win_h * 0.72) / hh
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        x0, y0, x1, y1 = (int(v * k) for v in box)
        hh = y1 - y0
        cw = x1 - x0
        col_w = int(cw * (1 + pad * 2))
        col_x = max(0, x0 - int(cw * pad))
        win_h = int(col_w * 4 / 3)
    top = int(y0 - (win_h - hh) * 0.35)
    top = max(0, min(top, im.height - win_h))
    return im.crop((col_x, top, col_x + col_w, top + win_h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--masthead", default="")
    ap.add_argument("--mode", choices=["context", "tight"], default="context")
    ap.add_argument("--pad", type=float, default=0.03)
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    box = highlight_box(im)
    if not box:
        raise SystemExit("未检测到黄色高亮，先在截图时打上 mark（--mark-mode para）")
    crop = build(im, box, a.mode, a.pad)

    avail_w, avail_h = W_OUT, H_OUT - BAND - 8
    scale = min(avail_w / crop.width, avail_h / crop.height)
    crop = crop.resize((max(1, int(crop.width * scale)), max(1, int(crop.height * scale))), Image.LANCZOS)

    canvas = Image.new("RGB", (W_OUT, H_OUT), "white")
    canvas.paste(crop, ((W_OUT - crop.width) // 2, BAND + 6))

    d = ImageDraw.Draw(canvas)
    if a.masthead:
        d.text((30, 14), a.masthead, fill=(130, 130, 130), font=load_font())
    canvas.save(a.out)
    print(f"saved {a.out} {canvas.size[0]}x{canvas.size[1]} | mode={a.mode} | highlight box={box}")


if __name__ == "__main__":
    main()
