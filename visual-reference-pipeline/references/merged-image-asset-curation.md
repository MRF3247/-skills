<!-- 由 image-asset-curation 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/media/image-asset-curation -->

---
name: image-asset-curation
description: "Organize image folders: rename by content, style prompts."
---

# Image Asset Curation (图片素材库工作流)

Batch-process a folder of collected images (browser collections, visual references, memes): identify content, rename files by content, reverse-engineer reusable visual-style prompts, and publish a family-grouped Obsidian gallery doc. Proven on 60-image collections; supports incremental re-runs.

## Workflow

1. **Inventory first** (before spending tokens): count files, extensions, pixel sizes via PIL, total MP. Est. cost: ~400-600 vision tokens/image + ~300-500 text tokens/image. Tell the user the estimate before the full run.
2. **Batch vision analysis** — one MiniMax-M3 call per image, structured 7-dimension extraction: 主体 / 类型 / 构图 / 配色 / 风格媒介 / 光影质感 / 字体特征 / 时代标签 + 建议命名 + 英文提示词. Concurrency 5, resume-from-JSON (skip already-done files), results written incrementally every N completions. See `references/minimax-m3-batch.md` for the script pattern.
3. **Quality gate**: check duplicate names, illegal filename chars (space `/\:*?"<>|`), missing fields, name length ≤60. Zero-dup, zero-illegal is the bar.
4. **Rename mapping**: generate a Markdown table (新名↔原名, grouped by 类型) for user review + a JSON mapping for execution + a rollback script (renames back via the same JSON). **Gate: user approves the mapping before renaming.** When approval is ambiguous, use clarify and proceed on best judgment only if the mapping is conflict-free and rollback exists.
5. **Bilingualize prompts** (user requirement): translate EN prompt → natural ZH prompt (model translation, NOT field stitching, for fluidity). This user uses 中文版 for 即梦/可灵, 英文版 for Midjourney.
6. **Refactor prompts — style vs elements** (user requirement): split each prompt into 美术风格 (构图/配色/媒介/质感/字体/时代/氛围) vs 画面元素 (specific nouns: bird, plum blossom, Fuji, neuron...). Output four fields: 风格_中 / 风格_英 / 元素_中 / 元素_英. Style prompts must contain NO concrete objects; elements go in their own column so the user can swap subjects freely.
7. **Family clustering** — do NOT exact-match cluster on free-text style fields (explodes to N families ≈ no dedup). Use keyword rules mapping to 10-12 style families (e.g. 浮世绘/木刻版画, 复古科学图鉴/蚀刻解剖, 点彩/半色调, 矢量扁平, 3D渲染, 复古拼贴, 水彩, 手绘线稿...). Pick the longest-prompt image as family representative.
8. **Obsidian gallery doc** — frontmatter (title/date/tags/source) + callouts + per-family table:
   `| 样张 | 文件名 | 画面元素 | 风格提示词（中文） | 风格提示词（英文） |`
   Sample images copied into a `样张/` subfolder inside the vault. **CRITICAL: in table cells use `<img src="样张/xxx.jpg" width="320"/>` — never `![[xxx.jpg|180]]`; the `|` in the wikilink is parsed as a cell separator and splits the link into two cells.** 320px is the size this user wants (large enough to see without clicking, small enough not to break layout). After generation, verify every row has the same pipe count and non-empty cells.
9. **变体：平铺表情包库合并**（N 个主题包 → 一个 `NNN-内容名` 平铺库，配 GIF动图 式使用库；含用户 3 问、判重账本坑、回滚产物、mp4 抽帧命名）→ `references/meme-library-flatten.md`。

## User preferences (this user)

- Chinese filenames, underscore separators, ≤60 chars, no spaces/special chars.
- Prompts: pure art-style only, elements listed separately (see step 6).
- Bilingual prompts (ZH + EN).
- Gallery docs: tables with uniform-width sample images; vault notes follow obsidian-markdown spec (frontmatter + callouts + tags).
- Workspace: source images in /Users/Jin/Documents/本地资源库/, vault docs in /Users/Jin/Documents/医时知识库/, scripts in /Users/Jin/Documents/Hermes/. Deliverables always land in the Hermes workdir, not /tmp.

## Pitfalls

- MiniMax-M3 (vision model, CN endpoint) is a reasoning model: `enable_thinking: false` is IGNORED — output always contains `<think>...</think>`, and thinking consumes the token budget. With `max_tokens: 400`, the real answer gets truncated to nothing. Use `max_tokens: 1500+` and strip `<think>...</think>` (regex, DOTALL) before parsing.
- Structured output: fixed-line format (`风格_英：xxx` on its own line) succeeds far more often than strict JSON for this model. If JSON is required, wrap literal braces in the prompt template as `{{ }}` or use placeholder replace — never `.format()` with literal JSON braces (KeyError).
- Validate + retry loop: re-request until content passes checks (contains CJK chars, doesn't contain model self-talk like "The user wants me to...", length threshold). 3-5 attempts with backoff; capture `socket.timeout` (it is NOT a subclass of URLError).
- Fallback when the model refuses: stitch the 7-dimension ZH fields (构图/配色/风格媒介/光影质感/字体特征/时代标签) into a usable style prompt; use 主体 as the element list.
- `os.path.isfile` needs the full joined path (bare filename returns False when cwd differs).
- Save partial results to JSON every ~10-15 completions; a crash mid-run must not lose work (make scripts resume-friendly).

## Verification

- After rename: file count unchanged, zero old-name residue, rollback script present.
- After doc generation: all rows with identical pipe counts; each row's 元素/风格中/风格英 non-empty; ZH column contains CJK, EN column contains ASCII letters.
