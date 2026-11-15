# 飞书 Wiki 知识库 + 多维表格迁移完整配方（2026-08-14 语雀→飞书实测）

场景：用户要「一个知识库承载医时办公文档（产品资料/会议纪要/内容运营）+ B站对标账号索引表格」，语雀数据表（lakesheet）无 API 读写 → 整体转飞书。以下全部命令实测成功。

## 环境

- `export PATH="$PATH:$HOME/.local/bin"`（lark-cli 不在默认 PATH）
- 认证：`lark-cli auth status`（user identity ready）；冒烟 `lark-cli calendar +agenda`
- 关键：**所有 wiki/base/docs 操作带 `--as user`**（默认 auto 常解析成 bot，列不到用户资源）

## 1. 建知识空间 + 目录树

```bash
# 建空间（返回 space_id）
lark-cli wiki +space-create --as user --name "医时知识库" --description "..." 
# → space_id: 7673753190189337892

# 顶层节点（docx 类型 = 文档容器；也可用 TITLE 类分组）
lark-cli wiki +node-create --as user --space-id <sid> --title "1. 产品资料" --obj-type docx
# → node_token + url https://my.feishu.cn/wiki/<node_token>

# 子节点（挂在父节点下）
lark-cli wiki +node-create --as user --space-id <sid> --parent-node-token <父node> --title "a. 产品介绍" --obj-type docx

# 多维表格直接作为 Wiki 节点（语雀做不到的关键能力）
lark-cli wiki +node-create --as user --space-id <sid> --parent-node-token <父node> --title "B站对标账号索引" --obj-type bitable
# → node_token（wiki 路径）+ obj_token（= base_token）
```

## 2. 文档创建（docs +create）与 title 坑

```bash
# ⚠️ 必须带 <title>，否则文档显示 Untitled（warning: missing_document_title）
# 正确：XML 第一行就是 <title>标题</title>
lark-cli docs +create --as user --parent-token <wiki node_token> --content @doc.xml
# → document_id + url

# 补救已创建的 Untitled：overwrite 整篇重写（XML 开头加 <title>，并删掉正文里重复的 H1）
lark-cli docs +update --as user --doc <document_id> --command overwrite --content @titled.xml
```

## 3. 表格单元格上限 2000（大表必须拆）

- 报错：`SchemaChecker ... too many table cell, max=2000`（warning 里 degrade_code=4000025，文档仍创建但内容截断）
- 423 行 × 7 列 = 2961 超限 → 拆 4 个表，每表 140 行（140×7=980 单元格）
- 结构：`<title>` + `<h2>账号名</h2>` + `<blockquote>` 元信息 + 多个 `<table>`，表间 `<h3>稿件 N-M（第 K 部分）</h3>`
- 验证：`docs +fetch --doc <id> --detail simple` 数 `<table>` 数 / `<tr>` 数 / `<a href` 数

## 4. Base（多维表格）建表 + 1300 条导入

```bash
BASE=<base_token>; TABLE=<table_id>  # 从 wiki +node-get 的 obj_token / base +table-list 获取

# 表改名（默认叫 "Table"）
lark-cli base +table-update --as user --base-token $BASE --table-id $TABLE --name "账号索引"

# 删默认字段：Text 是主字段不能删（改名为业务主字段），其余可删
lark-cli base +field-update --as user --base-token $BASE --table-id $TABLE --field-id fldJh6M6SP --json '{"type":"text","name":"账号名"}' --yes
lark-cli base +field-delete --as user --base-token $BASE --table-id $TABLE --field-id fld6QQbjJW --yes

# 建业务字段（select 带 options / number 带 style / text 最小）
lark-cli base +field-create --as user --base-token $BASE --table-id $TABLE --json '{"type":"select","name":"分组","multiple":false,"options":[{"name":"正式","hue":"Green"},{"name":"候选","hue":"Wathet"},{"name":"扩展","hue":"Gray"}]}'
lark-cli base +field-create --as user --base-token $BASE --table-id $TABLE --json '{"type":"number","name":"粉丝数","style":{"type":"plain","precision":0,"thousands_separator":true}}'
lark-cli base +field-create --as user --base-token $BASE --table-id $TABLE --json '{"type":"text","name":"UID"}'

# 批量导入记录：payload = {"create_records":[{字段名:值, ...}, ...]}，每批 ≤200
lark-cli base +record-batch-create --as user --base-token $BASE --table-id $TABLE --json @batch.json
# 1300 条 = 7 批（6×200 + 100），批间 sleep 1s（防 1254291 并发写冲突）
```

### ⚠️ record-list 显示空值 bug

- `+record-list` 的表格视图和 `--format json` 输出**全是 null**，但数据实际已写入
- 正确验证：`+record-get --record-id <id>` 或 `+record-search --keyword 兔叭咯 --search-field 账号名`（能看到完整字段值）
- `+record-search` 必传 `--keyword` + `--search-field` 两个参数
- select 字段 CellValue 是数组 `["正式"]`；number 直接数字；text 字符串

### ⚠️ Base 默认自带 10 条示例空记录

- 新建 Base 的默认表（`records_count: 10`）自带 **10 条空示例记录**——删默认字段后它们变全空行，排在表格最前面（用户会反馈「前面几行都是空的」）
- 修复：先 `+record-list`（json 模式返回 `record_id_list`）确认哪些是空的，再删
- **删除参数是 `--record-id`（可重复传多次），不是 `--record-ids`**（unknown flag 报错）

```bash
lark-cli base +record-delete --as user --base-token $BASE --table-id $TABLE \
  --record-id recXXX --record-id recYYY --yes   # 批量删多条
```

- ⚠️ `+record-list` 分页参数是 **`--offset`**（int），不是 `--page-token`；返回结构里有 `record_id_list` + `has_more`，循环 `offset += len(ids)` 拉全量

### 清空 select 字段（批量）

用户要「分组列先空着」时：`+record-batch-update`，payload `{"update_records": {<record_id>: {"分组": []}}}`（**select 清空传空数组**），每批 ≤200 串行：

```bash
lark-cli base +record-batch-update --as user --base-token $BASE --table-id $TABLE --json @clear.json
# clear.json: {"update_records": {"recA": {"分组": []}, "recB": {"分组": []}, ...}}
```

### 按 redfox 数据重构 Base 字段（账号库模式）

用户要求「按 redfox 能拉到的数据整理表格」时，把 Base 字段对齐 redfox `accountDetail` 返回（22 字段），这样后续 redfox 数据可一一对应写入：

| redfox 字段 | Base 字段类型 | 说明 |
|---|---|---|
| follower / videoCount | number | 粉丝数 / 稿件数（本地库已能填） |
| likeCount / playCount / electricCount | number | 获赞 / 总播放 / 充电数 |
| redFoxIndex / weekRedFoxIndex / monthRedFoxIndex | number | 红狐指数-日/周/月（redfox 独有增量） |
| lastCreated | datetime（style.format yyyy-MM-dd） | 最近发文 |
| type/typeV2 / initTags / regionDesc | text | 分类 / 标签 / 地域 |
| officialTitle / sign | text | 认证 / 简介 |
| 分组（select） | 用户可能要求先空着 | 可后续用 redfox 分类/标签回填 |

要点：删除 redfox 没有的字段（如「粉丝(原文)」「来源」「收录日期」），新增 redfox 字段用 `+field-create --json`（number 带 `style:{"type":"plain","precision":0,"thousands_separator":true}`，datetime 带 `style.format`）。redfox 每账号 1 次 `accountDetail` 调用（¥0.02/次起）——拉数据前先问用户拉哪批（正式44 / 正式+候选100 / 全量1300），别默认全拉。

## 5. md → 飞书 XML 转换器（python 要点）

```python
from xml.sax.saxutils import escape
def inline(t):  # 行内：**b**→<b>、[t](url)→<a href>、`c`→<code>
    t = escape(t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)]+)\)', r'<a href="\2">\1</a>', t)
    return t
def md_to_xml(md):  # 标题→<hN>、表格（表头+分隔行）→<table><colgroup><col width>、列表→<ul>/<ol>、> →<blockquote>、---→<hr/>、段落→<p>
    ...
```
- 转换前清洗：去 frontmatter（`---...---`）、wikilinks `[[x]]`→纯文本、本地图片→`〔图片：名〕` 占位、Obsidian callout `> [!info]`→`<blockquote>` 或 `<callout emoji= background-color=>`
- 表格列宽 `<col width="90"/>` 等，表头 `<th><p>..</p></th>`，单元格 `<td><p>..</p></td>`

## 6. 验证与清理

- 结构树：`wiki +node-list --as user --space-id <sid>`（顶层）+ 每个父节点 `--parent-node-token` 递归
- 删除重复/测试节点：`+node-get` 拿 `obj_token` → `drive +delete --file-token <obj_token> --type docx --yes`（async，polling 完成）
- 交付：列文档链接清单（`wiki +node-get` 的 url / `docs +create` 返回的 url）

## 7. Base 内多块管理（2026-08-14 用户「全部文档整合进一个 Base」实测）

```bash
# Base 内建块：folder/table/docx/dashboard/workflow（块总数=表+仪表盘+文档 ≤300，其中 docx 文档块 ≤10）
lark-cli base +base-block-create --as user --base-token $BASE --type folder --name "产品资料"   # → folder 块 id (bfl...)
lark-cli base +base-block-create --as user --base-token $BASE --type docx --name "SciLink产品简介" --parent-id <folder块id>
# → docx_token（= 普通飞书文档 document_id，可 docs +update 写内容）+ 块 id (ldx...)
lark-cli docs +update --as user --doc <docx_token> --command overwrite --content @titled.xml   # 写正文（与 Wiki 文档无差异）

# Base 内建表（稿件清单模式）：+table-create 一次带字段
lark-cli base +table-create --as user --base-token $BASE --name "稿件清单" --fields '[
  {"name":"标题","type":"text"},
  {"name":"链接","type":"text","style":{"type":"url"}},
  {"name":"播放量","type":"number","style":{"type":"plain","precision":0}},
  {"name":"所属账号","type":"link","link_table":"账号索引"}
]'   # link_table 指向另一表名 → 跨表关联；首个字段为主字段

# 删除块
lark-cli base +base-block-delete --as user --base-token $BASE --block-id <块id> --yes
```

- ⚠️ **docx 块上限 10 个**（官方帮助中心 2026-03）：表+仪表盘+文档总数 300、**文档最多 10**。报错 `800080105 unsafe_operation_blocked` + hint「limit is 300」**有误导**——实际是 10 个文档配额用尽。产品 4 + 会议 6 = 正好 10，第 11 篇（方案）放不进去 → 应对：文档留 Wiki/普通文档（Base 管数据）、合并文档数、或 Base 只做数据中枢（账号/稿件/选题表 + 文档索引表挂链接）
- Base 内 docx 块有独立 URL（`my.feishu.cn/docx/<token>`），可编辑可分享，与 Wiki 文档等价
- 用户最终架构（2026-08-14 定）：**普通电子表格 > 多维表格**。用户建了「B站内容 副本」Base 想当主库（账号索引+稿件清单+文档块全整合），但体验后**否掉多维表格**（原话「感觉没必要用多维表格」），副本整个删除（`drive +delete --file-token <obj_token> --type bitable --yes`），转回：
  - Wiki「医时知识库」文档树不变（产品资料/会议纪要/方案留 docx）
  - 账号索引 + 稿件清单 → **普通电子表格**（`sheets +create --headers --data` + `wiki +move --obj-type sheet` 挂「ⅰ.B站参考账号」下），数据从 Base 导出（`+record-list --offset` 拉全量 → JSON → 2D 数组）
  - 账号表加了「是否对标」列（R 列，白名单精确匹配 44 个正式账号 = 对标，其余 1254 = 暂不对标）——批量打标见 SKILL.md「电子表格追加列/批量打标」节
