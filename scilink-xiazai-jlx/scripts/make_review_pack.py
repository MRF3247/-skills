"""打包送审包：教材源 + 逐字稿 + PPT 文字 + 成品 PDF，不含视频音频帧图

用法：python make_review_pack.py <项目目录> <输出.zip>

项目目录需含：00_成书/ 01_教材源/ 02_逐字稿/ 03_PPT帧OCR/
必须用 Python zipfile —— macOS 自带 zip 打中文目录名，对方解压成乱码。
"""
import sys
import zipfile
from collections import Counter
from pathlib import Path

A = Path(sys.argv[1])
OUT = Path(sys.argv[2])

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    # README
    for p in A.glob("README*.md"):
        z.write(p, f"00_{p.name}")

    # 成品 PDF
    for p in (A / "00_成书").glob("*.pdf"):
        z.write(p, f"01_成书/{p.name}")

    # 教材源
    for p in sorted((A / "01_教材源").glob("*.md")):
        z.write(p, f"02_教材源/{p.name}")

    # 逐字稿：原始与校对分开，审方靠对比验证校对质量
    for p in sorted((A / "02_逐字稿").glob("*.json")):
        kind = "校对" if "_proofed" in p.name else "原始"
        z.write(p, f"03_逐字稿{kind}/{p.name}")

    # PPT 页面文字（不带帧图）
    for p in sorted((A / "03_PPT帧OCR").glob("*_slides.json")):
        z.write(p, f"04_PPT页面文字/{p.name}")

names = zipfile.ZipFile(OUT).namelist()
print(f"✓ {OUT}  {OUT.stat().st_size / 1024 / 1024:.1f}MB  {len(names)} 个文件")
for k, v in sorted(Counter(n.split("/")[0] for n in names).items()):
    print(f"    {k}: {v}")
