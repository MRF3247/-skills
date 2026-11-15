<!-- 由 multimodal-document-reading 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/multimodal-document-reading -->

---
name: multimodal-document-reading
description: "Read PDFs/PPTs mixing text and images in position order."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pdf, pptx, document, vision, extraction, interleaved, multimodal]
    related_skills: [ocr-and-documents, pdf, powerpoint]
---

# Multimodal Document Reading (text + images, in order)

Use when the user hands you a document (PDF, PPTX, report) that contains BOTH
text and images and wants its content understood — especially when image↔text
correspondence matters ("which figure belongs to which paragraph").

## Hard requirement: keep text and images interleaved

Read page by page, and WITHIN each page read text blocks and image blocks in
their on-page position order. NEVER read all the text first and all the images
after — you lose which figure illustrates which passage. The user has
explicitly demanded ordered reading; treat it as a correctness rule, not a
style nicety.

## Workflow

1. **Locate the file** with `search_files` (target='files', pattern `*name*`).
2. **Extract interleaved content** — run `scripts/extract_interleaved.py <pdf>`:
   - per page: text blocks via `page.get_text("blocks")`, image rects via
     `page.get_images(full=True)` + `page.get_image_rects(xref)`;
   - merge both lists, sort by (y, x);
   - save every image to the user's working folder (`<workdir>/<doc>_media/`,
     e.g. `/Users/Jin/Documents/Hermes/<name>_media/` — never /tmp),
     named `pageNN_imgMM.png`, plus a `manifest.json` mapping page → ordered items.
3. **Deduplicate decorative repeats** before vision analysis:
   `md5 -q page*.png | sort | uniq -c` — full-page backgrounds, page-footers
   and logos are byte-identical across pages. Typical result: 150+ embedded
   images collapse to ~20 real content images. Analyze the unique content
   images only (background/footer/logo: describe once, skip the rest).
4. **Read in order**: print each page's text (execute_code on the manifest),
   then `vision_analyze` that page's content images in position order, batched
   with the surrounding text in context. Ask each vision call a contextual
   question ("this is the screenshot in the 'avoid AI hallucination' section —
   what does it show?").
5. **Deliver a structured learning note** (markdown) saved in the working
   folder; group by the document's own section structure.

## Variant: chart/screenshot detail extraction (text-layer gap analysis)

When the task is to pull out of chart/screenshot images the precise details the
document's text layer lacks (axis values, peaks, word-cloud keywords, UI
elements, platform names):

- Use ONE fixed per-image question for consistency, covering: chart type, all
  visible text/numbers/platform names/keywords, axis ticks, peak values,
  word-cloud keywords, conclusion.
- Report format: group by image name (`## p06_i4`), each group with
  「图片内容」 and 「关键数据」; mark every detail NOT present in the text layer
  with ⭐ so the reader instantly sees what the images add. Close with a
  "top-N text-layer omissions" list in the summary.
- **Cross-check text-layer numbers against chart numbers.** A mismatch usually
  means different metric scopes or platforms, not an error — e.g. B站"内容指数"
  peak 12,000 vs text-layer "搜索量 460"; 微信指数 34M vs 百度指数 360K. Flag
  the discrepancy and state which metric each number belongs to.
- **Chinese keywords OCR'd from chart screenshots are often garbled**
  (e.g. 「领论求勘验」 for what is likely a different term). Label uncertain
  readings as OCR-uncertain instead of asserting them; if two similar charts
  give conflicting readings (e.g. reversed age peaks), report both and note
  the conflict rather than silently picking one.

## Pitfalls

- **`vision_analyze` parallel batches can exhaust file descriptors**: firing
  6+ vision_analyze calls in one turn can fail with `Errno 24: Too many open
  files` (common on macOS with `ulimit -n` 256). The images are fine — just
  reduce batch size to ~2 parallel calls per turn (or 1) and retry; single
  calls always work. Check `ulimit -n` first if in doubt.
- **CMYK images** crash or render wrong on save: convert first —
  `if pix.n - pix.alpha > 3: pix = pymupdf.Pixmap(pymupdf.csRGB, pix)`.
- **No bare `pip`** on some macOS setups — use `python3 -m pip install pymupdf`.
- **Small UI fragments** (logo bars, section chips) are noise; vision models
  over-interpret them. Read them only if the text around them references them.
- **Vision model may over-annotate** (e.g. describing a screenshot as "an
  architecture diagram"); the page text is the ground truth for what the image
  is for.
- **Clean up after**: the user requires all artifacts (test outputs, extracted
  media, scripts) to live in the working folder and test artifacts to be
  deleted on request — check with the user before keeping the `_media/` dir.

## Support files

- `scripts/extract_interleaved.py` — position-ordered text+image extraction
  with manifest output. Run it, then read the manifest in order.
- `templates/chart-image-analysis-report.md` — markdown skeleton for the
  per-image chart-analysis report (图片内容/关键数据 + ⭐ text-layer-gap marks).
