<!-- 由 pdf-image-vision-analysis 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/pdf-image-vision-analysis -->

---
name: pdf-image-vision-analysis
description: "Read PDF images/charts with vision when text misses visuals."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [pdf, vision, images, extraction, pymupdf, subagents, parallel, charts, screenshots]
---

# PDF Image Vision Analysis

Use when a PDF's text layer alone is not enough: marketing decks, strategy docs, and reports carry real information in charts, screenshots, word clouds, and dashboards. Users who ask you to "read"/"学习" a PDF often implicitly expect the images read too — text-only extraction is a half-job for PPT-style PDFs. Also use when you need images from a PDF as deliverable assets.

## Workflow

1. **Extract the text layer first** (pymupdf, `page.get_text("text")` per page, save to a raw txt with `===== 第 N 页 =====` separators). This gives page structure + all selectable text.

2. **Extract all embedded images** (`scripts/extract_pdf_images.py`): iterate `page.get_images(full=True)`, `Pixmap(doc, xref)`, convert CMYK→RGB (`Pixmap(pymupdf.csRGB, pix)`), skip tiny images (<50px — icons/watermarks), save as `p{page:02d}_i{idx}.png`.

3. **md5-dedup to separate content from decoration**: PPT backgrounds repeat on every page (same bytes). Compute md5 per file, group by hash:
   - Duplicated groups = background/decoration → skip (but note which are true content repeated for layout, e.g. logos).
   - Unique files = actual content screenshots/charts. Typically a 50-page deck yields 194 extracted → ~80 unique content images.

4. **Read the content images with vision in parallel subagents** — this is the scalable pattern for 50-100 images:
   - Split the unique set into ≤3 batches, one `delegate_task` per batch (respect delegation.max_concurrent_children).
   - Give each subagent the same detailed vision prompt (describe all visible text/numbers/axis/peaks, mark text-layer-missing details with ⭐).
   - **CRITICAL: give each subagent a UNIQUE output filename** (e.g. `shemei_imgs_竞品报告.md`, `shemei_imgs_数据图表报告.md`). Parallel subagents writing the same default path silently overwrite each other — observed: two subagents both wrote `shemei_imgs_报告.md`, the later one clobbered the earlier 22-image report, which had to be re-dispatched.
   - If a report is lost/overwritten, re-dispatch that batch with a fresh filename rather than reconstructing from memory.

5. **Merge findings into the source note**: add a "插图补充发现" section; keep text-layer facts and image-derived facts separate (⭐ = not in text layer); flag contradictions (e.g. B站 content-index 1.2w vs search-index 460 — a 26× scale difference, two different metrics).

6. **Archive assets**: copy extracted images + per-batch analysis reports into the vault's 附件 folder so the note can reference them; clean up working-dir temp files only after archiving.

## Pitfalls

- **`read_file` misdetects UTF-8 text as binary** ("Binary file") for some extracted text files — read via `python3 -c "print(open(path,encoding='utf-8').read())"` instead of trusting the verdict.
- **Vision batches can hit fd limits** (Errno 24, macOS ulimit 256) when firing many parallel vision_analyze calls; reduce batch width (observed: 6 parallel → 2 parallel worked).
- **Deleting a duplicated section with index-slicing is dangerous**: computing `rfind('\n---\n', 0, first)` + `c[second:]` to remove a duplicate chapter also removed the following chapter (the "second" anchor was inside the content being deleted). Prefer `patch` with unique anchor strings; if slicing, re-read the file and verify chapter list after.
- **Use `patch` to reorder sections, not delete+re-append from memory** — a full re-append of a long chapter is error-prone (observed chapter 8 lost and restored).
- Some extracted images are pure backgrounds — the vision subagent will flag them; that's fine, don't pre-filter beyond md5+size.
- OCR-vs-truth ambiguity: vision reads numbers with ±5% error; label uncertain values ("识读存疑") rather than asserting.

## Support files

- `scripts/extract_pdf_images.py` — pymupdf image extraction with CMYK→RGB and min-size filter; pass PDF path + outdir.
