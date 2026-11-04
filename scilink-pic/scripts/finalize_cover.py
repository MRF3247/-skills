"""标准收尾：把生成的插画缩到封面尺寸并叠上固定 PSD 模板（logo + 顶部白渐变 + 底部蓝渐变）。

输出固定 1080×1440。psd-tools 的 topil() 不含图层蒙版，所以必须读 layer.mask 自己合成。

用法:
  python finalize_cover.py --art gen.png [--psd assets/cover-template.psd] [--out cover.png] [--width 1080]
"""
import argparse
import os
import numpy as np
from PIL import Image

DEFAULT_PSD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "cover-template.psd")


def layer_rgb_alpha(layer):
    img = layer.topil()
    if img is None:
        return None, None
    img = img.convert("RGBA")
    rgb = np.asarray(img.convert("RGB")).astype(np.float64)
    alpha = np.asarray(img)[:, :, 3].astype(np.float64) / 255.0
    if getattr(layer, "mask", None) is not None:
        m = layer.mask.topil()
        if m is not None:
            m = np.asarray(m.convert("L")).astype(np.float64) / 255.0
            if m.shape == alpha.shape:
                alpha = alpha * m
    return rgb, alpha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--psd", default=DEFAULT_PSD)
    ap.add_argument("--out", default="cover-final.png")
    ap.add_argument("--width", type=int, default=1080)
    args = ap.parse_args()

    from psd_tools import PSDImage
    psd = PSDImage.open(args.psd)
    pw, ph = psd.size
    W = args.width
    H = int(round(ph * W / pw))

    art = Image.open(args.art).convert("RGB")
    # 封面比例 3:4：先居中裁切再缩，避免拉伸变形
    target_ratio = W / H
    aw, ah = art.size
    if abs(aw / ah - target_ratio) > 0.005:
        if aw / ah > target_ratio:
            nw = int(round(ah * target_ratio))
            left = (aw - nw) // 2
            art = art.crop((left, 0, left + nw, ah))
        else:
            nh = int(round(aw / target_ratio))
            top = (ah - nh) // 2
            art = art.crop((0, top, aw, top + nh))
        print(f"居中裁切到 {art.size} 以匹配 {W}x{H}")
    canvas = np.asarray(art.resize((W, H), Image.LANCZOS)).astype(np.float64)

    for layer in psd:
        if not layer.visible:
            continue
        if layer.kind == "type":
            print(f"跳过文字层 {layer.name!r}（需自行栅格化）")
            continue
        rgb, alpha = layer_rgb_alpha(layer)
        if rgb is None:
            continue
        l, t, r, b = layer.bbox
        lw, lh = r - l, b - t
        if lw <= 0 or lh <= 0:
            continue
        if rgb.shape[1] != lw or rgb.shape[0] != lh:
            rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((lw, lh), Image.LANCZOS)).astype(np.float64)
            alpha = np.asarray(Image.fromarray((alpha * 255).astype(np.uint8)).resize((lw, lh), Image.LANCZOS)).astype(np.float64) / 255.0
        x0, y0 = max(0, l), max(0, t)
        x1, y1 = min(W, l + lw), min(H, t + lh)
        if x1 <= x0 or y1 <= y0:
            continue
        sub_rgb = rgb[:y1 - y0, :x1 - x0]
        sub_a = alpha[:y1 - y0, :x1 - x0][..., None]
        region = canvas[y0:y1, x0:x1]
        canvas[y0:y1, x0:x1] = region * (1 - sub_a) + sub_rgb * sub_a

    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(args.out)
    print(f"saved {args.out}  {W}x{H}")


if __name__ == "__main__":
    main()
