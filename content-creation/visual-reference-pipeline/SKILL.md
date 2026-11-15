---
name: visual-reference-pipeline
description: 浏览器采集新图批量处理：识别→重命名→双语风格提示词→更新家谱文档→归档。
---

# 视觉素材批量处理流水线

处理入口：`/Users/Jin/Documents/本地资源库/浏览器采集`（新图丢这里）
归档库：`/Users/Jin/Documents/本地资源库/视觉参考`（已处理图移入）
产物文档：`/Users/Jin/Documents/医时知识库/视觉风格参考/视觉风格家谱/`（文件夹结构：`00_索引.md` 家族目录+wikilink，`01_~11_` 每风格家族独立文档，共享 `样张/` 子目录；每文档含家族模板提示词 + 样张表格 + 中英风格提示词 + 画面元素分离列）
脚本目录：`/Users/Jin/Documents/Hermes/`

## 标准流程（增量，可随时中断续跑）

0. **去重**：`python3 dedup.py`（在识别前跑！）
   - MD5 精确重复（含与归档库 视觉参考 的对比）→ 自动删除，保留质量最优副本
   - dHash 感知重复（同图不同分辨率/压缩，汉明距离 ≤5）→ 移入 `/Users/Jin/Documents/本地资源库/疑似重复/` 待用户确认
   - 归档库哈希索引：`视觉参考_哈希索引.json`（新归档后跑 `python3 dedup.py --index` 增量补建）
   - 好处：重复图不进入识别，省 token
1. **识别**：`python3 analyze_images.py`（后台跑，5 并发）
   - 自动跳过识别结果 JSON 中已存在的条目（断点续跑）
   - gif 自动转 PNG 首帧；`.DS_Store` 识别失败属正常，忽略
2. **清理错误条目**：删除结果中 `error` 字段条目（422 = MiniMax 内容审核敏感图，跳过并告知用户；可先用 PIL 验证文件是否损坏）
3. **生成增量映射**：`python3 build_mapping.py`（已过滤：只处理 浏览器采集 目录中仍存在的文件，不会重复处理已归档的）
4. **重命名**：`python3 do_rename.py`（按映射执行，失败 0 才放心；回滚脚本 浏览器采集_回滚脚本.py 自动生成）
5. **中文提示词**：`python3 translate_prompts.py`（只处理缺 中文提示词 的）
6. **风格/元素分离**：`python3 fix_refactor.py`（四行格式输出 风格_中/风格_英/元素_中/元素_英）
7. **收尾**：仍缺的条目跑 `python3 diag_refactor.py`（单线程+失败日志）；再手工检查 JSON（空 中文提示词/风格_中 用 7 维字段拼装兜底：风格=构图+配色+风格媒介+光影质感+字体特征+时代标签，元素=主体）
8. **更新文档**：`python3 merge_family_doc.py`（全量重新生成，含新旧全部；旧图"源图缺失"警告可忽略——样张已在 vault）
9. **归档**：按 重命名映射.json 把已处理新图 move 到 视觉参考（目标已存在则删源）

## 关键坑（都是实测踩出来的）

- **MiniMax-M3 是推理模型**：`enable_thinking:false` 无效，输出必带 `<think>` 内容且耗 token。**所有调用 max_tokens 必须 ≥1500**，否则正式输出被 think 截断成空（症状：结果 JSON 里字段为空串）
- **结构化输出用固定行格式**（如 `风格_中：xxx` 每行一个）远比严格 JSON 成功率高；JSON 格式模型约 60% 失败
- **偶发 socket.timeout**：脚本必须捕获 `socket.timeout`（不是 URLError 子类）并重试 3-4 次
- **文字密集的图用 OCR 读字，MiniMax 只管审美**（用户 2026-08-06 建议）：排版参考图/提示词截图/信息图文字多时，macOS Vision OCR（VNRecognizeTextRequest，zh-Hans+en-US）比 MiniMax 视觉转录准得多。分工：OCR 读字、MiniMax 看风格/版式/配色。脚本模板：swift /tmp/ocr_vision.swift <图>（accurate 级别）
- **识别结果 JSON 是累积档案，只增不删**：已归档的图不在 浏览器采集 目录是正常的（在 视觉参考 库）。清理脚本只允许删 `error` 条目，禁止按「文件不在采集目录」批量删条目（2026-08-06 曾误删 315 条历史记录，靠 merge 生成的家谱文档反向恢复，工具 restore_recognition.py）
- 若误删：merge_family_doc.py 生成的 11 个家族文档含全部样张表格（文件名/元素/风格中英），`restore_recognition.py` 可从家谱文档反向重建识别结果 JSON
- **所有处理脚本必须跳过 error 条目**：识别结果 JSON 里敏感图/DS_Store 的 error 条目没有 建议命名/英文提示词 等字段，build_mapping/translate/fix/merge 遍历时必须 `if "error" in v: continue`，否则 KeyError 崩溃（merge 崩溃时文档静默不更新，注意核对行数）
- **422 误判复查法**：MiniMax 对「女性/人体解剖类插画」常误触发色情审核（实测 FEMALE TORSO 白底插画被拦，灰度+224px 也无效）。复查手段：PIL 验证文件完好 → 主色调统计（92% 白底=正常）→ macOS Vision OCR 读图上文字/署名判断内容 → 确认正常后手工补识别记录（去 error 字段，补 建议命名/风格媒介/时代标签/风格_中/风格_英/元素_中/元素_英）→ 重命名归档 + 重跑 merge 即可收录
- **merge 源图查找**：样张复制先查 浏览器采集，找不到再查归档库 视觉参考；样张已存在则跳过（旧图归档后必然"源图缺失"，属正常，别误判）
- **Obsidian 表格内嵌图**：不能用 `![[xxx.jpg|180]]`（竖线 `|` 会被表格语法切开），必须用 `<img src="样张/xxx.jpg" width="320"/>`，src 相对笔记所在文件夹
- **文件名规范**：新名=中文 主体_来源特征，下划线分隔，无空格/特殊字符，≤60 字符，保留原扩展名
- 视觉模型调用用 `load_key()` 模式从 `~/.hermes/.env` 读 `MINIMAX_CN_API_KEY`，密钥永不打印

## 素材用途分流（可选）

用户曾问过表情包分流：新图可加"用途判定"（视觉参考/表情包/截图/其他），表情包归独立素材库。当前未实施，需要时在 analyze 的 prompt 里加一个字段即可。

## 相关文件

- analyze_images.py（识别，含 gif 转换）
- build_mapping.py / do_rename.py / 浏览器采集_回滚脚本.py（重命名链）
- translate_prompts.py / fix_refactor.py / diag_refactor.py（提示词链）
- merge_family_doc.py（文档生成，320px 样张 + 5 列表格）
- 浏览器采集_识别结果.json（数据源，126+ 条）

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `visual-asset-library` | 批量整理图片素材库：识别→重命名→风格提示词→Obsidian 家谱文档。Use when 用户要整理一批收藏图片。 | `references/merged-visual-asset-library.md` |
| `image-asset-curation` | Organize image folders: rename by content, style prompts. | `references/merged-image-asset-curation.md` |
