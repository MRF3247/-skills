"""把插画叠进 PSD 封面模板（正确读取 layer mask，psd-tools 的 topil() 不含蒙版）。

依赖: pip install psd-tools pillow numpy -i https://pypi.tuna.tsinghua.edu.cn/simple

用法: python cover_compose.py --psd cover.psd --art art.png --out cover-out.png [--width 1080]
"""
import argparse
import numpy as np
from PIL import Image
from psd_tools import PSDImage


def layer_pixels_with_mask(layer):
    """返回 (rgb, alpha)，alpha 取自 layer mask（若无 mask 则用自身 alpha）。"""
    img = layer.topil()
    if img is None:
        return None, None
    img = img.convert("RGBA")
    rgb = np.asarray(img.convert("RGB")).astype(np.float64)
    alpha = np.asarray(img)[:, :, 3].astype(np.float64)
    if layer.mask is not None:
        m = layer.mask.topil()
        if m is not None:
            m = np.asarray(m.convert("L")).astype(np.float64)
            if m.shape == alpha.shape:
                alpha = np.minimum(alpha, m)
    return rgb, alpha / 255.0


def describe(layer, idx):
    m = layer.mask.topil() if layer.mask is not None else None
    info = f"[{idx}] {layer.name!r} kind={layer.kind} visible={layer.visible} bbox={layer.bbox}"
    if m is not None:
        a = np.asarray(m.convert("L")).astype(float)
        rows = [int(a[y:y + 100].mean()) for y in range(0, a.shape[0], 100)]
        info += f"\n     mask rows(每100行): {rows}"
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--psd", required=True)
    ap.add_argument("--art", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=0, help="输出宽，默认用 PSD 画布宽")
    args = ap.parse_args()

    psd = PSDImage.open(args.psd)
    W, H = psd.size
    if args.width and args.width != W:
        H = int(round(H * args.width / W))
        W = args.width

    art = Image.open(args.art).convert("RGB").resize((W, H), Image.LANCZOS)
    canvas = np.asarray(art).astype(np.float64)

    print(f"canvas {W}x{H}")
    for i, layer in enumerate(psd):
        print(describe(layer, i))
        if not layer.visible:
            print("     -> 隐藏，跳过（通常是旧底图）")
            continue
        if layer.kind == "type":
            print("     -> 文字层，需自行栅格化，跳过")
            continue
        rgb, a = layer_pixels_with_mask(layer)
        if rgb is None:
            continue
        # 统一到画布尺寸（层可能是局部尺寸，用 bbox 贴回）
        l, t, r, b = layer.bbox
        layer_img = np.zeros((H, W, 3))
        layer_a = np.zeros((H, W))
        sx, sy = rgb.shape[1], rgb.shape[0]
        if sx != (r - l) or sy != (b - t):
            rgb_im = Image.fromarray(rgb.astype(np.uint8)).resize((r - l, b - t), Image.LANCZOS)
            a_im = Image.fromarray((a * 255).astype(np.uint8)).resize((r - l, b - t), Image.LANCZOS)
            rgb = np.asarray(rgb_im).astype(np.float64)
            a = np.asarray(a_im).astype(np.float64) / 255.0
        l, t = max(0, l), max(0, t)
        r2, b2 = min(W, l + rgb.shape[1]), min(H, t + rgb.shape[0])
        layer_img[t:b2, l:r2] = rgb[:b2 - t, :r2 - l]
        layer_a[t:b2, l:r2] = a[:b2 - t, :r2 - l]
        canvas = canvas * (1 - layer_a[..., None]) + layer_img * layer_a[..., None]
        print(f"     -> 已叠加，平均 alpha {layer_a.mean():.3f}")

    Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)).save(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    main()
