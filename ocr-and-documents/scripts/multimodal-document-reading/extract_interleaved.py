#!/usr/bin/env python3
"""Extract PDF content as position-interleaved text blocks and images.

Usage: python3 extract_interleaved.py <document.pdf> [output_dir]

- Per page: text blocks (get_text "blocks") and image rects
  (get_images + get_image_rects) are merged and sorted by (y, x).
- Every image is saved as pageNN_imgMM.png into <output_dir> (default:
  <pdf-name>_media/ in the CURRENT working directory — pass the user's
  working folder explicitly if the script runs elsewhere).
- Writes manifest.json: [{page, items: [{kind: text|image, ...}]}]
- Prints a compact per-page summary of the interleaved order.

Requires: pip install pymupdf  (use `python3 -m pip` if bare pip missing).
"""
import json
import os
import sys

import pymupdf


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    pdf_path = os.path.abspath(sys.argv[1])
    out_dir = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else (
        os.path.join(os.getcwd(), os.path.splitext(os.path.basename(pdf_path))[0] + "_media"))
    os.makedirs(out_dir, exist_ok=True)

    doc = pymupdf.open(pdf_path)
    print(f"PAGES: {len(doc)}")

    manifest = []
    for pno, page in enumerate(doc):
        text_blocks = []
        for b in page.get_text("blocks"):
            x0, y0, x1, y1, text, bno, btype = b
            text = text.strip()
            if text and btype == 0:
                text_blocks.append({"y": y0, "x": x0, "kind": "text", "text": text})

        img_blocks = []
        for info in page.get_images(full=True):
            xref = info[0]
            try:
                rects = page.get_image_rects(xref)
            except Exception:
                rects = []
            for r in rects:
                img_blocks.append({"y": r.y0, "x": r.x0, "kind": "image", "xref": xref,
                                   "w": r.width, "h": r.height})

        items = text_blocks + img_blocks
        items.sort(key=lambda it: (round(it["y"], 1), it["x"]))

        page_manifest = []
        for i, it in enumerate(items):
            if it["kind"] == "text":
                page_manifest.append({"kind": "text", "text": it["text"]})
            else:
                fname = f"page{pno+1:02d}_img{i:02d}.png"
                fpath = os.path.join(out_dir, fname)
                pix = pymupdf.Pixmap(doc, it["xref"])
                if pix.n - pix.alpha > 3:  # CMYK -> RGB
                    pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                pix.save(fpath)
                page_manifest.append({"kind": "image", "file": fpath,
                                      "size": f'{int(it["w"])}x{int(it["h"])}'})
        manifest.append({"page": pno + 1, "items": page_manifest})

    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    for pg in manifest:
        kinds = " | ".join(
            f'[T:{len(it["text"])}字]' if it["kind"] == "text"
            else f'[IMG {os.path.basename(it["file"])} {it["size"]}]'
            for it in pg["items"]
        )
        print(f"--- Page {pg['page']} ---")
        print(kinds)


if __name__ == "__main__":
    main()
