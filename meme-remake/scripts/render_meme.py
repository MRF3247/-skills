#!/usr/bin/env python3
"""Chrome headless 渲染梗图 HTML，并做尺寸 / 四边裁切自检。

用法:
    python3 render_meme.py meme.html out.png --w 960 --h 1280 --scale 2 --ratio 0.75

退出码非 0 = 自检未过（尺寸不符或内容贴边），此时不要交付。
"""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("out")
    ap.add_argument("--w", type=int, default=960, help="CSS 视口宽")
    ap.add_argument("--h", type=int, default=1280, help="CSS 视口高")
    ap.add_argument("--scale", type=int, default=2, help="device scale factor")
    ap.add_argument("--ratio", type=float, default=None, help="期望 宽/高，3:4 填 0.75")
    arg = ap.parse_args()

    src = Path(arg.html).resolve()
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         "--virtual-time-budget=6000",  # JS 生成的文字必须等渲染完，否则截到半张空白
         f"--screenshot={arg.out}",
         f"--window-size={arg.w},{arg.h}",
         f"--force-device-scale-factor={arg.scale}",
         f"file://{src}"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    im = Image.open(arg.out)
    w, h = im.size
    exp = (arg.w * arg.scale, arg.h * arg.scale)
    print(f"size {w}x{h}  expect {exp[0]}x{exp[1]}  ratio {w / h:.4f}")

    bad = False
    if (w, h) != exp:
        print("FAIL 尺寸不符：画布被内容撑开，或 JS 未渲染完")
        bad = True
    if arg.ratio and abs(w / h - arg.ratio) > 0.005:
        print(f"FAIL 比例 {w / h:.4f} != 期望 {arg.ratio}")
        bad = True

    gray = np.array(im.convert("L"))
    for name, edge in (("left", gray[:, :3]), ("right", gray[:, -3:]),
                       ("top", gray[:3, :]), ("bottom", gray[-3:, :])):
        ink = int((edge < 200).sum())
        if ink:
            print(f"FAIL {name} 边有 {ink} 个墨点像素 → 内容贴边或被裁")
            bad = True

    print("OK" if not bad else "SELF-CHECK FAILED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
