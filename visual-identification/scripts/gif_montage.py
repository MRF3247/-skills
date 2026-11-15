#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 GIF/视频抽帧拼成一张横向长图（每格标「序号 (f帧号)」），一次调用看完整条动作时间轴。

用法（需有 PIL 的解释器；本机默认 python3 无 PIL）:
  /Users/Jin/Documents/Hermes/venvs/huashu/bin/python3 gif_montage.py <gif> <out.png> [最多格数=6] [格高=220]

配合 `vision_analyze` 使用：它一次只吃一张图，把整条时间轴拼成一张就能一次看完。
⚠️ 超宽长图会被视觉工具大幅缩小（提示里的 downscaled 倍率），宽过 ~3000px 细节就丢了：
   长 GIF 拆成 8~10 格/张、必要时分 2~3 张；短 GIF（≤10 帧）全抽。
"""
import sys
from PIL import Image, ImageSequence, ImageDraw


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    gif, out = sys.argv[1], sys.argv[2]
    maxn = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    H = int(sys.argv[4]) if len(sys.argv) > 4 else 220

    frames = [f.convert("RGB") for f in ImageSequence.Iterator(Image.open(gif))]
    n = len(frames)
    if n >= maxn:
        idx = sorted(set(round(i * (n - 1) / (maxn - 1)) for i in range(maxn)))
    else:
        idx = list(range(n))

    tiles = []
    for k, i in enumerate(idx):
        im = frames[i]
        w = max(1, int(im.width * H / im.height))
        im = im.resize((w, H), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        label = f"{k + 1} (f{i})"
        d.rectangle([0, 0, 8 + 7 * len(label), 16], fill=(0, 0, 0))
        d.text((3, 3), label, fill=(255, 255, 0))
        tiles.append(im)

    gap = 6
    W = sum(t.width for t in tiles) + gap * (len(tiles) - 1)
    canvas = Image.new("RGB", (W, H), (30, 30, 30))
    x = 0
    for t in tiles:
        canvas.paste(t, (x, 0))
        x += t.width + gap
    canvas.save(out)
    print(f"{gif} 共 {n} 帧 → 取 {len(idx)} 帧 → {out}  ({canvas.size})")
    if W > 3000:
        print("⚠️ 宽过 3000px，视觉工具会大幅缩小——建议减少格数或分张")
    return 0


if __name__ == "__main__":
    sys.exit(main())
