#!/usr/bin/env python3
"""资料/教材页 → 多页拼图 + 中央两行压字（3:4 收藏向封面）。

用法：
  python3 collage_pages.py --pages p2.png,p3.png,p7.png,p54.png \
      --line1 "医学硕博都存一下" --line2 "全是干货" --out 封面.png

坐标与字号全部由画布宽度算，改页数不用改参数（超过 4 页自动多行）。

定稿压字形态（用户 2026-11 逐轮调到这一版，别再从头试）：
  pill（默认）  白字 + 品牌蓝**纯色**胶囊 + **无阴影**，大留白、细长比 ≈3.7
  outline       黄字 + 白色圆角粗描边 + 黑硬阴影（旧档，白底页面上描边会隐形，慎用）

关键实现口径：
  1) **用墨迹框定位**（font.getbbox 的 y0/y1），不要用行高/上行距定位——
     字体的行高留白会把胶囊上下撑胖约 0.3×字号，怎么调参数都「胖」。
  2) 字号由「胶囊宽 = 画宽 × --pill-width」反推，左右留白也跟着缩，不要手填字号。
  3) 圆角胶囊必须 4 倍超采样再 LANCZOS 缩回，否则弧边有锯齿。
"""
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_HEAVY = '/Users/Jin/Library/Fonts/SourceHanSansSC-Heavy.otf'   # 思源黑体 Heavy
FONT_COVER = '/Users/Jin/Library/Fonts/AlibabaPuHuiTi-3-115-Black.otf'
WHITE = (255, 255, 255, 255)
YELLOW = (255, 214, 10, 255)
BLACK = (0, 0, 0, 255)
BRAND_BLUE = (0, 110, 187, 255)      # #006EBB = assets/logo.png 像素均值（教材封面印的是 #006CB8，同色）


def text_width(probe, text, path, size):
    return probe.textlength(text, font=ImageFont.truetype(path, size))


def pill_layer(sheet, l1, l2, f1, f2, pad_x, pad_y, gapv, shadow):
    """白字 + 品牌蓝纯色胶囊。按墨迹框排版，胶囊自然收紧。"""
    W, H = sheet.size
    probe = ImageDraw.Draw(Image.new('L', (4, 4)))
    b1, b2 = f1.getbbox(l1), f2.getbbox(l2)
    ink1, ink2 = b1[3] - b1[1], b2[3] - b2[1]
    tw1, tw2 = probe.textlength(l1, font=f1), probe.textlength(l2, font=f2)

    pw = max(tw1, tw2) + 2 * pad_x
    ph = ink1 + gapv + ink2 + 2 * pad_y
    px0, py0 = (W - pw) / 2, (H - ph) / 2

    S = 4
    big = Image.new('L', (int(pw * S), int(ph * S)), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, big.width - 1, big.height - 1],
                                          radius=big.height / 2, fill=255)
    pill = Image.new('L', (W, H), 0)
    pill.paste(big.resize((int(pw), int(ph)), Image.LANCZOS), (int(px0), int(py0)))

    if shadow:                                  # 旧档才要阴影；定稿无阴影
        off = int(f1.size * 0.10)
        sh = Image.new('L', (W, H), 0)
        sh.paste(pill.crop((0, 0, W - off, H - off)), (off, off))
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        lay.paste(BLACK, (0, 0, W, H), sh)
        sheet = Image.alpha_composite(sheet, lay)

    blue = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    blue.paste(BRAND_BLUE, (0, 0, W, H), pill)
    sheet = Image.alpha_composite(sheet, blue)

    ink = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    top1 = py0 + pad_y
    top2 = top1 + ink1 + gapv
    d.text(((W - tw1) / 2, top1 - b1[1]), l1, font=f1, fill=WHITE)
    d.text(((W - tw2) / 2, top2 - b2[1]), l2, font=f2, fill=WHITE)
    return Image.alpha_composite(sheet, ink)


def outline_layer(sheet, l1, l2, f1, f2, asc1, asc2, gapv, y1, y2):
    """旧档：黄字 + 白色圆角粗描边 + 黑硬阴影（描边用 blur+阈值 做圆角）。"""
    W, H = sheet.size

    def mask(txt, f, top, sw):
        m = Image.new('L', (W, H), 0)
        md = ImageDraw.Draw(m)
        md.text(((W - md.textlength(txt, font=f)) / 2, top), txt, font=f, fill=255,
                stroke_width=sw, stroke_fill=255)
        return m.filter(ImageFilter.GaussianBlur(max(2, int(sw * 0.55)))).point(lambda v: 255 if v > 128 else 0)

    sw1, sw2 = int(f1.size * 0.095), int(f2.size * 0.095)
    m1, m2 = mask(l1, f1, y1, sw1), mask(l2, f2, y2, sw2)
    import numpy as np
    union = Image.fromarray(np.maximum(np.array(m1), np.array(m2)))

    off = int(f1.size * 0.06)
    sh = Image.new('L', (W, H), 0)
    sh.paste(union, (off, off))
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    lay.paste(BLACK, (0, 0, W, H), sh)
    sheet = Image.alpha_composite(sheet, lay)

    white = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    white.paste(WHITE, (0, 0, W, H), union)
    sheet = Image.alpha_composite(sheet, white)

    ink = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ink)
    for txt, f, top in ((l1, f1, y1), (l2, f2, y2)):
        d.text(((W - d.textlength(txt, font=f)) / 2, top), txt, font=f, fill=YELLOW)
    return Image.alpha_composite(sheet, ink)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True, help='逗号分隔的页面 PNG，按从左到右、从上到下')
    ap.add_argument('--line1', required=True)
    ap.add_argument('--line2', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--style', default='pill', choices=['pill', 'outline'])
    ap.add_argument('--gap', type=int, default=6, help='拼格缝隙 px（margin 要少就保持个位数）')
    ap.add_argument('--cols', type=int, default=2)
    ap.add_argument('--pill-width', type=float, default=0.94, help='胶囊宽占画宽比')
    ap.add_argument('--pad-x', type=float, default=1.30, help='左右留白 = 字号 × 该值')
    ap.add_argument('--pad-y', type=float, default=0.30, help='上下留白 = 字号 × 该值（越小越细长）')
    ap.add_argument('--l2-gap', type=float, default=0.14, help='两行间距 = 字号 × 该值')
    ap.add_argument('--l2-ratio', type=float, default=1.16, help='第二行字号倍数（字数少的那行更大）')
    ap.add_argument('--shadow', action='store_true', help='pill 档加黑色硬阴影（旧档，默认不加）')
    a = ap.parse_args()

    imgs = [Image.open(p).convert('RGB') for p in a.pages.split(',')]
    cols = a.cols
    rows = (len(imgs) + cols - 1) // cols
    cw, ch = max(i.width for i in imgs), max(i.height for i in imgs)
    W, H = cols * cw + (cols - 1) * a.gap, rows * ch + (rows - 1) * a.gap
    sheet = Image.new('RGB', (W, H), 'white')
    for k, im in enumerate(imgs):
        r, c = divmod(k, cols)
        if im.size != (cw, ch):                     # 宽度归一、顶部对齐，余下留白
            cell = Image.new('RGB', (cw, ch), 'white')
            s = cw / im.width
            cell.paste(im.resize((cw, max(1, int(im.height * s))), Image.LANCZOS), (0, 0))
            im = cell
        sheet.paste(im, (c * (cw + a.gap), r * (ch + a.gap)))
    sheet = sheet.convert('RGBA')

    probe = ImageDraw.Draw(Image.new('L', (4, 4)))
    path = FONT_HEAVY if a.style == 'pill' else FONT_COVER
    k = text_width(probe, a.line1, path, 100) / 100.0     # 每 1px 字号的文字宽度
    if a.style == 'pill':
        # 胶囊宽固定 = 画宽 × pill-width，字号与左右留白一起反推（手填字号会飘）
        f1s = int(W * a.pill_width / (k + 2 * a.pad_x))
    else:
        f1s = int(100 * (W * 0.80) / text_width(probe, a.line1, path, 100))
    f2s = int(f1s * a.l2_ratio)
    f1, f2 = ImageFont.truetype(path, f1s), ImageFont.truetype(path, f2s)

    b1, b2 = f1.getbbox(a.line1), f2.getbbox(a.line2)
    gapv = int(f1s * a.l2_gap)
    y1 = (H - ((b1[3] - b1[1]) + gapv + (b2[3] - b2[1]))) / 2      # 墨迹框定位
    y2 = y1 + (b1[3] - b1[1]) + gapv

    if a.style == 'pill':
        sheet = pill_layer(sheet, a.line1, a.line2, f1, f2,
                           int(f1s * a.pad_x), int(f1s * a.pad_y), gapv, a.shadow)
        probe2 = ImageDraw.Draw(Image.new('L', (4, 4)))
        pw = max(probe2.textlength(a.line1, font=f1), probe2.textlength(a.line2, font=f2)) + 2 * int(f1s * a.pad_x)
        ph = (b1[3] - b1[1]) + gapv + (b2[3] - b2[1]) + 2 * int(f1s * a.pad_y)
        print(f'pill {pw:.0f}x{ph:.0f}  细长比 {pw/ph:.2f}（目标 3.7–4.0；<3.2 就是胖）')
    else:
        sheet = outline_layer(sheet, a.line1, a.line2, f1, f2, b1[3], b2[3], gapv, y1, y2)

    sheet.convert('RGB').save(a.out, quality=96)
    print(f'{a.out}  {sheet.size}  ratio {sheet.width/sheet.height:.3f}  f1={f1s} f2={f2s} style={a.style}')


if __name__ == '__main__':
    main()
