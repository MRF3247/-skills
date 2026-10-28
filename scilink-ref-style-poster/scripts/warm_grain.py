#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""封面上色后处理：加暖黄微光 + 细密颗粒噪点（不动主色域）。

用法: python warm_grain.py in.png out.png [--glow 0.22] [--grain 2.2] [--fx 0.78 --fy 0.24 --ratio 0.55]
"""
import argparse
import numpy as np
from PIL import Image


def gauss_field(h, w, cx, cy, rx, ry):
    ys = (np.arange(h)[:, None] - cy) / ry
    xs = (np.arange(w)[None, :] - cx) / rx
    return np.exp(-(xs ** 2 + ys ** 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--glow", type=float, default=0.20)
    ap.add_argument("--grain", type=float, default=2.2)
    ap.add_argument("--fx", type=float, default=0.78)
    ap.add_argument("--fy", type=float, default=0.24)
    ap.add_argument("--ratio", type=float, default=0.55)
    ap.add_argument("--warm", default="255,206,132")
    a = ap.parse_args()

    img = np.asarray(Image.open(a.src).convert("RGB")).astype(np.float64)
    h, w, _ = img.shape

    if a.glow > 0:
        warm = np.array([float(v) for v in a.warm.split(",")])
        f = gauss_field(h, w, a.fx * w, a.fy * h, a.ratio * w, a.ratio * h * 1.15)
        alpha = (f * a.glow)[..., None]
        # 只在亮部加暖光（暗部不动，避免发脏）
        lum = img.mean(axis=2, keepdims=True) / 255.0
        alpha = alpha * np.clip((lum - 0.45) / 0.55, 0, 1)
        img = img * (1 - alpha) + warm * alpha

    if a.grain > 0:
        rng = np.random.default_rng(7)
        n = rng.normal(0, a.grain, size=(h, w, 1)).repeat(3, axis=2)
        img = img + n

    out = np.clip(img, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(a.dst)
    print(f"{a.dst}  glow={a.glow} grain={a.grain}  size={w}x{h}")


if __name__ == "__main__":
    main()
