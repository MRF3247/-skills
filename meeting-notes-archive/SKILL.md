---
name: meeting-notes-archive
description: 会议纪要归档到飞书知识库。Use when 用户要把录音/会议笔记整理成飞书会议纪要文档。
---

# 会议纪要归档：得到大脑录音笔记 → 飞书知识库

用户持续把得到大脑（Get 笔记）的**录音/会议笔记**归档到飞书 wiki「不卷@医时」→「2. 会议纪要」节点下，编号 `会议N-标题`（2026-08 已有 会议1~会议7）。重复性工作流，实测多次。

## 环境事实（2026-08 快照）

- 得到大脑 API：`GETNOTE_API_KEY` / `GETNOTE_CLIENT_ID` 环境变量已配置（读取走 `getnote-api` skill）。**直接用 os.environ 读取，不要用 grep 从 rtf 提取**（会覆盖成空值导致 401）。
- 飞书 wiki space：「不卷@医时」= `7673753190189337892`；「2. 会议纪要」节点 = `V4fbw2Ddui8Entk5kzmcVx7QnHb`。
- 飞书写入走 lark-cli：`docs +create --parent-token <wiki节点token> --content @xml` 可直接挂到 wiki 节点下成为子文档（无需先建再移动）。

## 步骤

1. **找笔记**：语义搜索 `POST /open/api/v1/resource/recall {query, top_k}`，按标题关键词命中（如「新员工入职合规与药物警戒培训」→ note_id `1919000896911555648`）。
2. **取全文**：`GET /open/api/v1/resource/note/detail?id=<note_id>`，正文在 `data.note.content`（markdown，含 📑智能总结/📅章节概要/✨金句精选/📋待办事项 四节 + 录音信息）。
3. **确认编号**：`lark-cli wiki +node-list --space-id 7673753190189337892 --parent-node-token V4fbw2Ddui8Entk5kzmcVx7QnHb --as user`，取最大会议号 +1。标题格式：`会议7-新员工入职合规与药物警戒培训记录`（= 会议N + 笔记原标题）。
4. **排版对齐既有会议文档**（会议1-6 的既有格式，务必保持一致性）：
   - `<title>会议N-标题</title>`
   - `<h3>📑 智能总结</h3>` → `<h4>录音信息</h4>` + `<ul>`（录音时间/时长/参与人数/内容类型）
   - 笔记图片 URL（`![](https://get-notes.umiwi.com/...)` 签名 URL）→ 保留为 `〔图片： url〕` 文本（对齐会议6 风格，不要试图下载重传）
   - `<h4>录音总结</h4>`：主题段 `<p><b>主题</b></p>`，条目 `<ul><li><b>标签</b>：内容</li></ul>`
   - `<h3>📅 章节概要</h3>`：时间戳链接 `<p><a href="https://getnotes.seek:秒">00:00:56</a> <b>标题</b> 内容</p>`
   - `<h3>✨ 金句精选</h3>` / `<h3>📋 待办事项</h3>`：`<ul><li>...</li></ul>`
   - XML 转义用 `xml.sax.saxutils.escape`（URL 里的 `&` → `&amp;`）
5. **创建**：`lark-cli docs +create --parent-token V4fbw2Ddui8Entk5kzmcVx7QnHb --content @meetingN.xml`（cwd 相对路径）。
6. **验证**：`docs +fetch --doc <doc_id> --detail with-ids` 核对 `<li` 数、时间戳 `<a ` 数与源一致；`wiki +node-list` 确认子节点出现在列表。

## 脚本（2026-11 起）

`/Users/Jin/.hermes/cache/scratch/md2xml.py <note_id> "会议N-标题" out.xml` —— 一条命令把 note.content 转成上面那套 XML（图片转〔图片：url〕、时间戳转 `<a href>`、`**bold**` 转 `<b>`、`* / -` 转 `<li>`），随后 `lark-cli docs +create --parent-token V4fbw2Ddui8Entk5kzmcVx7QnHb --content @out.xml`。校验看输出里的 li / 时间戳数。脚本在 scratch 目录（24h 闲置会被清），丢了按上文格式重写即可。

## 坑

- **用户给的 `https://www.biji.com/note/share_note/<短码>` 分享链接**：`web_extract`/`curl` 只拿到 SPA 空壳（title 空、body 无字），短码也不是 note_id。解法：`browser_navigate` 打开后 `browser_console` 读 `document.body.innerText` 拿标题与正文首段，再用标题去 `getnote notes --limit 5` 匹配最新 meeting 笔记拿真实 note_id，之后走 API 取全文。
- **编号先查、别沿用旧记忆**：会议号增长很快（2026-11 已到会议10），每次都要 `wiki +node-list` 取当前最大号 +1，避免撞号。

- **不要用 grep 从 ~/Documents/Hermes/APIs/*.rtf 提取 getnote 凭证**再塞给脚本——会得到空值 → HTTP 401。环境变量本来就有。
- 笔记 content 可能含特殊字符导致 `read_file` 判为 binary；用 python `open().read()` 或 `execute_code` 读。
- markdown 行级 → XML 转换模式可复用：`**主题**` → `<p><b>...</b></p>`、`- **label**：x` → `<li><b>label</b>：x</li>`、`[00:00:56](https://getnotes.seek:56) **t**` → 时间戳链接段。
