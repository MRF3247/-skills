---
name: batch-image-analysis
description: "Batch-analyze a folder of images via a vision model."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [vision, image-analysis, renaming, style-prompts, minimax, batch]
---

# Batch Image Analysis (vision API)

Analyze a whole folder of images with a vision-capable model: recognize
content, rename files by content, extract per-image style prompts, and
distill a deduped, reusable template library. Proven on a 60-image
collection (browser-saved reference screenshots) using MiniMax-M3 as the
auxiliary vision model.

## When to use
- User points at a folder of images and wants them renamed by content
- User wants visual style prompts reverse-engineered from reference images
- User wants an image collection categorized / a style template library
- User asks for a token/cost estimate for such a job

## Workflow

1. **Scope & estimate first.** Count files, types, total pixels (PIL).
   Then estimate tokens BEFORE any API spend: measured ≈400 input tokens
   per ~1.1MP image on MiniMax-M3 (see references/minimax-vision-api.md).
   Reasoning models add think-token overhead on output. Give the user the
   estimate up front — they explicitly asked for it before running.

2. **Present the scheme before executing** (user preference — he will ask
   "你的方案是什么" and only then approve). Scheme must cover: naming
   rules, style-prompt format, safety (mapping-table review + rollback),
   and deliverable files. Do not start API calls before approval.

3. **Verify the vision model.** Check `auxiliary.vision` in
   ~/.hermes/config.yaml (provider/model/base_url/api_key_env). Verify the
   model exists via `GET {base_url}/models` and live-probe one small image
   (one round-trip, ~440 tokens). NEVER print the API key — read it from
   .env inside the shell and pass by env var.

4. **Batch analysis.** Use scripts/batch_image_analyze.py — OpenAI-
   compatible chat/completions with `data:image/...;base64,` URLs,
   ThreadPoolExecutor (5 workers), 3-attempt retry with backoff, checkpoint
   JSON every 10 items, resume skips completed keys. Ask the model for a
   STRICT JSON object (fields: 主体/类型/构图/配色/风格媒介/光影质感/
   字体特征/时代标签/建议命名/英文提示词/中文备注), temperature 0.2,
   max_tokens ~900. 60 images @ 5 workers ≈ 148s wall, 0 failures.

5. **Rename safely.** Build a mapping (新名 → 原名) as JSON + a Markdown
   table grouped by content type. Validate: zero duplicate new names, zero
   illegal chars (`\/:*?"<>|` and spaces), extension preserved. Get user
   confirmation on the table, THEN rename, THEN auto-generate a rollback
   script from the same mapping JSON. Verify afterwards: file count
   unchanged, zero old-name residues.

6. **Style prompts.** Extract 7 dimensions per image: subject, composition,
   color palette, style/medium, lighting&texture, typography, era/culture.
   Output English comma-joined prompt (generation models respond best to
   English) + one-line Chinese note on what design it can be replicated as.

7. **Template library — cluster by KEYWORD FAMILIES, not exact match.**
   Exact-match clustering on free-text style fields yields ~1 template per
   image (useless). Instead classify each image into style families via
   keyword rules (浮世绘/木刻版画, 复古科学图鉴/蚀刻解剖, 卡哈尔式神经手绘,
   点彩/半色调, 矢量扁平现代插画, 现代极简/包豪斯几何, 3D渲染/科技未来,
   复古拼贴/混合媒介, 水彩生物艺术, 手绘线稿/钢笔素描, 复古印刷/胶片颗粒).
   Pick the longest-prompt image per family as representative; list the
   rest as "same template + replace subject/palette".

## Naming conventions (this user)
- Chinese filenames: `主体_来源特征[_编号].ext` — underscores, no spaces
  or special chars, ≤60 chars total (cloud-sync / editor-safe)
- Deliverable docs (mapping table, prompts, templates, rollback script)
  go to /Users/Jin/Documents/Hermes/

## Pitfalls
- `os.path.isfile(f)` without `os.path.join(IMG_DIR, f)` → 0 files found,
  script silently no-ops. Always join the dir.
- Reasoning vision models (MiniMax-M3) wrap answers in `<think>…</think>`
  that pollutes JSON. Strip think blocks, then stray XML tags, before
  parsing. Tolerant parse: on json.loads failure, slice from first `{` to
  last `}`.
- Clustering dedup: exact string match on 风格媒介×时代标签 → 59 templates
  for 60 images. Keyword-family rules are the fix. Order families so
  SPECIFIC keywords (浮世绘, 江户) match before GENERIC ones — "木刻版画"
  as a ukiyo-e keyword wrongly captured Victorian etchings and collage
  posters.
- read_file misdetects .md files with very long lines as binary — use
  `sed -n`/terminal instead of read_file for generated prompt docs.
- Checkpoint saves every ~10 items so a mid-run timeout loses nothing.

## Support files
- references/minimax-vision-api.md — MiniMax-M3 API facts measured 2026-08
  (endpoints, model list, token costs, think-tag behavior)
- references/kimi-vision-analysis.md — kimi code k3-256k 批量视觉分析
  （端点/key 读取/请求体/图片预处理/prompt 设计「只看视觉风格不读文字」/
  JSON 正则解析/max_tokens≥1200/批量筛选应用）— 视觉审核与风格分析默认走 kimi
- scripts/batch_image_analyze.py — proven batch analyzer; edit IMG_DIR /
  OUT_FILE / PROMPT and run
