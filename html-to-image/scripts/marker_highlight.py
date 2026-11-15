"""在截图上画「真马克笔」荧光笔高亮。

用法：
  python3 marker_highlight.py shot.png lines.json out.png [--alpha 0.8]

lines.json 来自页面里 Range.getClientRects()（视口像素坐标，与截图 1:1 时可直接用）：
  [{"y": 303, "x1": 196, "x2": 799}, ...]
  同一 y 的多个 rect 先合并成 min(x1)..max(x2)。

若截图与视口不是 1:1（browser_vision 的 PNG 尺寸 ≠ JS innerWidth），先读 PNG 实际尺寸算出
scale，把 lines 里的坐标乘同一个比例（两个方向比例可能不同，分开算）。

要点（被用户/视觉审核打回过的）：
  - CSS background-image 高亮 = 规整色块，像数字高亮，会要求返工；必须逐行用 PIL 画。
  - 用 multiply 叠色，不要半透明覆盖：字才透得过。
  - alpha 低于 ~0.6、边缘不起伏、端点直角，都会被判「不像真马克笔」。
"""
import argparse
import json
import random

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

YELLOW = np.array([255, 216, 20], dtype=np.float64)


def soft_ends(n, k=9):
    w = np.ones(n)
    e = min(k, n // 3)
    w[:e] = np.linspace(0.15, 1.0, e)
    w[-e:] = np.linspace(1.0, 0.1, e)
    return w


def build_mask(size, lines, seed=101):
    random.seed(seed)
    np.random.seed(seed)
    w_img, h_img = size
    mask = np.zeros((h_img, w_img), dtype=np.float64)
    for y, x1, x2 in lines:
        left = max(0, int(x1) - random.randint(2, 9))
        right = min(w_img, int(x2) + random.randint(2, 13))
        xs = np.arange(left, right)
        n = len(xs)
        if n < 4:
            continue
        top = y + 2 + random.uniform(-0.8, 0.8)
        bot = y + 23 + random.uniform(-0.8, 0.8)
        slope = random.uniform(-0.035, 0.035)
        jitter_t = np.cumsum(np.random.normal(0, 0.5, n))
        jitter_b = np.cumsum(np.random.normal(0, 0.5, n))
        yt = top + slope * (xs - xs[0]) + jitter_t
        yb = bot + slope * (xs - xs[0]) + jitter_b
        yt -= yt.mean() - top
        yb -= yb.mean() - bot
        col = 1.0 + 0.10 * np.sin(np.linspace(0, random.uniform(6, 14), n)) + np.random.normal(0, 0.07, n)
        col = np.clip(col, 0.72, 1.22) * soft_ends(n)
        for k in range(n):
            t = int(np.clip(yt[k], 0, h_img - 1))
            b = int(np.clip(yb[k], 0, h_img - 1))
            if b - t < 3:
                continue
            prof = np.ones(b - t)
            edge = max(1, (b - t) // 7)
            ramp = np.linspace(0.5, 1.0, edge)
            prof[:edge] *= ramp
            prof[-edge:] *= ramp[::-1]
            val = prof * col[k] * 0.66
            mask[t:b, xs[k]] = np.maximum(mask[t:b, xs[k]], val)
        if random.random() < 0.55:  # 随机重涂，形成叠色加深
            s = random.randint(left, max(left + 1, right - 80))
            e = min(right, s + random.randint(80, 300))
            bt = int(np.clip(top + random.uniform(-1, 4), 0, h_img - 1))
            bb = int(np.clip(bot + random.uniform(-4, 1), 0, h_img - 1))
            if bb > bt:
                sub = mask[bt:bb, s:e]
                mask[bt:bb, s:e] = np.clip(sub * random.uniform(1.3, 1.65) + 0.06, 0, 1)
    mask = gaussian_filter(mask, sigma=0.55)
    tex = 1.0 + np.random.normal(0, 0.05, mask.shape) + 0.03 * np.sin(np.linspace(0, 400, w_img))[None, :]
    return np.clip(mask * tex, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("lines")
    ap.add_argument("out")
    ap.add_argument("--alpha", type=float, default=0.82)
    ap.add_argument("--crop-width", type=int, default=0)
    ap.add_argument("--seed", type=int, default=101)
    a = ap.parse_args()

    img = Image.open(a.image).convert("RGB")
    if a.crop_width and a.crop_width < img.width:
        img = img.crop((0, 0, a.crop_width, img.height))
    raw = json.load(open(a.lines))
    lines = [(int(l["y"]), int(l["x1"]), int(l["x2"])) for l in raw]

    arr = np.asarray(img).astype(np.float64)
    mask = build_mask(img.size, lines, seed=a.seed)[..., None] * a.alpha
    out = arr * (1 - mask) + (arr * YELLOW / 255.0) * mask
    res = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    res.save(a.out)

    zoom_w = min(res.width, 650)
    zoom = res.crop((min(180, res.width // 4), max(0, lines[0][0] - 12),
                     zoom_w + 160, min(res.height, lines[0][0] + 190)))
    zoom = zoom.resize((zoom.width * 2, zoom.height * 2), Image.LANCZOS)
    zoom.save(a.out.replace(".png", "_zoom.jpg"), quality=95)
    print(f"saved {a.out} {res.size} | 放大自检: {a.out.replace('.png', '_zoom.jpg')}")


if __name__ == "__main__":
    main()
