#!/usr/bin/env python3
"""在实拍照片/截图上压中文大字文案：淡黄字 + 白色细描边 + 黑色硬阴影 + 斜体。

用法：
    python3 add_snap_text.py in.jpg out.jpg "文案" \
        --pos bottom|top|right|left|center --size-ratio 0.05 --wrap 12 \
        [--font /Users/Jin/Library/Fonts/MiSans-Heavy.ttf] [--color FFF3B0] [--skew 12]

设计口径（用户 2026-11）：淡黄色、很粗的简体中文、白色细描边、黑色硬阴影（不模糊）、斜体、
字号不要大（默认 5% 画宽，宁小不大），多行以短行换行。
"""
import argparse
import math
from PIL import Image, ImageDraw, ImageFont

FONT_DEFAULT = "/Users/Jin/Library/Fonts/MiSans-Heavy.ttf"


def wrap(text, font, max_chars):
    """按标点断句后贪心装箱：不拆词、不让标点落在行首，行宽尽量接近"""
    import re as _re
    # 支持手动换行：文案里写 \n 就在那里断（不想出现标点但要求特定断行时用）
    out = []
    for para in text.split("\n"):
        out.extend(_wrap_one(para, max_chars))
    return out


def _wrap_one(text, max_chars):
    import re as _re
    clauses = [c for c in _re.split(r"(?<=[，。、；：！？])", text) if c]
    lines, cur = [], ""
    for c in clauses:
        if len(c) > max_chars:                       # 单句超长才硬切
            if cur:
                lines.append(cur); cur = ""
            while len(c) > max_chars:
                lines.append(c[:max_chars]); c = c[max_chars:]
            cur = c
            continue
        if len(cur) + len(c) <= max_chars:
            cur += c
        else:
            if cur:
                lines.append(cur)
            cur = c
    if cur:
        lines.append(cur)
    return [x for x in lines if x]


def draw_text_layer(size, lines, font, color, stroke_w, shadow_off, line_gap, skew_deg=12,
                    stroke_color=(255, 255, 255, 255), shadow_color=(0, 0, 0, 210)):
    """先画在透明层上（含斜体），再返回图层"""
    tmp = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    y = 0
    for ln in lines:
        w = d.textlength(ln, font=font)
        x = (size[0] - w) / 2
        # 硬阴影（无模糊）
        d.text((x + shadow_off, y + shadow_off), ln, font=font,
               fill=shadow_color, stroke_width=stroke_w, stroke_fill=shadow_color)
        # 描边 + 填充
        d.text((x, y), ln, font=font, fill=color,
               stroke_width=stroke_w, stroke_fill=stroke_color)
        y += font.size + line_gap
    if abs(skew_deg) > 0.1:
        k = math.tan(math.radians(skew_deg))
        tmp = tmp.transform(size, Image.AFFINE, (1, k, -k * size[1] / 2, 0, 1, 0),
                            resample=Image.BICUBIC)
    return tmp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("text")
    ap.add_argument("--pos", default="bottom", choices=["bottom", "top", "center", "right", "left"])
    ap.add_argument("--size-ratio", type=float, default=0.05, help="字号 = 画宽 × 该比例")
    ap.add_argument("--wrap", type=int, default=14, help="每行字数上限")
    ap.add_argument("--font", default=FONT_DEFAULT)
    ap.add_argument("--color", default="FFE066", help="淡黄色（十六进制，默认 FFE066；FFF3B0 太浅会被看成白色）")
    ap.add_argument("--skew", type=float, default=14.0, help="斜体角度（度，越大越斜）")
    ap.add_argument("--margin", type=float, default=0.045, help="边距比例")
    ap.add_argument("--stroke-color", default="000000", help="描边颜色（十六进制）；默认黑色")
    ap.add_argument("--stroke-px", type=float, default=2.0,
                    help="描边粗细，按 1080 宽参考算的 px（如 2 = 宽 1080 时 2px）")
    ap.add_argument("--shadow-color", default="FFFFFF", help="阴影颜色（十六进制）；默认白色")
    ap.add_argument("--shadow-ratio", type=float, default=0.10, help="阴影位移 = 字高 × 该比例")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    W, H = im.size
    font = ImageFont.truetype(a.font, max(18, int(W * a.size_ratio)))
    stroke_w = max(1, int(round(a.stroke_px * W / 1080)))          # 2px@1080 参考
    shadow_off = max(3, int(font.size * a.shadow_ratio))           # 硬阴影位移
    line_gap = int(font.size * 0.30)

    lines = wrap(a.text, font, a.wrap)
    layer_w = W
    layer_h = int(len(lines) * font.size + (len(lines) - 1) * line_gap + font.size * 0.6)
    def _rgba(h, alpha=255):
        h = h.lstrip("#")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)

    layer = draw_text_layer((layer_w, layer_h), lines, font, _rgba(a.color), stroke_w, shadow_off,
                            line_gap, a.skew,
                            stroke_color=_rgba(a.stroke_color), shadow_color=_rgba(a.shadow_color))

    # 斜体 transform 会让字块整体偏移，按实际墨迹包围盒重新居中
    bbox = layer.getbbox()
    if not bbox:
        raise SystemExit("文字层为空")
    lw, lh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    layer = layer.crop(bbox)
    mx, my = int(W * a.margin), int(H * a.margin)
    if a.pos == "bottom":
        pos = ((W - lw) // 2, H - my - lh)
    elif a.pos == "top":
        pos = ((W - lw) // 2, my)
    elif a.pos == "center":
        pos = ((W - lw) // 2, (H - lh) // 2)
    elif a.pos == "right":
        pos = (W - mx - lw, (H - lh) // 2)
    else:
        pos = (mx, (H - lh) // 2)

    im = im.convert("RGBA")
    im.alpha_composite(layer, pos)
    im.convert("RGB").save(a.out, quality=94)
    print(f"saved {a.out} {W}x{H} | lines={len(lines)} size={font.size} pos={a.pos}")


if __name__ == "__main__":
    main()
