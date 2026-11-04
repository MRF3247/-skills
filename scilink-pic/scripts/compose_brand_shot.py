#!/usr/bin/env python3
"""新增图文风格：来源页截图 / 关键结果截图 + 品牌包装（logo + 中文标题/译文）。

版式（固定 1080×1440）：
  [logo 540×63 @ (270,26)]
  [英文标题（从原文取，可省略）]
  [中文标题（英文标题下面）]
  [截图：顶部留白，不压 logo]
  [中文译文面板（可选，放在高亮段下方）]

用法：
  python3 compose_brand_shot.py --shot p2_crop.png --out p2_brand.png \
      --en-title "..." --cn-title "..." [--cn-body "..."] [--source "PubMed · The Lancet · PMID …"]
"""
import argparse
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
X0, X1 = 44, 1036
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONTS = [
    ("/Users/Jin/Library/Fonts/MiSans-Heavy.ttf", 0),
    ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
]
BRAND = (46, 107, 230)
INK = (26, 36, 48)
MUTED = (110, 122, 138)
PANEL = (242, 246, 255)


def font(size):
    for p, i in FONTS:
        try:
            return ImageFont.truetype(p, size, index=i)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_cn(text, f, max_w, d):
    """中文按字断、英文按词断（避免把 repair 拆成 re/pair）"""
    if " " in text and sum(c.isascii() for c in text) > len(text) * 0.5:
        lines, cur = [], ""
        for w in text.split():
            trial = (cur + " " + w).strip()
            if d.textlength(trial, font=f) > max_w and cur:
                lines.append(cur); cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=f) > max_w and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--en-title", default="")
    ap.add_argument("--cn-title", default="")
    ap.add_argument("--cn-body", default="", help="高亮段的中文译文")
    ap.add_argument("--source", default="", help="底部来源行（期刊/PMID）")
    ap.add_argument("--shot-top-gap", type=int, default=26, help="截图上方留白（不压 logo/标题）")
    ap.add_argument("--max-upscale", type=float, default=1.6, help="截图最多放大倍数（填满版面用）")
    a = ap.parse_args()

    canvas = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(canvas)
    logo = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
    canvas.paste(logo, (270, 26), logo)

    y = 118
    max_w = X1 - X0
    if a.en_title:
        f = font(25)
        for ln in wrap_cn(a.en_title, f, max_w, d):
            d.text((X0, y), ln, font=f, fill=MUTED)
            y += 34
        y += 8
    if a.cn_title:
        f = font(31)
        for ln in wrap_cn(a.cn_title, f, max_w, d):
            d.text((X0, y), ln, font=f, fill=BRAND)
            y += 43
    if a.en_title or a.cn_title:
        d.line([(X0, y + 4), (X1, y + 4)], fill=(226, 232, 240), width=2)
        y += 4 + a.shot_top_gap
    else:
        y += a.shot_top_gap

    shot = Image.open(a.shot).convert("RGB")
    body_h = 0
    if a.cn_body:
        fb = font(23)
        body_lines = wrap_cn(a.cn_body, fb, max_w - 56, d)
        body_h = 58 + len(body_lines) * 34 + 22
    avail_h = H - y - 36 - body_h
    scale = min(a.max_upscale, avail_h / shot.height)   # 允许适度放大以填满版面（不留大片空白）
    shot_h = int(shot.height * scale)
    if shot_h > avail_h:
        shot_h = avail_h
    shot = shot.resize((max_w, shot_h), Image.LANCZOS)
    # 竖向居中剩余空间，避免底部大片空白
    slack = max(0, H - 36 - body_h - (y + shot_h))
    canvas.paste(shot, (X0, y + slack // 2))
    y += shot_h + slack // 2 + 12

    if a.cn_body:
        panel = Image.new("RGB", (max_w, body_h), PANEL)
        pd = ImageDraw.Draw(panel)
        pd.rectangle([0, 0, 10, body_h], fill=BRAND)
        fl = font(19)
        pd.text((30, 16), "高亮段 · 中文译文", font=fl, fill=BRAND)
        fb = font(23)
        ty = 46
        for ln in wrap_cn(a.cn_body, fb, max_w - 56, pd):
            pd.text((30, ty), ln, font=fb, fill=INK)
            ty += 34
        canvas.paste(panel, (X0, y))
        y += body_h

    if a.source:
        d.line([(X0, H - 52), (X1, H - 52)], fill=(226, 232, 240), width=2)
        fs = font(20)
        d.text((X0, H - 40), a.source, font=fs, fill=(90, 102, 118))

    canvas.save(a.out)
    print(f"saved {a.out}  {W}x{H}")


if __name__ == "__main__":
    main()
