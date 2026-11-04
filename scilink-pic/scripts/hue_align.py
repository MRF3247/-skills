"""只把某个色相域（默认蓝）对齐到参考图的分布，其它颜色一概不动。

这是唯一安全的调色后处理：全局 LAB 迁移会把图拉绿，限定色板映射会吃掉红色印章。

用法: python hue_align.py ref.png out.png aligned.png [--hue 175 255] [--strength 1.0]
"""
import sys
import numpy as np
from PIL import Image


def to_hsv(arr):
    mx, mn = arr.max(2), arr.min(2)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    i = m & (mx == r); h[i] = (60 * ((g[i] - b[i]) / d[i]) + 360) % 360
    i = m & (mx == g); h[i] = 60 * ((b[i] - r[i]) / d[i]) + 120
    i = m & (mx == b); h[i] = 60 * ((r[i] - g[i]) / d[i]) + 240
    s = np.where(mx > 0, d / np.maximum(mx, 1e-9), 0)
    return h, s, mx / 255.0


def from_hsv(h, s, v):
    hh = (h / 60.0) % 6
    c = v * s
    x = c * (1 - np.abs(hh % 2 - 1))
    m = v - c
    z = np.zeros_like(hh)
    r = np.select([hh < 1, hh < 2, hh < 3, hh < 4, hh < 5], [c, x, z, z, x], z)
    g = np.select([hh < 1, hh < 2, hh < 3, hh < 4, hh < 5], [x, c, c, x, z], z)
    b = np.select([hh < 1, hh < 2, hh < 3, hh < 4, hh < 5], [z, z, x, c, c], x)
    return np.clip(np.stack([r + m, g + m, b + m], 2) * 255, 0, 255).astype(np.uint8)


def main():
    ref_p, out_p, dst_p = sys.argv[1], sys.argv[2], sys.argv[3]
    lo, hi = 175.0, 255.0
    strength = 1.0
    if "--hue" in sys.argv:
        i = sys.argv.index("--hue"); lo, hi = float(sys.argv[i + 1]), float(sys.argv[i + 2])
    if "--strength" in sys.argv:
        strength = float(sys.argv[sys.argv.index("--strength") + 1])

    ref = np.asarray(Image.open(ref_p).convert("RGB")).astype(np.float64)
    src = np.asarray(Image.open(out_p).convert("RGB")).astype(np.float64)
    rh, rs, rv = to_hsv(ref)
    rm = (rh > lo) & (rh < hi) & (rs > 0.12) & (rv > 0.12)
    sh, ss, sv = to_hsv(src)
    sm = (sh > lo) & (sh < hi) & (ss > 0.12) & (sv > 0.12)
    if rm.sum() < 1000 or sm.sum() < 1000:
        print("色相域内像素太少，放弃对齐（检查 --hue 范围）")
        return

    new = {0: sh.copy(), 1: ss.copy(), 2: sv.copy()}
    limits = {0: (lo, hi), 1: (0.03, 0.95), 2: (0.03, 0.99)}
    for ch_i, (sch, rch, rmch) in enumerate(((sh, rh, rm), (ss, rs, rm), (sv, rv, rm))):
        smean, sstd = sch[sm].mean(), sch[sm].std() + 1e-6
        rmean, rstd = rch[rmch].mean(), rch[rmch].std() + 1e-6
        aligned = (sch[sm] - smean) / sstd * rstd + rmean
        blended = sch[sm] + (aligned - sch[sm]) * strength
        lo_c, hi_c = limits[ch_i]
        new[ch_i][sm] = np.clip(blended, lo_c, hi_c)

    out = from_hsv(new[0], new[1], new[2])
    Image.fromarray(out).save(dst_p)
    oh, os_, ov = to_hsv(out.astype(np.float64))
    om = (oh > lo) & (oh < hi) & (os_ > 0.12) & (ov > 0.12)
    print(f"ref  H{rh[rm].mean():.0f} S{rs[rm].mean():.2f} V{rv[rm].mean():.2f}")
    print(f"out  H{oh[om].mean():.0f} S{os_[om].mean():.2f} V{ov[om].mean():.2f}  -> {dst_p}")


if __name__ == "__main__":
    main()
