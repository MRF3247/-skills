#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把指定帧的主体区域裁出来放大，专供重问视觉模型用（读法冲突时的定案手段）。

用法:
  python3 zoom_crop.py <帧png...> [--box L,T,R,B 比例] [--scale 3] [--outdir .]
例:
  python3 zoom_crop.py a_1.png a_3.png a_6.png            # 默认裁 5%-95%
  python3 zoom_crop.py b_5.png --box 0.2,0.1,0.85,0.75     # 只裁头部区域

为什么必须放大后再问:
  半尺寸/整帧预览会让模型读错细节（五角星读错、动作读成「没动」）。
  主体区域裁出 + 3x LANCZOS 后，多帧塞进同一条消息按时间顺序问，
  并**要求模型给出判断依据**（肚子朝哪 / 有没有手指 / 能看到几种毛色 /
  皮肤是否有毛孔与发际粘贴感）——多数一次定案；仍定不了就写中性动作名。

裁剪框怎么定: 先问模型「主体在画面哪个位置、约占宽高各百分之几」，
  换算成比例再填 --box。
依赖 PIL（用带 PIL 的 venv，如 huashu venv 的 python3）。
"""
import os
import sys
from PIL import Image

argv = sys.argv[1:]
if not argv:
    print(__doc__)
    sys.exit(1)

box = (0.05, 0.05, 0.95, 0.95)
scale = 3
outdir = "."
paths = []
i = 0
while i < len(argv):
    a = argv[i]
    if a == "--box":
        box = tuple(float(x) for x in argv[i + 1].split(","))
        i += 2
    elif a == "--scale":
        scale = float(argv[i + 1])
        scale = int(scale) if scale == int(scale) else scale
        i += 2
    elif a == "--outdir":
        outdir = argv[i + 1]
        i += 2
    else:
        paths.append(a)
        i += 1

if len(box) != 4:
    print("--box 需要 4 个比例值: L,T,R,B")
    sys.exit(1)

for p in paths:
    im = Image.open(p).convert("RGB")
    w, h = im.size
    l, t, r, b = box
    c = im.crop((int(w * l), int(h * t), int(w * r), int(h * b)))
    new_size = (int(c.width * scale), int(c.height * scale))
    c = c.resize(new_size, Image.LANCZOS)
    out = os.path.join(outdir, f"zoom_{os.path.basename(p)}")
    c.save(out)
    print(f"{p} (原 {w}x{h}) -> {out} ({c.width}x{c.height})")
