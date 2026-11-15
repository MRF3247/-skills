"""把教材 PDF 页面拼成 3:4 小红书资料图（每张 4 页 2×2）。

用法：
    python textbook_screens.py <全书.pdf> [输出目录] 3,5,9,13 16,17,28,31 ...

每个位置参数是一组，逗号分隔的页码（1-indexed），每组出一张图。
依赖：pymupdf, Pillow。输出 1080×1440。

选页原则：只挑有章节大标题或插图的页，宁可跳章节也不要连续四页纯文字。
"""
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter

PDF = sys.argv[1]
GROUP_ARGS = [a for a in sys.argv[2:] if "," in a]
OUT = Path(next((a for a in sys.argv[2:] if "," not in a), str(Path(PDF).parent / "教材截图")))
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1080, 1440
GAP = 16
PAD_X, PAD_Y = 51, 32
PW = (W - 2 * PAD_X - GAP) // 2          # 481
PH = int(PW * 1.4142)                     # 680，A4 比例
BG = (247, 248, 250)
BORDER = (223, 227, 232)

doc = pymupdf.open(PDF)


def render(page_no, w, h):
    """200dpi 渲染再降采样，比直接低 dpi 清楚得多。"""
    pix = doc[page_no - 1].get_pixmap(dpi=200)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return im.resize((w, h), Image.LANCZOS)


for gi, group in enumerate(GROUP_ARGS, 1):
    pages = [int(x) for x in group.split(",")]
    if len(pages) != 4:
        print(f"跳过 {group}：需要正好 4 页，给了 {len(pages)} 页")
        continue

    canvas = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(canvas)

    for idx, pno in enumerate(pages):
        r, c = divmod(idx, 2)
        x = PAD_X + c * (PW + GAP)
        y = PAD_Y + r * (PH + GAP)

        # 淡阴影：灰矩形 + 高斯模糊，垫在页面下方
        sh = Image.new("RGB", (PW + 12, PH + 12), BG)
        ImageDraw.Draw(sh).rectangle([6, 6, PW + 5, PH + 5], fill=(196, 202, 210))
        canvas.paste(sh.filter(ImageFilter.GaussianBlur(5)), (x - 6, y - 4))

        canvas.paste(render(pno, PW, PH), (x, y))
        draw.rectangle([x, y, x + PW - 1, y + PH - 1], outline=BORDER, width=1)

    tag = "-".join(str(p) for p in pages)
    out = OUT / f"{gi:02d}_p{tag}.png"
    canvas.save(out, optimize=True)
    print(f"✓ {out}  {W}×{H}  {out.stat().st_size // 1024}KB")

print("\n出图后用 vision 复核：四页完整无裁切、间距与阴影一致、没有一页空白过多。")
