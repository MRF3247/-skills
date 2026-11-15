---
name: feishu-md-doc-sync
description: 本地 Markdown 同步为飞书云文档（含原图批量上传）。Use when 用户要把 .md 笔记转成飞书云文档。
---

# 本地 Markdown → 飞书云文档（含原图）

把本地 `.md`（含 `<img src="本地路径">` 引用）同步为排版良好的飞书云文档，图片全部上传原图。实测规模：225 张 / 115MB / 11 家族表格，全流程约 25 分钟（上传为主）。

## 前置条件

- `lark-cli` 已安装并绑定（`lark-cli auth status` 确认 user identity ready；身份 `--as user`）
- 必须先读 CLI 内置 skill：`lark-cli skills read lark-doc`（及其 references：lark-doc-xml.md、lark-doc-create.md、lark-doc-media-insert.md），不要从 --help 猜工作流

## 三个关键认知（决定方案）

1. **Markdown 导入不支持本地图片**：`docs +create --doc-format markdown` 的 `![alt](url)` 只接受 http(s) URL。本地图必须：上传拿 `file_token` → XML `<img src="file_token">` 引用。
2. **XML 可以直接引用 file_token**：`<img src="<file_token>" width="240" name="文件名"/>` 一次成型（CLI 会内部复制媒体，token 会变但内容正确）。无需先建文档再移动图片块。
3. **大内容一次性创建会超时**：约 120KB 的完整 XML 提交报 `server time out`。必须拆：先建骨架（title+说明+callout），再逐段 `append`（单段 ≤55KB 实测安全，超时则再拆半）。

## 标准流程

1. **解析 md** → 结构化 JSON（标题/说明/callout/家族/表格行/图片相对路径）。注意：跳过 YAML frontmatter；`##` 标题后跟 `> [!abstract]` 模板块；表格行按 `|` 拆列；图片 `<img src="...">` 提取 rel 路径。样例脚本 `scripts/parse_family_doc.py`。
2. **批量上传图片**：`lark-cli docs +create --title "临时-图片中转站（自动删除）"` 建临时文档 → 对每张图 `lark-cli docs +media-insert --doc <tmp> --file ./<rel> --width 240`（**cwd 必须在图片所在目录**，--file 只接受 cwd 内相对路径，禁止 `../`）→ 解析输出 `file_token` 存 state（断点续跑：每张后写 JSON；跳过已有 token 的）。
   - webp 必须同时传 `--height`（用 `sips -g pixelWidth -g pixelHeight <file>` 探测，按 240 宽等比算高），否则报 "source image dimensions could not be detected"
   - 失败重试 4 次；失败**必须**记录占位（`MISSING` 或单独失败列表），否则 retry 脚本找不到
3. **生成 XML**：`<title>` + 说明 `<p>` + 使用方式 `<callout emoji="bulb">` + 每家族 `<h2>` + 模板 `<callout emoji="abstract" background-color="blue">` + `<table>`（colgroup 列宽：图 240/文件名 140/元素 260/中 260/英 320）。文本 XML 转义（`&<>`）；callout 内**禁止** img/table（仅文本/标题/列表）；英文提示词去掉 markdown 反引号。
4. **分块创建**：先 `docs +create --content @skeleton.xml`（--content 支持 `@file`，仅 cwd 相对路径），再循环 `docs +update --doc <id> --command append --content @family_XX.xml`。append 顺序即文档顺序。失败重试 3 次，进度写 state 可续跑。
5. **验证**：`docs +fetch --doc <id> --detail with-ids` 统计 `<img ` 数 == 源图片数、`<h2 ` == 家族数、`<table ` 数、`<tr>` 行数；抽查 `docs +media-download --token <file_token> --output <f>` 用 `file` 命令确认是原图（重点查 webp）。
6. **清理**：`lark-cli drive +delete --file-token <tmp_doc> --type docx --yes` 删临时文档（已删会报 "file has been delete"，属正常）。测试文档同理。本地 `verify_download.jpg`、二维码等临时文件删掉。

## 轻量场景：纯 md → 知识库「父/子文档」（无图，最省事）

内容只有文字（如外文原文 + 中文译文、会议纪要、情报卡）时，不要走上面的图片与 XML 重流程。两步建节点 + 一条命令灌全文：

```bash
# 1) 父节点（知识库根层）——返回 node_token 与 obj_token
lark-cli wiki +node-create --space-id <space_id> --as user --title "<原文标题>" --format json
# 2) 子节点（挂在父 node_token 下）
lark-cli wiki +node-create --parent-node-token <父 node_token> --as user --title "中文译文｜<中文标题>" --format json
# 3)/4) 对各 obj_token 灌 markdown（@file 必为 cwd 相对路径）
lark-cli docs +update --doc <obj_token> --as user --doc-format markdown --command append --content @./draft.md
```

- **`append` 对空文档等于写全文**，不必先 fetch 拿 block_id；纯文本 md 一次 append 完即可。
- **标题策略（用户偏好）**：父 = 原稿标题原样（外文保留外文），子 = `中文译文｜<中文意译>`；不自创系列前缀。
- **库定位**：只给库名时用 `lark-cli wiki spaces list --as user --format json` 精确匹配 `name` 拿 `space_id`；写前 `wiki +node-list` 看根层命名习惯（编号目录 vs 平铺），新文档与同类文档并列，不自建文件夹。
- **写完回读**：`docs +fetch --doc <token> --format json` 取 `data.document.content`（XML 串），搜关键词验证转义与尾部完整；中文正文按 3 字节/字估算量级。
- **两个隐性坑**：①`wiki node-list` 不存在，只有 `wiki +node-list`（shortcut 都带 `+`）；②`+node-list` 的结果在 `data.nodes`，裸 API 才用 `data.items` —— 解析器写错字段会**静默返回 0 条**，误判成「库里没节点」。先把原始 JSON 原样打印看一眼再写解析。
- 节点层级/移动/删除的完整规则在 `lark-wiki` 技能（该技能为只读内置件，改动写在本技能），正文编辑/转义规则在 `lark-doc`。

## 清单/表格类内容：直接走 Markdown，别为表格写 XML

用户说「把这份清单列到这个文档」时（网站清单、信源表、对比表），**Markdown 管道表格就能直接成表**：

```bash
lark-cli docs +create --parent-token <wiki node_token> \
  --title "清单标题" --doc-format markdown --content @/tmp/list.md --as user
```

- `|` 表格 → 真正的 `<table>`；`[文本](url)` → 真正的 `<a href>`。`docs +fetch` 回读能看到 `<table>`/`<a href>` 即确认落位。
- `--parent-token` 直接吃 **wiki node_token**，一步建成该节点子文档，不用先 `wiki +node-create` 再二次写入。
- 只有需要 callout、自定义列宽时才转自定义列宽流程（见图文同传章节）。

## 最快路径：`<img path="@./x.jpg"/>` 直传 + `<grid>` 两列（2026-11 实测 91 张）

不必先建「临时中转文档」拿 file_token：XML 里直接写本地路径，CLI 会自己上传并换成 file_token。

```bash
cd <图片父目录>   # cwd 必须是图片所在的公共父目录
lark-cli docs +update --doc <doc_id> --as user --command append --doc-format xml --content @./_xml/part_01.xml
```

- 图片标签：`<img path="@./<子目录>/01.jpg" width="320"/>`（**`@` 前缀必须带**，否则报 `path must start with @`；绝对路径被拒）。
- 多图排版：`<grid><column width-ratio="0.5"><img …/></column><column width-ratio="0.5"><img …/></column></grid>`，两两一组，单图用 `width="480"`。回读后 `src` 变成新 file_token 属正常（CLI 内部复制媒体）。
- 大文档：先 `overwrite` 写骨架+总览表（会清空全文，只对自建空文档用），再 `for i in $(seq -w 1 17)` 逐段 `append`，每段 ≤5KB 最稳；段尾 `sleep 2`。
- 验收：`docs +fetch` 数 `<img `（应等于源图片总数）、`<h1>`/`<table>`/`<grid>` 计数，再 `docs +media-download --token <src>` 抽查 1 张 `sips -g pixelWidth` 确认是原图。

## 坑：URL 里的 `?table=ldx...` 不是数据表

用户贴的飞书链接常带 `?table=ldxXXXXX&view=vewXXXX`，但 `ldx` 开头是**文档块（docx block）**，数据表是 `tbl` 开头。

- 拿它当 table-id 读记录会报 `800010116: The provided table reference resolves to a docx block, not a table`。
- 正确处置：`base +table-list --base-token <t>` 先确认该 Base 有哪些表；表里没有这个 id 就说明链接指向**文档/BaseApp 页面**。按文档处理（`docs +fetch` 读现有内容，或按上文新建），不要往表里塞记录。
- 拿不准时先 `wiki +node-get --node-token <token>` 看 `obj_type`（bitable / docx）再决定动作，比猜快。

## 外部文章整篇导入飞书文档（公众号/网页 → 已有文档）

用户给「把这个链接的文章复制到这个文档里」时走这条，不是 md 同步：

1. **抓原文**：公众号用 `china-source-fetch` 的 curl + MicroMessenger UA 路线。**不要用转贴/客户端给的正文**——常被截断到几百字，图片全是空 `![]()`。
2. **先回读目标文档**确认是否为空：`docs +fetch --doc <url> --detail with-ids` 只回一个空 `<title>` 即空文档。
3. **图片先落盘**：从 `data-src` 逐张 `curl -sL -A "<微信 UA>" -e https://mp.weixin.qq.com/ <url> -o wximg/imgN.png`（缺 referer 拿占位图）。
4. **构造 XML**：`<title>` 打头（**overwrite 时 `<title>` 会连文档标题一起设上**，不必再调改名）；正文 `<p>`；引文 `<blockquote><p>原文</p><p>——出处</p></blockquote>`；原文小标题 `01 xxx` 写成 `<h1>01　xxx</h1>`；图片 `<img path="@./wximg/img1.png"/>`（cwd 相对路径，绝对路径会被拒）；文末补一行原文链接（`<a href=...>`）。
5. **空文档一次 overwrite**：`docs +update --doc <url> --command overwrite --doc-format xml --content @./article.xml`。空文档没有可丢的评论/资源，此时 overwrite 是安全选项；非空文档只能 `append`，勿 overwrite。
6. **回读核对**：`docs +fetch --doc <url> --doc-format xml` 数 `<img ` == 原图数、首尾段落与尾段尾句都在、标题已生效。

## 关键坑（全部实测）

- `--file` 严格限定 cwd 内相对路径：`../xxx` 报 `unsafe file path`；绝对路径也拒。workdir 设为图片目录，传 `./相对路径`。
- 图片显示宽度：飞书表格单元格内 320px 偏宽，240px 合适；点击图片可看原图，不必追求大缩略图。
- 文档超时创建可能残留：创建失败先 `drive +search` 查是否已建，避免重复。
- `+media-insert` 是写入操作（high-risk），批量跑之前先小样本（1 张图 + 1 个 1 行表格）验证全链路，确认 `img src=file_token` 在当前 CLI 版本可用。
- 中英提示词、元素文本含特殊字符（引号/`/`，XML 一律转义；`--content` 用 `@file` 绕开 shell 转义）。
- 飞书对文档媒体有配额/大小限制，单张 >20MB 自动分片（+media-insert 内置）；超大图可考虑先压缩。
- **中转文档可能被飞书侧风控删除**（实测 340 张上传到一半报 `resource deleted` / `Document page has been deleted`）：上传脚本每 ~40 张检查一次文档存活（`docs +fetch`），被删自动新建替换；断点续跑 + 幂等（有效 token 跳过）保证收敛。
- `--content @file` 只接受 **cwd 相对路径**：subprocess 必须 `cwd=BASE` 且传 `@xml/xxx.xml` 相对路径，绝对路径报 `--content: invalid file`。
- 多文档批量（每个 md → 一个 wiki 子文档）可用 `docs +create --parent-token <wiki_node_token> --content @skeleton.xml` 直接挂到 wiki 节点下（node_create 返回的 node 会出现在父节点下，`has_child` 变 true）；删测试节点用 `drive +delete`（会连 wiki 节点一起清），`wiki +node-delete` 需要 `--obj-type` 且对刚创建的节点易报 not_found。
- 解析 md 前先看表格是 markdown `|` 还是 HTML `<tr><td>` 格式（本文档用 HTML table）；索引 wikilink `[[a|b]]` 内含 `|`，拆列前先替换占位符。
- 分块按**字节**算（`len(x.encode('utf-8'))`），不要按字符数（中文 3 字节/字会超限）。
- `docs +fetch --detail with-ids` 返回 XML 在 `data.document.content`（不是 `data.content`）。

## 脚本模板（已实测，在 scripts/）

- `parse_family_doc.py` — 解析家谱类 md（frontmatter/说明/tip/家族 abstract/5 列表格）→ JSON
- `upload_images.py` — 批量 +media-insert 上传，断点续跑（state JSON）
- `retry_upload.py` — 补传失败/缺失图（webp 自动 sips 探测尺寸）
- `build_xml.py` — 用 file_token 构建完整 XML
- `create_doc.py` — 骨架 + 逐段 append，断点续跑

通用化改造提示：`parse_family_doc.py` 里的解析器是按「风格家谱」md 结构写的（家族=##、模板=callout、5 列表格）；其他 md 按同样思路解析后，复用 upload → build → create 三段即可。脚本里的 `BASE`/`IMG_DIR`/`SRC` 路径改为目标文档的实际路径。

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `feishu-doc-sync` | 本地 Markdown 同步为飞书云文档（原图上传、飞书格式排版）时使用。 | `references/merged-feishu-doc-sync.md` |
