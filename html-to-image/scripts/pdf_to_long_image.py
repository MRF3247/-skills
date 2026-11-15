#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 每页渲染后纵向拼接成一张长图（原样拼接，不重设计）。

用法:
    env -u PYTHONPATH /usr/bin/python3 pdf_to_long_image.py <in.pdf> <out.png> [zoom]

⚠️ 本机必须清 PYTHONPATH 跑系统 python：terminal 全局 PYTHONPATH 指向 hermes
venv (py3.11 site-packages)，系统 /usr/bin/python3 (3.9) 加载其 PIL 会报
ImportError: cannot import name '_imaging'。venv 内 python3 的 PIL 同样坏。
"""
import sys
import fitz
from PIL import Image


def main(src: str, out: str, zoom: float = 2.5) -> None:
    doc = fitz.open(src)
    imgs = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))  # ~180 DPI @2.5
        imgs.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    w = max(im.width for im in imgs)
    h = sum(im.height for im in imgs)
    canvas = Image.new("RGB", (w, h), "white")
    y = 0
    for im in imgs:
        canvas.paste(im, (0, y))
        y += im.height
    canvas.save(out, "PNG")
    print(f"OK -> {out}  {w}x{h}px, {len(doc)}页")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 2.5)
