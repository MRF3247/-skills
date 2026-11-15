# 腾讯文档 MCP 同步流程（mcp__tencent_docs__*）

用户常用腾讯文档（docs.qq.com）承载「方案→选题」成套文档：方案总纲 + 选题脚本总览在同一个腾讯文档里，Obsidian 侧放外链。

## 工具入口
- 工具名前缀 `mcp__tencent_docs__`，在 deferred catalog，需 `tool_search` / `tool_describe` 加载后 `tool_call` 调用。
- 常用：`get_content`（只读正文）、`doc_resolve_document_structure`（结构树，定位）、`doc_insert_markdown`（插入）。

## 读取
- `get_content(file_id)`：返回纯文本正文，只读。⚠️ 不返回位置索引/样式——编辑前必须另查结构。
- `doc_resolve_document_structure(file_id, mode=1)`：返回扁平节点列表（Heading/Paragraph/Table + start_index/end_index/paragraph_index）。编辑类工具定位 idx 用它，别用 get_content。

## 写入（插入方案章节）
- `doc_insert_markdown(file_id, idx, markdown)`：Markdown 转富文本插入。优先用 `base64_markdown` 避免特殊字符问题。
- **idx 用插入位置前一节点的 end_index**（如标题 Heading 的 end_index = 标题后）。插入位置=文档开头标题之后，即第一个 Heading 节点的 end_index。
- 返回 `new_version`；再用 `get_content` 回读验证插入成功且原有内容未被破坏。

## 成套文档模式（方案→选题）
- 结构：腾讯文档 = 标题 → 方案总纲章节（同步自 Obsidian 方案文档，含新增内容）→ 原有选题脚本总览（A1-A7 索引/发布节奏，保留不动）。
- 方案章节做成 `## 📋 一、方案总纲（…同步自 Obsidian）` 级别，小节用 `###`，表格保留 markdown 表格语法。
- 附录大数据（如 1,950 条选题库）**不塞腾讯文档**——留在 Obsidian 数据底座，腾讯文档只放方案核心 + 选题索引。
- Obsidian 侧：在资料索引 callout 里加 `[腾讯云成套文档（方案→选题）](https://docs.qq.com/doc/<file_id>)` 外链。

## Pitfalls
- 若 personal 与 enterprise 双账号都连接，写类工具会要求先选账号（AskUserQuestion）。
- 插入后必须回读验证：`doc_insert_markdown` 成功但内容错位的情况以 `get_content` 回读为准。
