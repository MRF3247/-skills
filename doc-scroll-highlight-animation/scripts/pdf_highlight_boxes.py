#!/usr/bin/env python3
"""Extract highlight / crop boxes for a document-scroll animation from a PDF.

Usage:
  pdf_highlight_boxes.py <pdf> [--page N] [--dpi 300] [--pad 3]
                         --phrase "fragment" [--phrase "..." ...]
                         --out boxes.json [--preview preview.png]

For every --phrase, the lines on the page containing that fragment are unioned
into one padded crop box.  The containment report lists exactly which lines end
up inside each box, so a box that swallows neighbouring text is caught BEFORE
anything is rendered.

Run with a python that has PyMuPDF (`import fitz`), e.g. an existing venv:
  ~/Documents/Hermes/venvs/huashu/bin/python pdf_highlight_boxes.py ...
"""
import argparse
import json
import re
import sys


def norm(s):
    s = s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=1, help="1-based page number")
    ap.add_argument("--dpi", type=int, default=300, help="pixel coords are emitted at this dpi")
    ap.add_argument("--pad", type=float, default=3.0, help="padding around the box, in pt")
    ap.add_argument("--phrase", action="append", required=True,
                    help="text fragment to box (repeat for several boxes)")
    ap.add_argument("--out", help="write JSON here")
    ap.add_argument("--preview", help="write an annotated page PNG here")
    a = ap.parse_args()

    import fitz  # PyMuPDF

    doc = fitz.open(a.pdf)
    pg = doc[a.page - 1]
    page_w, page_h = pg.rect.width, pg.rect.height

    lines = []
    for blk in pg.get_text("dict")["blocks"]:
        for ln in blk.get("lines", []):
            txt = "".join(sp["text"] for sp in ln["spans"])
            lines.append((fitz.Rect(ln["bbox"]), txt))

    k = a.dpi / 72.0

    def px(r):
        return [round(r.x0 * k, 1), round(r.y0 * k, 1), round(r.x1 * k, 1), round(r.y1 * k, 1)]

    boxes = []
    for phrase in a.phrase:
        want = norm(phrase)
        hits = [r for r, t in lines if want in norm(t)]
        if not hits:
            first = want.split(" ")[0]
            near = [t for _, t in lines if first and first in norm(t)][:3]
            print(f"!! not found: {phrase!r}")
            for t in near:
                print(f"     nearby line: {t[:90]!r}")
            continue
        u = fitz.Rect(hits[0])
        for r in hits[1:]:
            u |= r
        box = fitz.Rect(u.x0 - a.pad, u.y0 - a.pad, u.x1 + a.pad, u.y1 + a.pad)
        inside = []
        for r, t in lines:
            it = fitz.Rect(r)
            it &= box
            area = max(0.0, r.width) * max(0.0, r.height)
            ia = max(0.0, it.width) * max(0.0, it.height)
            if area and ia / area > 0.35:
                inside.append([round(r.y0, 1), round(r.y1, 1), t.strip()])
        boxes.append({
            "label": phrase,
            "pt": [round(v, 1) for v in (box.x0, box.y0, box.x1, box.y1)],
            f"px{a.dpi}": px(box),
            "lines_inside": inside,
        })
        print(f"\n=== {phrase} ===")
        print(f"  box pt {boxes[-1]['pt']}  |  {a.dpi}dpi {boxes[-1][f'px{a.dpi}']}")
        print("  lines inside (must be ONLY the intended passage / its own sentence):")
        for y0, y1, t in inside:
            print(f"    y{y0}-{y1} | {t[:88]}")

    data = {"pdf": a.pdf, "page": a.page, "page_pt": [page_w, page_h],
            "render_dpi": a.dpi, "boxes": boxes}
    if a.out:
        with open(a.out, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nwrote {a.out}")

    if a.preview and boxes:
        # Annotated page: outlines + labels kept OUTSIDE the text column, in a
        # left/right gutter, so a label never covers the source text.
        from PIL import Image, ImageDraw, ImageFont
        z = 150 / 72.0
        tmp = "/tmp/_hlbox_page.png"
        pg.get_pixmap(matrix=fitz.Matrix(z, z), alpha=False).save(tmp)
        im = Image.open(tmp).convert("RGB")
        padl, padr = 250, 560
        canvas = Image.new("RGB", (im.width + padl + padr, im.height + 90), (245, 245, 247))
        canvas.paste(im, (padl, 60))
        dr = ImageDraw.Draw(canvas)
        try:
            fp = "/System/Library/Fonts/Hiragino Sans GB.ttc"
            Fs = ImageFont.truetype(fp, 26)
            Ft = ImageFont.truetype(fp, 32)
        except Exception:
            Fs = Ft = None
        colors = [(226, 152, 0), (210, 36, 36), (40, 110, 200), (20, 140, 90)]
        for i, b in enumerate(boxes):
            col = colors[i % len(colors)]
            x0, y0, x1, y1 = [v * z for v in b["pt"]]
            dr.rectangle([padl + x0 - 4, 60 + y0 - 4, padl + x1 + 4, 60 + y1 + 4], outline=col, width=4)
            dr.line([padl - 10, 60 + y0 + 6, padl + x0 - 6, 60 + y0 + 6], fill=col, width=3)
            dr.text((30, 60 + y0 - 8), f"({i+1}) {b['label'][:26]}", fill=col, font=Fs)
        for i, b in enumerate(boxes):
            dr.text((im.width + padl + 24, 110 + i * 36), b["label"][:40], fill=(40, 40, 45), font=Fs)
            for j, (yy0, yy1, t) in enumerate(b["lines_inside"][:6]):
                dr.text((im.width + padl + 24, 150 + i * 36 + j * 30), "  " + t[:34], fill=(110, 112, 118), font=Fs)
        dr.text((30, 14), "crop boxes \u2014 labels kept off the text", fill=(20, 20, 20), font=Ft)
        canvas.save(a.preview)
        print(f"wrote {a.preview}  {canvas.size}")


if __name__ == "__main__":
    sys.exit(main())
