#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract embedded images from a PDF, size-filtered, with optional md5 dedup.

Usage:
  python3 extract_pdf_images.py <file.pdf> <out_dir> [--dedup]

Writes p{page:02d}_i{idx}.png per image (skipping <50px decorations,
converting CMYK to RGB). With --dedup, prints duplicate/unique counts so you
know how many images actually need vision reading.

Verified in production: 50-page deck → 194 raw images → 83 unique content
images after dedup (backgrounds recur on every page).
"""
import hashlib
import os
import sys

try:
    import pymupdf
except ImportError:
    print("pip install pymupdf", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf_path, out_dir = sys.argv[1], sys.argv[2]
    dedup = "--dedup" in sys.argv
    os.makedirs(out_dir, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    hashes = {}
    total = 0
    for pno, page in enumerate(doc):
        for idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = pymupdf.Pixmap(doc, xref)
            except Exception as e:
                print(f"p{pno+1} img{idx+1} failed: {e}", file=sys.stderr)
                continue
            if pix.n - pix.alpha > 3:  # CMYK -> RGB
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            if pix.width < 50 or pix.height < 50:
                continue
            fn = os.path.join(out_dir, f"p{pno+1:02d}_i{idx+1}.png")
            pix.save(fn)
            total += 1
            if dedup:
                with open(fn, "rb") as f:
                    h = hashlib.md5(f.read()).hexdigest()
                hashes.setdefault(h, []).append(fn)

    print(f"extracted {total} images -> {out_dir}")
    if dedup:
        dup = {h: v for h, v in hashes.items() if len(v) > 1}
        print(f"unique md5: {len(hashes)}, duplicate groups: {len(dup)} "
              f"({sum(len(v) - 1 for v in dup.values())} duplicate files)")
        print(f"content images to read: {len(hashes)}")


if __name__ == "__main__":
    main()
