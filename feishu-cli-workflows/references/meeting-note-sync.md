# 得到大脑录音笔记 → 飞书「会议N」纪要文档（2026-08-18 会议7 实测）

用户话术：「我的得到大脑有一篇新增的录音笔记就是 xx，帮我整理到飞书的 不卷@医时 知识库，里面有个会议纪要，放在这个文档下面，编号为会议N」。

## 完整流程

1. **拿笔记**：得到大脑语义搜索
   ```python
   import os, json, urllib.request
   def call(method, path, body=None, params=""):
       url = f"https://openapi.biji.com{path}{params}"
       data = json.dumps(body).encode() if body else None
       req = urllib.request.Request(url, data=data, method=method, headers={
           "Authorization": os.environ["GETNOTE_API_KEY"],          # ⚠️ 直接读 env
           "X-Client-ID": os.environ["GETNOTE_CLIENT_ID"],
           "Content-Type": "application/json"})
       with urllib.request.urlopen(req, timeout=30) as r:
           return json.loads(r.read())
   r = call("POST", "/open/api/v1/resource/recall", {"query": "笔记标题", "top_k": 5})
   # data.results[].note_id → 取标题精确匹配那条
   d = call("GET", "/open/api/v1/resource/note/detail", params="?id=<note_id>")
   content = d["data"]["note"]["content"]   # markdown，存 /tmp/xxx.md
   ```
   ⚠️ note_id 是 int64，当字符串处理。API key 必须从 `os.environ` 读——用 grep 从 RTF 提取再 export 覆盖会覆盖成空 → 401。

2. **定编号**：`lark-cli wiki +node-list --space-id <space> --parent-node-token <会议纪要节点>` 数现有「会议N」最大 N → 新文档 N+1，标题 `会议N-主题`（会议6/会议7 命名先例：`会议7-新员工入职合规与药物警戒培训记录`）。

3. **转 XML**（meeting 笔记 content 的固定结构）：见下方转换规则。对齐既有会议文档排版（先 fetch 会议6 看模板）。

4. **创建**：`lark-cli docs +create --parent-token <会议纪要节点token> --content @xml/meetingN.xml`（cwd 相对路径；纪要 <10KB 一次成型不超时）。

5. **验证**：`docs +fetch --doc <id> --detail with-ids` 数 `<h3`/`<li`/`<a` 与源一致；`wiki +node-list` 确认节点挂载。

## 转换规则（meeting 类型笔记 → 飞书 XML）

| 源 markdown | 目标 XML |
|---|---|
| `### xxx` / `#### xxx` | `<h3>` / `<h4>`（📑智能总结 / 📅章节概要 / ✨金句精选 / 📋待办事项 用 h3；录音信息 / 录音总结 用 h4） |
| `![](url)` 封面图 | `<p>〔图片： url〕</p>`（**不嵌入图片**：签名 URL 会过期，且与既有会议文档风格一致） |
| 独立行 `**xxx**` | `<p><b>xxx</b></p>`（主题段） |
| `- **label**：content` / `* **label**：content` | `<ul><li><b>label</b>：content</li></ul>` |
| `- ` 普通列表项 | `<ul><li>...</li></ul>` |
| `[00:00:56](https://getnotes.seek:56) **标题** 内容` | `<p><a href="https://getnotes.seek:56">00:00:56</a> <b>标题</b> 内容</p>` |
| `- **“...”** (标签)` 金句 | `<ul><li><b>“...”</b> (标签)</li></ul>` |
| 其余段落 | `<p>...</p>` |

- XML 转义用 `xml.sax.saxutils.escape`（URL 里 `&` → `&amp;`）。
- 转换后 `parseString("<root>" + xml + "</root>")` 验证合法性（飞书 XML 无单一根元素，直接 parse 报 junk after document element 是误报）。

## 验证脚本的坑（写「内容无丢失」检查时）

- **先整体剥 markdown 标记、再按句切分**：金句 `**“...”**` 内含句号，先 split 再剥标记会把金句从引号中间切断 → 误报丢失。
- 剥行首列表符/标题符的正则加 `(?m)` 多行标志，否则只处理第一行。
- 提取 XML 纯文本要**递归**遍历元素节点（`<b>` 内文本在子元素里，只取直接文本节点会丢内容）。

## 实测数据点（会议7）

- 笔记 content 6121 字符 → XML 7174 字符，一次 `docs +create` 成功（无需分块）。
- 源 10 个时间戳章节 → XML 10 个 `<a>` 链接，全部保留。
- 编号规则确认：会议纪要节点下有会议1~6，第 7 篇自动续号。
