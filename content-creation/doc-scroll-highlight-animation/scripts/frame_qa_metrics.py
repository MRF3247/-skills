#!/usr/bin/env python3
"""帧级视觉审：从交付的 MP4 自己抽帧并量化（不采信实现方给的审片 PNG）。

用法:
  python3 frame_qa_metrics.py 成片.mp4 --at 0.5 3.2 5.6 8.5 10.6
  python3 frame_qa_metrics.py 成片.mp4 --at 3.2 8.5 --outdir /tmp/qa --card 243 --dark 120

每帧输出:
  * 浮出卡片 bbox 与左右留白（近白长横带）
  * 卡片内文字暗行带（估英文正文 / 中文对照的实高）
  * 投影检测：贴卡 2-30px 带 vs 卡外 40-70px 带的平均亮度（贴卡应更暗）
  * 马克笔像素量（黄 / 红）：跨帧递增 = 顺序单笔；一次到位后不变 = 并发
  * 成片 sha256 前 16 位（跟素材台账钉的哈希对一下）

依赖: ffmpeg（抽帧）+ PIL。刻意不用 numpy，任何带 PIL 的 python 都能跑。
"""
import argparse
import hashlib
import os
import subprocess
import sys

from PIL import Image, ImageChops


def extract(mp4, t, out):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", mp4, "-frames:v", "1", "-y", out],
        check=True,
    )
    return out


def row_runs(mask_bytes, W, H):
    """每行最长的 255 连续段长度（mask 必须是 0/255 的 L 图 tobytes()）。"""
    return [max(len(s) for s in mask_bytes[y * W:(y + 1) * W].split(b"\x00")) for y in range(H)]


def mean_lum(gray, box):
    return gray.crop(box).resize((1, 1), Image.BOX).getpixel((0, 0))


def measure(path, card_thresh=243, dark_thresh=120, band_frac=0.5):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    g = im.convert("L")
    res = {"file": os.path.basename(path), "size": (W, H)}

    white = g.point(lambda v: 255 if v >= card_thresh else 0)
    wb = white.tobytes()
    band = [y for y, v in enumerate(row_runs(wb, W, H)) if v > W * band_frac]

    if band:
        y0, y1 = band[0], band[-1]
        ym = (y0 + y1) // 2
        xs = [x for x, v in enumerate(wb[ym * W:(ym + 1) * W]) if v]
        x0, x1 = min(xs), max(xs)
        res["card"] = (x0, y0, x1, y1)
        res["margin"] = (x0, W - 1 - x1)

        # 卡片内文字行：逐行数暗像素，连续暗带 = 一个文本行
        cx0, cx1 = x0 + 5, x1 - 5
        dark = g.crop((cx0, y0, cx1, y1 + 1)).point(lambda v: 255 if v < dark_thresh else 0)
        db, cw = dark.tobytes(), cx1 - cx0
        counts = [sum(db[y * cw:(y + 1) * cw]) // 255 for y in range(y1 - y0 + 1)]
        lines, inl, start = [], False, 0
        for i, c in enumerate(counts):
            if c > 8 and not inl:
                inl, start = True, i
            elif c <= 8 and inl:
                inl = False
                if i - start >= 6:
                    lines.append((y0 + start, i - start))
        if inl and len(counts) - start >= 6:
            lines.append((y0 + start, len(counts) - start))
        res["lines"] = lines

        if x0 > 80:
            res["shadow"] = (
                mean_lum(g, (x0 - 70, y0 + 20, x0 - 40, y1 - 20)),
                mean_lum(g, (x0 - 30, y0 + 20, x0 - 2, y1 - 20)),
            )

    r, gg, b = im.split()
    yellow = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v > 200 else 0),
                            gg.point(lambda v: 255 if v > 170 else 0)),
        b.point(lambda v: 255 if v < 130 else 0))
    red = ImageChops.multiply(
        ImageChops.multiply(r.point(lambda v: 255 if v > 170 else 0),
                            gg.point(lambda v: 255 if v < 95 else 0)),
        b.point(lambda v: 255 if v < 95 else 0))
    res["yellow"] = sum(yellow.tobytes()) // 255
    res["red"] = sum(red.tobytes()) // 255
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mp4")
    ap.add_argument("--at", nargs="+", type=float, required=True, help="抽帧时间点（秒）")
    ap.add_argument("--outdir", default="/tmp/frame_qa")
    ap.add_argument("--card", type=int, default=243, help="卡片纸面阈值")
    ap.add_argument("--dark", type=int, default=120, help="文字暗像素阈值")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    h = hashlib.sha256()
    with open(args.mp4, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    print(f"成片: {os.path.basename(args.mp4)}  sha256[:16]={h.hexdigest()[:16]}  "
          f"{os.path.getsize(args.mp4)} bytes")
    print("（与素材台账 README 钉的哈希核一遍，改名覆盖过的版本会在这里露出来）\n")

    prev = {}
    for t in args.at:
        p = extract(args.mp4, t, os.path.join(args.outdir, f"f_{t}.png"))
        m = measure(p, args.card, args.dark)
        W, H = m["size"]
        card = m.get("card")
        if card:
            x0, y0, x1, y1 = card
            print(f"t={t:<5} {W}x{H}  卡片 x{x0}→{x1} y{y0}→{y1}  "
                  f"左右留白 {m['margin'][0]}/{m['margin'][1]}px")
            hs = [h_ for _, h_ in m.get("lines", [])]
            if hs:
                print(f"          卡内文本行高(暗带): {hs}")
            if "shadow" in m:
                outer, inner = m["shadow"]
                tag = "投影✓" if inner < outer - 5 else "投影不可见⚠"
                print(f"          投影: 卡外带 {outer} vs 贴卡带 {inner}  {tag}")
        else:
            print(f"t={t:<5} {W}x{H}  无长白卡（整页全亮或未浮出）")
        y, r = m["yellow"], m["red"]
        warn = ""
        if t in prev:
            if abs(y - prev[t][0]) < 50 and y > 1000:
                warn = "  黄笔本帧与上帧持平 → 检查是否并发"
        prev[t] = (y, r)
        print(f"          马克笔: 黄 {y} px / 红 {r} px{warn}")
        print(f"          帧文件: {p}")

    print("\n判读: 留白应 ≥100px/侧；贴卡带应比卡外带暗一档；"
          "同一颜色像素量应逐帧递增（顺序单笔）；印章应完整在画幅内且不压卡片。")


if __name__ == "__main__":
    sys.exit(main())
