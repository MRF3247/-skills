# MiniMax-M3 直连 API 要点（批量视觉/文本任务）

## 配置
- endpoint: `https://api.minimaxi.com/v1/chat/completions`
- model: `MiniMax-M3`（**推理模型**，会先思考再回答）
- key: `MINIMAX_CN_API_KEY`（在 ~/.hermes/.env；**绝不在聊天/终端打印明文**，shell 里 `grep ... | sed 's/.*=//'` 引用）
- Hermes 侧已配 auxiliary.vision: provider=custom, model=MiniMax-M3（~/.hermes/config.yaml）

## 视觉输入
- base64 → `data:image/{jpeg|png|webp};base64,...`（webp 的 mime 是 image/webp）
- content 为数组：`[{"type":"image_url","image_url":{"url":...}}, {"type":"text","text":...}]`
- token 参考：一张 ~1.1MP 图 ≈ 400 输入 token（375x491 实测 439 含文本）

## 推理模型四大坑（按踩坑顺序）
1. **输出带 `<think>...</think>` 标签**：解析前必须剥离：
   `re.sub(r'<think>.*?</think>', '', content, flags=re.S)`，再剥残留 `<[^>]+>`
2. **max_tokens 太小被思考吃光 → 返回空字符串**：实测 60 条翻译中 25 条为空（max_tokens=400）。修复：max_tokens 提到 600 + 关思考
3. **`"enable_thinking": false`**：纯文本任务（翻译/提取/分类）必须加，实测有效；图片识别任务可不开（识别输出短，思考开销可控）
4. **偶发无视"只输出译文"指令**，输出 "The user wants me to translate the given English prompt..." 这类英文元评论（有时混着编号列表）。对策：
   - 内容校验正则：中文字符数 > 40 且不含 `'The user'` / `'Let me'` / `'break down'`
   - 重试最多 5 次（sleep 2s），全部失败走兜底
   - **兜底**：用识别阶段的结构化中文字段拼装——`主体 + 风格媒介+'风格' + 配色 + 构图 + 光影质感 + 字体特征 + 时代标签 + '高细节'`，过滤值为'无'的字段，'，'连接。信息完整但措辞生硬，可手工润色（本次 2 条兜底后手工重写）

## 批量脚本模式（analyze_images.py / translate_prompts.py 已验证）
- `ThreadPoolExecutor(max_workers=5)` 并发；60 张图识别 ≈ 148s，60 条文本翻译 ≈ 87s
- 结果每 10~15 条落盘一次 JSON，断点续跑：`todo = [f for f in files if f not in results]`（判空值用 `not v.get(key,'').strip()`，空字符串也算已处理）
- 请求失败重试 3 次，退避 `3*(attempt+1)`s；超时 60~90s
- **脚本小坑**：`os.listdir(dir)` 后 `os.path.isfile(f)` 必须拼 `os.path.join(dir, f)`，否则相对路径读到 0 个文件

## 中文提示词生成结论
模型直译质量不稳定（58/60 可用，2 条敷衍）。策略：先批量直译 → 长度校验（<40 字判为过短）→ 单独补翻 → 仍失败用字段拼装兜底 → 手工润色。中文提示词要求：逗号分隔短语序列（非散文）、保留风格/媒介术语（浮世绘、木刻版画、交叉排线、半色调…）。
