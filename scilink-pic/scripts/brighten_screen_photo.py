#!/usr/bin/env python3
"""把偏暗的实拍屏幕照片提亮，但不把屏幕内容（文字）洗白。

思路：在 LAB 亮度通道做 gamma 提亮（保护高光，不直接乘亮度），再小幅提曝光与饱和度；
对截图类照片不建议用自动对比度（会把白底拉爆、字反而变淡）。

用法：
    python3 brighten_screen_photo.py in.jpg out.jpg [--gamma 0.82] [--exposure 1.05] [--sat 1.06]
    --gamma <1 提亮中间调（0.8 明显变亮，0.9 轻微）；--exposure 全局曝光乘数；--sat 饱和度。
"""
import argparse
import numpy as np
from PIL import Image, ImageEnhance
from skimage import color as skcolor, exposure as skexposure


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * (x ** (1 / 2.4)) - 0.055)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--gamma", type=float, default=0.82, help="<1 提亮中间调")
    ap.add_argument("--exposure", type=float, default=1.05)
    ap.add_argument("--sat", type=float, default=1.06)
    ap.add_argument("--black-point", type=float, default=0.06,
                    help="提亮后重新压黑场的比例（0=不压；0.05~0.1 让字保持深色）")
    ap.add_argument("--lift", type=float, default=1.45, help="lift 模式的提亮强度（1.2 轻微，1.8 明显）")
    ap.add_argument("--mode", choices=["lift", "clahe", "gamma"], default="lift",
                    help="clahe=局部均衡（推荐，屏幕内容不易洗白）；gamma=全局 gamma")
    ap.add_argument("--clip", type=float, default=0.012, help="CLAHE clip_limit，越大对比越强")
    ap.add_argument("--kernel", type=int, default=64, help="CLAHE 网格大小")
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGB")
    arr = np.asarray(im).astype(np.float32) / 255.0

    if a.mode == "lift":
        # 抬中间调、保住两端（黑仍是黑、白仍是白）：x' = 1-(1-x)^k
        k = a.lift
        arr2 = 1.0 - np.power(1.0 - np.clip(arr, 0, 1), k)
        arr2 = np.clip(arr2 * a.exposure, 0, 1) ** a.gamma
        if a.black_point > 0:      # 重新压黑点：提亮后字会发灰，把暗字拉回深色
            bp = a.black_point
            arr2 = np.clip((arr2 - bp) / max(1e-6, 1 - bp), 0, 1)
        im2 = Image.fromarray((arr2 * 255).astype(np.uint8))
    elif a.mode == "clahe":
        # 只在亮度通道做局部均衡：暗区提亮、白底与黑字对比不被压平
        lab = skcolor.rgb2lab(arr)
        L = lab[:, :, 0]
        lo, hi = L.min(), L.max()
        Ln = (L - lo) / max(1e-6, hi - lo)
        Ln = skexposure.equalize_adapthist(Ln, clip_limit=a.clip, kernel_size=a.kernel)
        lab[:, :, 0] = Ln * (hi - lo) + lo
        rgb = skcolor.lab2rgb(lab)
        rgb = np.clip(rgb * a.exposure, 0, 1) ** a.gamma
        im2 = Image.fromarray((rgb * 255).astype(np.uint8))
    else:
        lin = srgb_to_linear(arr) * a.exposure
        lin = np.clip(lin, 0, 1) ** a.gamma
        out = linear_to_srgb(lin) * 255.0
        im2 = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    if a.sat != 1.0:
        im2 = ImageEnhance.Color(im2).enhance(a.sat)
    im2.save(a.out, quality=94)

    g0 = np.asarray(im.convert("L")).mean()
    g1 = np.asarray(im2.convert("L")).mean()
    print(f"saved {a.out} | 平均亮度 {g0:.1f} → {g1:.1f} (+{g1 - g0:.1f})")


if __name__ == "__main__":
    main()
