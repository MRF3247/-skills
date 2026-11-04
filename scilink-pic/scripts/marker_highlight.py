"""在网页截图上画真马克笔高亮（边缘随机游走 + 逐列抖动 + 重涂加深）。

不依赖浏览器 CSS：CSS background 高亮出来是「数字色块」，不像荧光笔。

用法:
  1) 浏览器里取每行 rect: 
     [...document.querySelectorAll('p')].slice(2,5).forEach(p => {
       const r = document.createRange(); r.selectNodeContents(p);
       console.log(JSON.stringify([...r.getClientRects()].map(x => ({y: x.top, x1: x.left, x2: x.right}))));
     });
  2) 存成 lines.json 后: python marker_highlight.py shot.png lines.json out.png

lines.json 里同 y 的多段会被自动合并成 min-x / max-right。
"""
import json
import sys
import random
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

YELLOW = np.array([255, 216, 20], dtype=np.float64)


def merge_lines(raw):
    groups = {}
    for r in raw:
        y = int(round(r["y"]))
        key = round(y / 6)  # 同视觉行的容差
        x1, x2 = r["x1"], r["x2"]
        if key in groups:
            g = groups[key]
            g[1] = min(g[1], x1)
            g[2] = max(g[2], x2)
        else:
            groups[key] = [y, x1, x2]
    return [tuple(int(v) for v in g) for g in groups.values()]


def soft_ends(n, k=9):
    w = np.ones(n)
    e = min(k, n // 3)
    w[:e] = np.linspace(0.15, 1.0, e)
    w[-e:] = np.linspace(1.0, 0.1, e)
    return w


def build_mask(size, lines, line_h=23):
    w_img, h_img = size
    mask = np.zeros((h_img, w_img), dtype=np.float64)
    for y, x1, x2 in lines:
        left = max(0, x1 - random.randint(2, 9))
        right = min(w_img, x2 + random.randint(2, 13))
        xs = np.arange(left, right)
        n = len(xs)
        top = y + 2 + random.uniform(-0.8, 0.8)
        bot = y + line_h + random.uniform(-0.8, 0.8)
        slope = random.uniform(-0.035, 0.035)
        yt = top + slope * (xs - xs[0]) + np.cumsum(np.random.normal(0, 0.5, n))
        yb = bot + slope * (xs - xs[0]) + np.cumsum(np.random.normal(0, 0.5, n))
        yt -= yt.mean() - top
        yb -= yb.mean() - bot
        col = (1.0 + 0.10 * np.sin(np.linspace(0, random.uniform(6, 14), n))
               + np.random.normal(0, 0.07, n))
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
        if random.random() < 0.55:
            s = random.randint(left, max(left + 1, right - 80))
            e = min(right, s + random.randint(80, 300))
            bt = int(np.clip(top + random.uniform(-1, 4), 0, h_img - 1))
            bb = int(np.clip(bot + random.uniform(-4, 1), 0, h_img - 1))
            if bb > bt:
                sub = mask[bt:bb, s:e]
                mask[bt:bb, s:e] = np.clip(sub * random.uniform(1.3, 1.65) + 0.06, 0, 1)
    mask = gaussian_filter(mask, sigma=0.55)
    tex = 1.0 + np.random.normal(0, 0.05, mask.shape)
    return np.clip(mask * tex, 0, 1)


def main():
    shot, lines_json, out = sys.argv[1], sys.argv[2], sys.argv[3]
    random.seed(101); np.random.seed(101)
    raw = json.load(open(lines_json))
    lines = merge_lines(raw)
    img = Image.open(shot).convert("RGB")
    arr = np.asarray(img).astype(np.float64)
    mask = build_mask(img.size, lines)[..., None] * 0.82
    res = arr * (1 - mask) + (arr * YELLOW / 255.0) * mask
    Image.fromarray(np.clip(res, 0, 255).astype(np.uint8)).save(out)
    print(f"saved {out}  lines={len(lines)}")


if __name__ == "__main__":
    main()
