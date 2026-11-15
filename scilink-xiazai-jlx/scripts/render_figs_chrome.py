"""用 Chrome headless 把 figs/*.html 渲成 2 倍 PNG，并自动裁掉底部空白"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FIGS = Path("/Users/Jin/Documents/Open Programs/funasr/sskt_book/figs")
names = sys.argv[1:] or [p.stem for p in sorted(FIGS.glob("fig_*.html"))]

for name in names:
    src = FIGS / f"{name}.html"
    if not src.exists():
        print(f"✗ 缺文件 {name}.html")
        continue
    raw = FIGS / f"_{name}_raw.png"
    subprocess.run([
        CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
        "--force-device-scale-factor=2",
        "--window-size=960,2400",
        f"--screenshot={raw}",
        f"file://{src}",
    ], capture_output=True, timeout=120)

    if not raw.exists():
        print(f"✗ 渲染失败 {name}")
        continue

    im = Image.open(raw).convert("RGB")
    # 裁掉底部纯白
    bg = Image.new("RGB", im.size, im.getpixel((im.width - 2, im.height - 2)))
    diff = ImageChops.difference(im, bg)
    bbox = diff.getbbox()
    if bbox:
        im = im.crop((0, 0, im.width, min(im.height, bbox[3] + 24)))
    out = FIGS / f"{name}.png"
    im.save(out)
    raw.unlink()
    print(f"✓ {name}.png  {im.size[0]}×{im.size[1]}")
