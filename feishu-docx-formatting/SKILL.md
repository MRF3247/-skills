---
name: feishu-docx-formatting
description: 用 lark-cli 写飞书文档时用：表格样式边界、单元格批量填列表、图片分栏 grid、改前先 fetch。
version: 1.0.0
author: Hermes Agent (curated)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [飞书, feishu, docx, 表格, 背景色, 删除线, lark-cli]
    related_skills: [lark-doc, lark-wiki, lark-shared]
---

# 飞书 Docx 表格与样式写入（lark-cli 能力边界）

## When to Use

用 `lark-cli docs +update` / `docs +create` 向飞书云文档（docx / wiki）写入**带样式的表格**（单元格背景色、整行染色、删除线）时。触发：用户要求「整行染色 / 单元格涂色 / 涂黑 / 删除线 / 分类列颜色」等。官方 lark-doc skill 讲基本增删改，本 skill 记录**样式写入的能力边界与实测坑**，避免踩数小时的坑。

## 已验证的能力边界（2026-08-28 实测）

1. **XML 的 `<td background-color="...">` / `<th background-color>` 导入被静默丢弃。**
   `docs +update --doc-format xml` 写入后 fetch 回来，单元格 block 的 `table_cell` 是空对象 `{}`，颜色根本没存进飞书——**用 XML background-color 实现表格染色写了也白写**（同样适用于「粉丝量级染色」这类整行/整格着色，客户端里一直是无色的）。验证方法：`lark-cli api GET /open-apis/docx/v1/documents/{id}/blocks` 检查 table_cell 是否为空。

2. **删除线 `<del>`（markdown `~~`）是生效的**：写入后 `text_element_style.strikethrough=true`，fetch markdown 回来是 `~~text~~`。这是可用的「删除 / 待观察」标记，跨单元格整行打删除线可把每个 `<td>` 文字包 `<del>`。

3. **单元格背景色的正确路径 = 原生 API + 文本颜色枚举（文档化，未实测）**：
   `PATCH /open-apis/docx/v1/documents/{document_id}/blocks/{block_id}`，body 用 `update_text_elements`，在 `text_run.text_element_style.background_color` 设**数值枚举**。lark-cli 未封装此能力，需 `lark-cli api PATCH ...`。单元格内文字背景色撑满即视觉整格染色。使用前先用一个单元格验证。

4. **飞书只有 14 种固定颜色，没有纯黑**：浅色系 7 种（浅红/浅橙/浅黄/浅绿/浅蓝/浅紫/浅灰）+ 深色系 7 种。用户要求「整格涂黑」时**必须提前说明平台不支持纯黑**，给替代方案（深灰最接近 / 深红警示 / 仅删除线），让用户选，不要硬做或假装做成。

5. **用户编辑过的文档，改动前必须先 `docs +fetch` 对比当前版本**：用户明确要求「先读一下云文档再执行，不要把我删掉的东西又加回去了」。`--command overwrite` 全量重写会复活用户删掉的块/图例/行。正确顺序：fetch 现版本 → diff 出用户增删 → 增量更新（str_replace / block 操作）或严格复刻用户保留的结构。

## 往已有表格的单元格里填内容（多条目 / 有序列表）

给已经存在的表格逐格补数据（如「痛点」列、「选题」列，每格一个有序列表）。**绝对不要用 overwrite**：会复活用户删过的行、丢评论。

1. **取 block id**：`lark-cli docs +fetch --doc <url> --as user --detail with-ids --doc-format xml`
   表格里每个单元格的内容是独立块：`<td><p id="doxcn..."></p></td>`，**空单元格也有空 `<p id>`**——要替换的就是这个 `<p>` 的 id。
   注意 fetch 的参数是 `--doc`（没有 `--url`）。
   **按表头 `<th>` 的列名定位，不要按列索引写。** 用户会随时加列、改列名（例：把「痛点」改成「痛点场景」），沿用上一轮的 `<td>` 下标会把内容写进邻列。先解析表头列出列名与下标的映射，再取目标列。
2. **整格替换成列表**：`--command block_replace --block-id <p的id> --content '<ol><li>…</li><li>…</li></ol>'`
   表格单元格的父容器接受块级列表，`<ol>` 落地会渲染成飞书原生有序列表（不是手打的「1. 2.」纯文本）。已实测。
   **单元格里已有列表时**：`<ol>` 容器本身没有 id，每个 `<li>` 是独立 block。重写用闭区间 `--command block_replace --start-block-id <首li的id> --end-block-id <末li的id>`，不要试图对 `<ol>` 操作。
3. **批量**：把 `{block_id: [条目...]}` 写成 dict 循环调用，一格一次 `block_replace`。跨单元格（不同 `<td>`）不能合并成一次替换。
4. **先验一格再批量**：`--scope keyword --keyword <该格某条特色文字>` 只读回片段，确认出现 `<li seq-marker="1. ">`，再跑其余单元格。
5. **验证**：重 fetch 后按 `<tr>` 切行、逐行数 `<li>` 个数，核对「行数 = 表体行数」「每行条目数一致」；带样式的列还要数 `<del>` 个数并核对合计（例：12 格 × 6 条 = 72、灰线 37）。只抽查一格不够，易漏某格没写进去。
6. **必须核对非目标列未被误改**：把写完的表整段 fetch，确认「业务对接点」这类相邻列文字仍是原文。这是唯一能发现「写错列」的证据，按索引写入时尤其必查。

### 灰字 + 删除线（标「接不住 / 已废弃」的条目）

```xml
<li><span text-color="gray"><del>这条接不住</del></span></li>
```

- 文字颜色用 XML `text-color` **是生效的**（与背景色被丢弃不同）：fetch 回来是 `<del><span text-color="rgb(143,149,158)">…</span></del>`，即灰色 + 删除线同时落地。已实测。
- 色相只用 `red/orange/yellow/green/blue/purple/gray`；`light-*` 只能用于背景，别写成 `light-gray`、`grey`。
- 只包文字，不整格铺色；同一列里「可用项」保持原色，「不可用项」灰线，读者一眼分层。
- 条目要跨列对应另一列的编号（如选题对应痛点编号）时，**默认不要手工叠加 ① / ② / ③**：两侧条目等长、顺序一致时，`<ol>` 自增编号本身就能对应，叠两套编号会被要求删掉。只有跳过条目导致编号错位、且用户明确要逐条对账时才加，并在交付时说明代价。

坑：
- **改单元格里已有的文字用 `<p>` 的 block_replace，不要用 `str_replace`**：`str_replace --pattern` 是纯文本匹配，markdown 渲染里的 `| 值 |` 管道、`**` 之类都不是单元格真实文本，带符号的 pattern 一律匹配不上。拿到单元格内 `<p id="doxcn…">旧值</p>` 的 id 后 `--command block_replace --block-id <p的id> --content '<p>新值</p>'`。`str_replace` 无命中时返回 `ok:false` 但**同时带 `document.revision_id`**（说明文档可写、只是没匹配到），别当成权限/失败排查。
- 全局替换前先查同名子串：`病例对照` → `病例对照研究` 会把正文里已经写好的「匹配病例对照研究」改成「…研究研究」，只改单元格就必须走 block_replace。
- 替换后 block id 全部失效，第二轮改动必须重新 fetch，不能复用旧 id。
- 表格在 markdown 导出里有时是 `|` 管道表、有时是 `<table>` HTML（取决于表格复杂度）；**结构操作一律用 `--doc-format xml --detail with-ids`**，markdown 看不出 `<p id>`。
- 一个格塞多条往往比拆多行更合适（同一条记录的多条要点）；条目之间保持句式一致、每条带一个具体卡点，不要写成同义反复。

## 给表格加行（没有插行指令，只能重建整表）

`lark-cli docs` 没有 table-row 类命令。要把已有表从几行扩成几十行（如按功能清单逐项展开）：

1. 先 fetch 整表 XML，把要保留的原有行（含用户已经填过的列）原样抄进新 XML，不能只写新行。
2. 用 `colspan` 分组标题行切段：`<tr><td colspan="3"><p><b>【一】…</b></p></td></tr>`，长表不必另起多个表。
3. `--command block_replace --block-id <table 的 id> --content @table.xml` 一次替换整表（表 id 从 `<table id="...">` 取）。
4. 写完 fetch 数 `<tr>`：表头 + 保留行 + 分组行 + 新增行，对不上就是丢了行。

**长 XML 必须落文件**：内联进命令行会被命令解析器的长度硬限拦下（返回 BLOCKED，命令根本没执行）。把 XML 写进 CWD 的文件再传 `--content @./table.xml`，其他目录用 `@<绝对路径>`。

改表结构前把整篇 XML fetch 下来存本地备份，出问题可直接对照回滚。

## 图片分栏（grid + column + img）

把多张图并排成栏（素材区、对比图、图文卡），用 `<grid>` 包 `<column>`：

```xml
<grid><column width-ratio="0.333333"><img path="@/abs/a.png"/></column><column width-ratio="0.333333"><img path="@/abs/b.png"/></column><column width-ratio="0.333333"><img path="@/abs/c.png"/></column></grid>
```

各列 `width-ratio` 之和必须等于 1。落地实测可用：三图并排、等比缩放、不变形。

三个必踩的坑：

1. **`img path` 必须以 `@` 开头，绝对路径也得带**。写成 `path="/Users/.../a.png"` 会被校验直接拦下（`local image #1: path must start with @`），整条 `block_insert_after` 不执行。CWD 内用 `@./a.png`，其他目录用 `@/绝对路径.png`。
2. **`src="token"` 复制图片：文档流里可靠，`<grid>` 里不可靠**。直接按段落流写 `<img src="<file_token>"/>`（不带 column 包裹）可以原图内嵌、保序、无需下载重传，实测 9 篇文档 67 张图逐张核对全对；但**放进 `<column>` 时**会落成 `name="test.jpg"` 之类的别的图（命令照样 success、image block 数量也对）。所以：平铺段落流用 `src`，要并排分栏就改用 `path="@/abs/x.png"` 重新上传——上传成本远低于排查错图的成本。
   复制图片 token 的来源：`docs +fetch` 的 XML 里 `<img src="<token>">`，原文档同一张图的 token 可直接写进新文档。
3. **block-id 认错会静默插到错误位置**。相邻的两个 h2（比如「图片素材：」和紧跟着的「标题：」）长得一样但 id 完全不同，插错后命令照样返回 `ok: true`。插之前把 fetch 的 XML 从头读一遍，**按标题文字核对 id**，不要按「第几个标题」推测。

验证三件事，只看到 `"ok": true` 就交付必翻车（坑 2 就是 ok 但图是错的）：

- `<grid>` 是否落在目标标题之后、下一个标题之前
- `<column>` 个数与 `width-ratio` 之和是否为 1
- 每个 `<img name="...">` 的文件名是否与预期一致

**栏数按最终观看设备定，不要按电脑上好不好看定。** 飞书版心约 820px，三栏每栏约 270px；1080px 宽的知识卡片缩到 270px，手机上文字基本读不出来。以手机阅读为主就 2 栏或单栏，宁可不并排，并在交付时把这个取舍摆给用户选。

**一行放 N 栏**（用户常说「只有一行分栏，所有图按顺序排进去」）：一个 `<grid>` 里写 N 个 `<column>`，`width-ratio` 各取 `1/N`（7 栏写 `0.1429`），不要拆成多个 grid。此时每栏只有版心 1/N，图上的小字必然要放大才读得出——这是用户已知并接受的取舍，**交付时点一句就行，不要擅自改回两栏**。

### 替换 / 重传图片时的三个坑（都会静默出错）

1. **`block_replace` 换 `<img>` 必须显式带 `width` 和 `height`**。只给 `src`/`name`/`caption` 时，飞书保留旧块的显示尺寸（实测把 1080×1440 的封面落成 `512×512`，用户看到的是「怎么图片不是 3:4 了」——文件本身是对的）。固定写法：
   ```xml
   <img src="<file_token>" name="01_封面.png" caption="封面（1080×1440）" width="960" height="1280"/>
   ```
   写完回读，逐个核 `height/width` 的比值（3:4 应 ≈0.75），不要只看 `ok: true`。
2. **`<img name="...">` 就是用户从飞书下载时拿到的文件名**，不是内部备注。要交付一整套有序图片时，**序号写在最前**（`01_封面.png` / `02_第3页_要点.png`），保证下载下来按文件名排序＝正文顺序。用 `①`、`第3页` 这类开头会让排序失效。
3. **`block_delete` 的 start/end 范围跨过 `<grid>` 会 FAIL**（返回 error，整次不执行）。要删掉旧的一整节（标题 + 说明 + 若干分栏）：先删 `h2`～说明段这一段，再把**每个 `<grid>` 用各自的 block-id 单独删一次**，最后回读 `grid`/`img` 计数确认为 0。删完再插新的，顺序不要反。

## 工作流（写带样式的飞书表格）

1. `lark-cli docs +fetch --doc <url> --doc-format markdown` 拿当前版本，对比用户改动（用户删了什么就保持删除）。
2. 数据侧算好每行归属（粉丝量级档 / 分类），生成内容（结构、文字、链接、删除线）。
3. 结构用 `docs +update --command overwrite --doc-format xml/markdown`（XML 支持表格+删除线；颜色用不了）。
4. 需要背景色：原生 API 逐个 patch 单元格（先小样本验证枚举值生效）。
5. 更新后 fetch 验证删除线/内容确实落盘，并向用户如实说明哪些效果实现了、哪些是平台不支持（如纯黑）。

## 备注

- 链接单元格包删除线：`<a href="..."><del>url</del></a>`（嵌套顺序 a→del）。
- 判断「颜色到底有没有生效」不要看 XML 源码里写了什么，要看 API 读回的 block 结构（table_cell 是否为空、text_element_style 是否有 background_color）。
