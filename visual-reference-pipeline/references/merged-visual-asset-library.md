<!-- 由 visual-asset-library 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/content-creation/visual-asset-library -->

---
name: visual-asset-library
description: 批量整理图片素材库：识别→重命名→风格提示词→Obsidian 家谱文档。Use when 用户要整理一批收藏图片。
---

# 视觉素材库整理 (Visual Asset Library)

把浏览器采集/散落的图片文件夹整理成可检索、可复刻的视觉风格参考库。

## 触发场景
- 用户有一批采集图（典型命名如 `收藏到 ARM connections_xxx.jpg`），要求"分析内容、重新命名、倒推视觉风格提示词"
- 需要为生成平台准备提示词（中文给即梦/可灵，英文给 Midjourney）
- 需要把素材沉淀进 Obsidian 库做风格分类

## 核心流程
1. **批量视觉识别**：MiniMax-M3（辅助视觉模型，见 ~/.hermes/config.yaml 的 auxiliary.vision）base64 图 + 结构化 prompt → JSON。复用脚本 /Users/Jin/Documents/Hermes/analyze_images.py（5 并发、断点续跑、结果每 10~15 条落盘；60 张 ≈ 2.5 分钟）
2. **命名映射表**：按 `主体_来源特征` 中文命名（25 字内、下划线分隔、无特殊字符）。先出映射表给用户审阅，确认后才执行；执行前生成 新名↔原名 JSON + 回滚脚本（build_mapping.py / do_rename.py）
3. **风格提取**：7 维拆解——主体/构图/配色/风格媒介/光影质感/字体特征/时代标签
4. **家族聚类**：按 风格媒介×时代标签 做**关键词模糊聚类**，人工归纳成 ~10 个风格家族（build_templates.py 的 FAMILIES 规则表）。精确匹配会碎成 50+ 套等于没去重
5. **中英双语提示词**：中文提示词必须单独生成（用户要求），不能只给英文。方法见 references/minimax-vision-api.md（直译不稳定，需校验+重试+拼装兜底）
6. **Obsidian 整合文档**：单一文档，风格家族为章节，每家族一个"模板提示词"引用块 + 样张表格（merge_family_doc.py）。用户偏好整合成一份，不散成多份

## 关键陷阱
- **Obsidian 表格内嵌图**：`![[img.png|180]]` 里的竖线 `|` 会被表格语法当成单元格分隔符，链接被切成两段 → 表格内必须用 `<img src="样张/xxx.jpg" width="180">`（src 相对路径是相对**笔记所在目录**，不是 vault 根）
- **推理模型 token 预算**：MiniMax-M3 是推理模型，max_tokens 太小会被 think 吃光 → 返回空字符串
- **enable_thinking**：纯文本任务（翻译/提取）加 `"enable_thinking": false`
- **模型无视"只输出X"指令**：会输出 "The user wants me to translate..." 英文元评论 → 必须内容校验（见 references/minimax-vision-api.md）+ 重试 + 结构化字段拼装兜底
- **聚类粒度**：模型自由文本精确匹配=每张一套模板 → 必须用关键词家族规则归并
- **重命名安全**：先映射表后执行、可回滚、文件名 ≤60 字符防网盘/剪映导入报错；审阅超时未响应可按已授权继续（保留回滚）
- **脚本小坑**：os.listdir 后 isfile 要拼绝对路径，否则读到 0 个文件

## 用户偏好（重要）
- 全程中文回复；新文件名用中文
- 风格提示词必须**中英双语**：中文版喂国内平台（即梦/可灵），英文版喂 Midjourney
- 文档偏好**整合成单一文件**（家谱式），不要散成多份
- 图片排版用**表格统一宽度**（180px），避免大小不一
- 破坏性操作（重命名）前先出映射表审阅；内容质量把关严，渲染/语法错误会被指出

## 交付物清单
- 识别结果 JSON（原始数据，含 7 维 + 双语提示词）
- 重命名映射表 md + json + 回滚脚本
- Obsidian 整合文档（家谱式）+ 样张图文件夹（复制进 vault，勿用外部路径）

## 参考文件
- references/minimax-vision-api.md — MiniMax-M3 直连 API 的调用细节、推理模型坑、校验/重试/兜底模式
