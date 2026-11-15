#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐帧位移探针：算指定区域内暗像素质心的逐帧 x/y，判断有没有整体位移（摇头/点头/走位）。

用法（需有 PIL 的解释器；本机默认 python3 无 PIL/numpy）:
  /Users/Jin/Documents/Hermes/venvs/huashu/bin/python3 gif_motion_probe.py <gif> [暗阈值=110] [区域=x0,x1,y0,y1]
  区域用 0-1 比例，默认 0,1,0,0.6（全宽 + 上部 60%，适合看头部）

判读:
  - 数百 px 画面里极差 < 3px ≈ 无整体位移；几十 px 才是明显位移。
  - 只能证伪「大位移」，不能证明「绝对没动」；细微位移要靠裁切放大后让视觉模型逐帧比。
  - ❌ 不要改用「相邻帧差分」定位动作：GIF 抖色噪点让差异区铺满整帧，结论永远是「全身在动」。
  - 暗区在画面顶部被边框/深色背景占满时，换更小的裁切区域再跑，别用「暗区上沿」这类口径。
"""
import sys
from PIL import Image, ImageSequence


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    path = sys.argv[1]
    th = int(sys.argv[2]) if len(sys.argv) > 2 else 110
    if len(sys.argv) > 3:
        x0, x1, y0, y1 = [float(v) for v in sys.argv[3].split(",")]
    else:
        x0, x1, y0, y1 = 0.0, 1.0, 0.0, 0.6

    im = Image.open(path)
    W, H = im.size
    rows = []
    for i, fr in enumerate(ImageSequence.Iterator(im)):
        g = fr.convert("L")
        px = g.load()
        w, h = g.size
        xa, xb = int(w * x0), int(w * x1)
        ya, yb = int(h * y0), int(h * y1)
        sx = sy = cnt = 0
        for y in range(ya, yb):
            for x in range(xa, xb):
                if px[x, y] < th:
                    sx += x
                    sy += y
                    cnt += 1
        if cnt:
            rows.append((i, sx / cnt, sy / cnt, cnt))

    if not rows:
        print(f"区域 {x0},{x1},{y0},{y1} 内无暗像素（阈值 <{th}）——调高阈值或换区域")
        return 1

    xs = [r[1] for r in rows]
    ys = [r[2] for r in rows]
    print(f"{path}  {W}x{H}  有效帧 {len(rows)}  暗阈值<{th}  区域 x[{x0},{x1}] y[{y0},{y1}]")
    print(f"质心 x: min={min(xs):.1f} max={max(xs):.1f} 极差={max(xs) - min(xs):.2f}px")
    print(f"质心 y: min={min(ys):.1f} max={max(ys):.1f} 极差={max(ys) - min(ys):.2f}px")
    step = max(1, len(rows) // 20)
    print("帧:x,y →", " ".join(f"{i}:{x:.1f},{y:.1f}" for i, x, y, c in rows[::step]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
