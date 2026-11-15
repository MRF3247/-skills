#!/usr/bin/env python3
"""在已有成品图上压小红书封面文案 —— 亮黄字 / 黑描边 / 白阴影 / 伪斜体

适用：手里已经是一张排好的图（教材截图拼图、课程资料页、实拍照片），用户要「做成封面，
正中写上文案」。不要为这个重走 HTML 排版，也不要丢给生图引擎（它会把已有的图重画掉）。

用法：
    python3 cover_caption.py 底图.png 输出.png "文献检索+文献阅读技巧" "全套教程"

可选参数：
    --s1 / --s2   两行字号（px）。缺省按画布宽度反算：行 1 占宽 85%，行 2 上限 2.4 倍
    --color       字色，缺省 255,214,0（亮黄 #FFD600）
    --stroke      黑描边宽度，缺省 10
    --shear       倾斜系数 = tan(角度)，缺省 0.20 ≈ 11°
    --veil        底图白蒙版浓度 0~1，缺省 0.10（把背景密集小字压下去）
    --shadow-blur 阴影模糊半径，缺省 8（柔影）；**用户说「硬阴影 / 不要过度 / 不透明」时传 0**
    --font        字体路径；缺省自动挑本机最粗的中文字体
    --single      只画一行

白影放白底上天生对比弱：盖住底下密集小字时看得见，落在纯白空白处几乎融合。这是物理事实，
不要去换成深色阴影「救」——用户指定白影就照做，交付时说清这一点，并把三个加强选项
（加大偏移 / 四周满包围 / 压低底图）一次给出来让他挑，不要自己拿主意。

依赖：Pillow。无其它依赖。
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# 本机可用的粗中文字体，按粗细降序。STHeiti Medium.ttc 需要 index=1 才是简体。
FONT_CANDIDATES = [
    ("/Users/Jin/Library/Fonts/AlibabaPuHuiTi-3-115-Black.otf", 0),
    ("/Users/Jin/Library/Fonts/AlibabaPuHuiTi-3-105-Heavy.otf", 0),
    ("/Users/Jin/Library/Fonts/AlibabaPuHuiTi-3-85-Bold.otf", 0),
    ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
    ("/System/Library/Fonts/Songti.ttc", 0),
]

SHADOW_OFF = (6, 9)
SHADOW_BLUR = 8      # 默认柔影；--shadow-blur 0 得纯白不透明硬影


def pick_font(explicit=None):
    if explicit:
        return explicit, 0
    for path, idx in FONT_CANDIDATES:
        if os.path.exists(path):
            return path, idx
    raise SystemExit("找不到可用的粗中文字体，用 --font 指定")


def width_units(text):
    """以「一个全角字 = 1」计的粗略宽度；半角约 0.5"""
    return sum(0.5 if ord(c) < 128 else 1.0 for c in text)


def render_line(text, size, font_path, font_index, color, stroke, shear):
    """渲染单行（含黑描边），做剪切变换模拟斜体，返回裁边后的透明图层"""
    font = ImageFont.truetype(font_path, size, index=font_index)
    bbox = font.getbbox(text, stroke_width=stroke)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = stroke + 20
    # 画布要留出倾斜后的横向位移：宽 = 字宽 + 字高×k
    w = tw + pad * 2 + int(th * abs(shear)) + 40
    h = th + pad * 2

    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(
        (pad - bbox[0], pad - bbox[1]), text, font=font,
        fill=color, stroke_width=stroke, stroke_fill=(0, 0, 0),
    )
    # x' = x + k*y —— 水平剪切。中文字体没有真斜体，这是唯一可靠的造法。
    layer = layer.transform((w, h), Image.AFFINE, (1, shear, 0, 0, 1, 0),
                            resample=Image.BICUBIC)
    return layer.crop(layer.getbbox())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("text1")
    ap.add_argument("text2", nargs="?", default=None)
    ap.add_argument("--s1", type=int, default=0)
    ap.add_argument("--s2", type=int, default=0)
    ap.add_argument("--color", default="255,214,0")
    ap.add_argument("--stroke", type=int, default=10)
    ap.add_argument("--shear", type=float, default=0.20)
    ap.add_argument("--veil", type=float, default=0.10)
    ap.add_argument("--shadow-blur", type=float, default=SHADOW_BLUR,
                    help="0 = 硬阴影（纯白不透明、无羽化）；用户说“不要过度”就传 0")
    ap.add_argument("--font", default=None)
    ap.add_argument("--gap", type=int, default=46)
    args = ap.parse_args()

    color = tuple(int(x) for x in args.color.split(","))
    font_path, font_index = pick_font(args.font)

    img = Image.open(args.src).convert("RGB")
    W, H = img.size
    if args.veil > 0:
        img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), args.veil)

    texts = [args.text1] + ([args.text2] if args.text2 else [])
    # 字号反算：中文字宽 ≈ 字号，所以「占满 X% 宽」= X*W/字数单位
    s1 = args.s1 or max(28, int(W * 0.85 / width_units(texts[0])))
    sizes = [s1]
    if len(texts) > 1:
        s2 = args.s2 or min(int(W * 0.72 / width_units(texts[1])), int(s1 * 2.4))
        sizes.append(s2)

    layers = [render_line(t, s, font_path, font_index, color, args.stroke, args.shear)
              for t, s in zip(texts, sizes)]

    block_h = sum(l.height for l in layers) + args.gap * (len(layers) - 1)
    top = (H - block_h) // 2

    # 左右补偿按「行宽」而不是字号：倾斜后近满宽的长行墨迹重心偏右，
    # 几何居中看起来偏左；短行本身窄，只需极小补偿。两行用同一个值必偏。
    def xoff(layer):
        return 10 if layer.width > 0.70 * W else 2

    ys, y = [], top
    for l in layers:
        ys.append(y)
        y += l.height + args.gap

    # 白阴影单独一层：先合成所有阴影、模糊，再叠主体 —— 直接在主体描边上做阴影会糊成脏边
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for lay, yy in zip(layers, ys):
        white = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        white.paste((255, 255, 255, 255), (0, 0), lay)
        shadow.alpha_composite(
            white, ((W - lay.width) // 2 + xoff(lay) + SHADOW_OFF[0], yy + SHADOW_OFF[1]))
    if args.shadow_blur > 0:
        shadow = shadow.filter(ImageFilter.GaussianBlur(args.shadow_blur))

    out = Image.alpha_composite(img.convert("RGBA"), shadow)
    for lay, yy in zip(layers, ys):
        out.alpha_composite(lay, ((W - lay.width) // 2 + xoff(lay), yy))

    out.convert("RGB").save(args.out, quality=95)
    print(f"OK {args.out}  {W}x{H}")
    for t, lay, s in zip(texts, layers, sizes):
        print(f"   size={s:>3}  layer={lay.size}  {t}")


if __name__ == "__main__":
    main()
