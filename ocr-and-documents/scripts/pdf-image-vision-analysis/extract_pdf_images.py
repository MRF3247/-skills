#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract all embedded images from a PDF for vision analysis.

Usage:
  python3 extract_pdf_images.py document.pdf [outdir]

Saves one PNG per image as p{page:02d}_i{idx}.png. Converts CMYK to RGB,
skips tiny images (<50px, icons/watermarks). After extraction, md5-dedup
to separate repeated PPT backgrounds from unique content screenshots:

  python3 - <<'EOF'
  import hashlib, os, collections
  d = "outdir"
  h = collections.defaultdict(list)
  for fn in sorted(os.listdir(d)):
      if fn.endswith(".png"):
          h[hashlib.md5(open(os.path.join(d,fn),'rb').read()).hexdigest()].append(fn)
  dups = {k:v for k,v in h.items() if len(v)>1}
  uniq = {k:v[0] for k,v in h.items() if len(v)==1}
  print(f"dup groups: {len(dups)}, unique: {len(uniq)}")
  EOF

The unique set is what a vision subagent should analyze; dup groups are
background/decoration (except logos that legitimately repeat).
"""
import sys
import os

import pymupdf


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pdf_path = sys.argv[1]
    outdir = sys.argv[2] if len(sys.argv) > 2 else "pdf_imgs"
    os.makedirs(outdir, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    total = 0
    for pno, page in enumerate(doc):
        for idx, img in enumerate(page.get_images(full=True)):
            xref = img[0]
            try:
                pix = pymupdf.Pixmap(doc, xref)
                if pix.n - pix.alpha > 3:  # CMYK -> RGB
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                if pix.width < 50 or pix.height < 50:
                    continue
                fn = os.path.join(outdir, f"p{pno+1:02d}_i{idx+1}.png")
                pix.save(fn)
                total += 1
            except Exception as e:
                print(f"p{pno+1} img{idx+1} failed: {e}")
    print(f"extracted {total} images -> {outdir}")


if __name__ == "__main__":
    main()
