#!/usr/bin/env python3
"""教材/电子书封面去营销区 + 可选横拼。

封面页（PDF 第 1 页 / 03_宣传图/p001.png）底部常带「二维码 + 加客服文案 +
ag.scilink.link」营销区，用户要「单纯放封面」「拼图别带二维码和链接」时必须切掉。
做法不写死 y 值，按墨迹行分段自动定位：

  分段 = 连续的有墨迹行。典型封面的段序：系列名 / 大标题 / 副标题 / 英文 /
  蓝线 / 简介行… / [数据栏] / 分隔线(细且宽) / 营销区(二维码+链接)

  营销区 = 最后一个段；分隔线 = 倒数第二个段（高 <=6px 且宽 > 0.7W）
  cut = min(分隔线上沿 - 25, 倒数第三个段底 + 60)   # 去掉营销区与模板横线，又不留大片空白

注意：数据栏（如「5 篇 / 15 章 / 86 节 / 9 幅图解」）不是营销区，保留。
书的模板不完全一样：有的封面有数据栏、有的是副题多一行，所以裁后高度
本来就不同——横拼时按宽度归一、顶部对齐、白底补足，不要纵向拉伸。

用法::

  # 单本：裁成纯封面
  python3 trim_cover_marketing.py --pdf "成书.pdf" --out cover.png

  # 多本：裁完直接横拼（等宽卡片、顶部对齐）
  python3 trim_cover_marketing.py --pdf a.pdf --pdf b.pdf --pdf c.pdf \
      --stitch out.png --card-w 900 --gap 14 --margin 28

PDF 渲染用 fitz（PyMuPDF）+ Pillow：走 terminal 的 python3 跑，
execute_code 沙箱里的解释器常常没有 fitz。
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

INK_THRESHOLD = 235   # 灰度低于它算墨迹
LINE_MAX_H = 6        # 分隔线段的最大高度（px@3x）
LINE_MIN_W = 0.7      # 分隔线至少要占页宽的比例


def load_page(path: Path, dpi_scale: float = 3.0) -> Image.Image:
    """PDF 取第 1 页按 dpi_scale 渲染；图片直接打开。"""
    if path.suffix.lower() == '.pdf':
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(dpi_scale, dpi_scale))
        return Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    return Image.open(path).convert('RGB')


def segments(img: Image.Image):
    """返回 (segs, rows)：segs 是连续有墨迹的行区间列表 [(y0,y1), …]。"""
    a = np.array(img.convert('RGB'))
    ink = a.mean(2) < INK_THRESHOLD
    rows = ink.sum(1)
    segs, start = [], None
    for y in range(a.shape[0]):
        if rows[y] > 0:
            if start is None:
                start = y
        elif start is not None:
            segs.append((start, y - 1))
            start = None
    if start is not None:
        segs.append((start, a.shape[0] - 1))
    return segs, rows


def cut_y(img: Image.Image, verbose: bool = True) -> int:
    """算出去掉营销区后的裁切高度。"""
    segs, rows = segments(img)
    if len(segs) < 3:
        if verbose:
            print('  ! 墨迹段不足 3 个，整页保留', file=sys.stderr)
        return img.height
    W = img.width
    last_start = segs[-1][0]
    line = segs[-2]
    is_line = (line[1] - line[0] + 1) <= LINE_MAX_H and rows[line[0]:line[1] + 1].max() > W * LINE_MIN_W
    if is_line:
        cut = min(line[0] - 25, segs[-3][1] + 60)
    else:
        # 没有分隔线：退回到「营销区上一块内容底 + 60」
        cut = segs[-2][1] + 60
    cut = max(1, min(cut, img.height))
    if verbose:
        print(f'  segs tail={segs[-3:]}  line={is_line}  cut={cut}/{img.height}')
    return cut


def main():
    ap = argparse.ArgumentParser(description='封面去营销区 + 可选横拼')
    ap.add_argument('--pdf', '--png', dest='srcs', action='append', required=True,
                    help='封面源文件（PDF 取第 1 页，或直接给 png）')
    ap.add_argument('--out', help='单张输出路径；配 --stitch 时可省略')
    ap.add_argument('--stitch', help='横拼成品输出路径')
    ap.add_argument('--card-w', type=int, default=900, help='横拼时每张卡片的宽度')
    ap.add_argument('--gap', type=int, default=14, help='卡片间距')
    ap.add_argument('--margin', type=int, default=28, help='四周留白')
    ap.add_argument('--scale', type=float, default=3.0, help='PDF 渲染倍率')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args()

    plates = []
    for src in args.srcs:
        p = Path(src).expanduser()
        img = load_page(p, args.scale)
        cut = cut_y(img, verbose=not args.quiet)
        cropped = img.crop((0, 0, img.width, cut))
        print(f'{p.name}: {img.size} -> {cropped.size}')
        plates.append(cropped)

    if args.out and not args.stitch:
        if len(plates) != 1:
            ap.error('多张输入请用 --stitch 指定横拼成品')
        Path(args.out).expanduser().parent.mkdir(parents=True, exist_ok=True)
        plates[0].save(Path(args.out).expanduser())
        print('saved', args.out)
        return

    scaled = [c.resize((args.card_w, round(c.height * args.card_w / c.width)), Image.LANCZOS)
              for c in plates]
    card_h = max(s.height for s in scaled)
    total_w = args.margin * 2 + args.card_w * len(scaled) + args.gap * (len(scaled) - 1)
    total_h = args.margin * 2 + card_h
    canvas = Image.new('RGB', (total_w, total_h), 'white')
    x = args.margin
    for s in scaled:                      # 顶部对齐，余下白底补足（都是白底封面，接缝看不出）
        canvas.paste(s, (x, args.margin))
        x += args.card_w + args.gap
    dest = Path(args.stitch or args.out).expanduser()
    dest.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(dest)
    print(f'saved {dest}  canvas={canvas.size}  card_h={card_h}')


if __name__ == '__main__':
    main()
