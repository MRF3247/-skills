<!-- 由 pdf-image-analysis 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/pdf-image-analysis -->

---
name: pdf-image-analysis
description: "Read images embedded in PDFs (charts, screenshots)."
version: 1.0.0
metadata:
  hermes:
    tags: [pdf, images, vision, documents, extraction, screenshots]
---

# PDF Image Analysis (Reading the Pictures in a PDF)

Use when: a PDF's images matter — decks/strategy PPTs full of screenshots, data charts, wordclouds, competitor account captures; the user asks "did you read the images / 插图你读了没"; text-layer extraction missed visual-only facts (prices, account names, 粉丝数, chart axis values, wordcloud keywords).

## Why

`pymupdf` text extraction (`get_text`) often omits image content entirely. For decks, the images routinely carry the unique facts: competitor account names/粉丝数, product prices (¥1396 etc.), exact chart values, wordcloud keywords, event-driven search spikes. Reading only the text layer = missing the payload. Always ask "does this document's value live in its images?" BEFORE extracting.

## Workflow

1. **Extract all images** with pymupdf (script: `scripts/extract_pdf_images.py`): per page `page.get_images(full=True)`, `Pixmap(doc, xref)`, skip <50px decorations, convert CMYK→RGB (`pix.n - pix.alpha > 3`), save as `p{page:02d}_i{idx}.png`.
2. **md5-dedup**: repeated backgrounds inflate counts hugely (194 raw → 83 unique in a 50-page deck). Group by content hash, keep one per hash. Background templates recur on every page — dedup filters them automatically and tells you how many images actually need reading.
3. **vision_analyze each unique image** with a targeted question, e.g. "图表类型、所有可见文字/数字/平台名、坐标轴刻度、峰值数值、词云关键词、结论" or "截图里所有可见文字（账号名、简介、标题、粉丝数、播放量、互动数、价格、按钮文字）".
4. **Volume handling**: for >~15 images, delegate to parallel subagents (batch up to 3, each gets a filename slice). Give each a strict output filename.
5. **Merge findings into the notes**: add a "插图补充发现" section, marking text-layer-missing details (⭐), and archive the images + per-group reports under the vault.

## Critical pitfalls

- **Parallel subagents must write DISTINCT output filenames.** Two background agents writing the same path (e.g. both `报告.md`) silently overwrite each other — one full report is lost with no error. Assign each task its own filename from the start. If one is lost anyway, re-run that slice with a fresh name, or recover the write_file content from the live transcript at `~/.hermes/cache/delegation/live/<id>/task-N.log` (the tool call args are logged).
- **Image counts ≠ content counts**: background/decor images dominate; ALWAYS md5-dedup before deciding how many images exist.
- **Vision reads have error**: chart numbers are ±5%; flag OCR-uncertain words (e.g. a brand name read two ways across screenshots) in the report rather than asserting one.
- **Charts may contradict the text layer**: e.g. B站 "内容指数" peak 1.2w vs text layer claiming "搜索峰值 460" — two different metric tabs of the same tool. Record both and note the 口径 difference; do NOT "fix" it.
- **`read_file` misdetects some valid UTF-8 files as binary** — fall back to `python3 -c "print(open('...', encoding='utf-8').read())"`; the file is usually fine.

## Support files

- `scripts/extract_pdf_images.py` — pymupdf image extraction with size filter and optional md5 dedup summary.
