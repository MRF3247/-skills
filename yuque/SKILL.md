---
name: yuque
description: "Use when 操作语雀知识库：建库、TOC目录、批量上传本地md。"
version: 1.0.0
metadata:
  hermes:
    tags: [yuque, 语雀, knowledge-base, toc, doc-sync, obsidian-migration]
---

# 语雀知识库操作（yuque CLI + MCP）

Use when 用户要求在语雀建知识库/目录结构、把本地 md（Obsidian 笔记/会议纪要/产品资料）批量上传到语雀、或迁移内容到语雀。双通道：**MCP（yuque-mcp，19 tools）管 AI 交互、CLI（yuque-open-cli，33 commands）管批量/脚本**。

## 环境（2026-08-14 实测）

- CLI：`~/.local/bin/yuque`（npm 全局 `yuque-open-cli`；交互版 `yuque-cli` 是另一个包，别装错）。PATH 常缺 `~/.local/bin` → 全路径或 `export PATH="$HOME/.local/bin:$PATH"`
- MCP：Hermes `mcp_servers.yuque` stdio（command=`/Users/Jin/.hermes/node/bin/npx`, args=`["-y","yuque-mcp"]`），工具名 `mcp_yuque_*`，**重启会话才注入**
- **语雀官方 AI 生态仓库核实（2026-08-14，用户两次要求查）**：`yuque/yuque-skills`（已归档→合并进 `yuque/yuque-plugin`）、`yuque/yuque-ecosystem`（Skills 分发仓）、`yuque/yuque-plugin`（Claude Code 插件，personal 4 skills + group 6 skills）。**全部是文档型工作流**（smart-search / meeting-notes / weekly-report / tech-design / onboarding / knowledge-report），底层工具全是 `yuque_search/get_doc/list_repos/list_docs/create_doc`，**无 sheet 操作**——plugin README 宣称「25 Tools」但就是 yuque-mcp 的 19 个 + skill 编排，能力边界不变。结论：语雀官方所有 AI 通道（MCP/CLI/skills/plugin）都碰不到数据表
- **MCP 与 CLI 环境变量名不同**：MCP 读 `YUQUE_PERSONAL_TOKEN`，CLI 读 `YUQUE_TOKEN`——配置别混
- token：`~/Documents/Hermes/APIs/语雀 API.rtf`（用户所有 API token 统一放该文件夹）；读取用 python 正则 `[a-zA-Z0-9_\-]{20,}` 提取，**全程不打印明文**
- 用户账号 `liink`（不卷），已充会员（免登录 PV 无上限、API 基础能力全开）
- ⚠️ **知识库 slug 双别名**：医时知识库建库 slug=`yishi-kb`，但用户分享/访问链接用 `yishi`（`https://www.yuque.com/liink/yishi/<doc>`）——实测两个 namespace（`liink/yishi-kb` 与 `liink/yishi`）都能解析到同一文档，API 对别名容错。用户贴链接时优先用 `yishi` 形态
- 权限模型与「同事免登录访问」方案见 tencent-docs-mcp references/document-platform-selection.md

## 核心工作流：建知识库 + TOC 目录骨架

### 1. 建知识库
```bash
yuque book create liink --name <名> --slug <slug> --public 1 --description <说明>
yuque book get liink/<slug> --json   # 确认 public 字段
```
- `--public`：0=私密 / 1=公开 / 2=org-only。办公库默认 public=1（链接免登录访问）
- 建完记得提醒用户：网页端关闭「允许被搜索引擎收录」（API/CLI 不暴露此开关）

### 2. 建 TOC 目录骨架（2026-08-14 实测核心）
TOC 节点类型：`TITLE`（分组，无文档，点开空）、`DOC`（挂文档）、`LINK`（外链）。

```bash
# 顶层分组（根下）
yuque toc update liink/<slug> --action appendNode --action-mode child --type TITLE --title "1. 产品资料"
# 二级挂到某分组下（先拿父节点 uuid）
yuque toc get liink/<slug> --json     # 返回每节点 uuid/title/type/parent_uuid
yuque toc update liink/<slug> --action appendNode --action-mode child --target-uuid <父uuid> --type TITLE --title "a. 产品介绍"
```
- ⚠️ **`--action-mode` 必填**（child/sibling），缺了报 `missing action_mode`
- 挂 DOC 节点：`--type DOC --doc-ids <id> --title <标题>`（doc 先创建拿 id）
- 目录编号风格用户偏好：顶层 `1. 2. 3.`，二级 `a. b.`，三级 `ⅰ. ⅱ.`（参考分组下用罗马数字）

### 3. 批量上传本地 md + 挂载（2026-08-14 实测）
```bash
yuque doc create liink/<slug> --title <标题> --body-file <file.md>   # 从文件读正文，避免 shell 转义
# 输出格式: ✓ Created doc liink/<slug>/<doc-slug> (id <doc_id>): <标题> —— 用正则提取 doc_id
yuque toc update liink/<slug> --action appendNode --action-mode child --target-uuid <分组uuid> --type DOC --title <标题> --doc-ids <doc_id>
```
- 循环里「创建 → 提取 doc_id → 挂载」三步连做，输出 `✓ Toc updated (N nodes)` 即挂载成功
- 验证：`yuque toc get liink/<slug>` 看层级缩进 + slug 是否正确归属

### 4. 清理/删除
- `yuque doc delete liink/<slug> <doc-slug> --yes`（删文档时 TOC 节点自动清理，无需手动 removeNode）
- `yuque book delete liink/<slug> --yes`（删整个库）
- `toc update --action removeNode --action-mode sibling --node-uuid <uuid>` 删单节点（实测**报 `invalid action` 但实际可能已删**——删除类 TOC 操作后必须 `toc get` 回读确认，别盲信报错；文档删除后节点已自动清，此命令少用）

### 5. 批量账号/清单 → 索引表格文档（2026-08-14 实测）
对标账号库这类「N 个 md 文件 → 一个索引表格」的通用配方：
1. 读每个账号文件的 frontmatter（粉丝数/UID/稿件总数字段）+ 文件名（去编号前缀 `^\d+-`、去 `（粉丝xx万）` 后缀得账号名）
2. 按粉丝量降序排序（粉丝数解析：`re.search(r'([\d.]+)万', s)`）
3. 生成 markdown 表格：`| # | 账号 | 粉丝 | 稿件数 | UID | 主页链接 |`（UID 拼 `https://space.bilibili.com/<uid>/video` 可点击）
4. 分组两张表（正式分析区 / 候选不分析区），文档开头注明数据快照日期与来源路径
5. `doc create --body-file` 上传 + `toc update --type DOC` 挂到对应参考分组

## Obsidian md → 语雀清洗配方（2026-08-14 实测，产品资料 4 篇）

上传前对**临时副本**做清洗（源文件不动），正则顺序：
1. **frontmatter**：`---...---` 整体删（`c.split("---", 2)[2]`）
2. **wikilinks** `[[名称]]` / `[[名|别名]]` → 纯文本名称（`re.sub(r'\[\[([^\]|]+)(\|[^\]]+)?\]\]', r'\1', c)`）
3. **callout → 语雀高亮块 `:::{类型}`**（2026-08-14 实测修正，用户反馈「导入后很乱」）：
   - Obsidian `> [!info] 标题` → `:::{info}` + 首行 `**标题**` + 正文（`> xxx` 行去 `>` 前缀）+ `:::` 收尾
   - ⚠️ **不要转成 `**[info] 标题**` 加粗字面量**——第一版这么转，用户在语雀里看到的是 `[info]` 字面文本，明确否掉
   - ⚠️ `<Callout type="info">` HTML 语法也无效（实测退化成普通段落）
   - 唯一有效语法 = `:::{类型}` ... `:::`，实测渲染成 `<div data-type="info" class="ne-alert">` 原生高亮块组件
   - 类型映射：info/note/abstract/summary→info；tip/hint/important→tip；success/check/done→success；question/help/faq→question；warning/caution/attention→warning；failure/danger/error→danger；example→example；quote/cite→quote
4. **本地相对路径图片** `![图](/document/0-1.1.png)` → `〔图片：文件名〕` 文字占位（语雀 markdown API 无法解析本地路径；语雀 OpenAPI 无附件上传端点，图进不去）
5. 压缩多余空行（`\n{4,}` → `\n\n\n`）
6. **更新已有文档**：`yuque doc update liink/<slug> <doc-slug> --body-file <清洗后文件>`——保持 doc id 与挂载位置不变，直接换正文；验证用 `yuque_get_doc(format="html")` 看 body_html 里 `ne-alert` 是否出现
7. 表格用标准 markdown 表格即可（语雀自适应宽度，无腾讯文档那种撑爆问题）
8. **⚠️ 表格必须有分隔行 + 无行首缩进，否则竖线全部裸露**（2026-08-14 用户反馈「排版很乱、很多竖线分割」实测修复）：
   - 症状：语雀里表格行变成纯文本，`|` 竖线全显示出来；根因 = markdown 表格**缺 `|---|---|` 分隔行**——Obsidian 能容错渲染缺分隔行的表格，**语雀不认，按普通段落渲染**
   - 网页抓取来的 md（帮助文档/官网抓取类）常同时带**行首 4+ 空格缩进**（触发语雀代码块，等宽字体更乱）
   - 修复配方：① 全部行去行首缩进 `re.sub(r'^[ \t]+', '', l)`（缩进去掉后被拆散的表头会重新接上）；② 重扫连续 `|` 块，每块首行=表头，按表头列数补分隔行 `'|' + '---|' * ncols`；③ 校验：每块第 2 行应为分隔行，非表格竖线行=0，缩进行=0
   - 验证：`yuque_get_doc(format="html")` 检查 body_html 里 `html.count('ne-table')` = 期望表格数、裸竖线文本 = 0
   - ⚠️ 上传前用脚本批量检查所有待传 md：孤立表头行数（`|` 开头但下一行非分隔行）>0 即有此病

## 陷阱

- **⚠️ 数据表/工作表类型完全无法通过 API 操作**（2026-08-14 深度实测，用户建表验证）：
  - **创建**：`POST /repos/:namespace/docs` 传 `type: "sheet"` 返回 422 `"要求是 Doc, HtmlDoc 其中的一个"`——OpenAPI 只支持 Doc/HtmlDoc
  - **读取已存在的数据表**：`get_doc` 能拿到元信息（`type: Sheet`, `format: lakesheet`）但 body 为空；`yuque_search(type=doc)` 搜不到
  - **写入**：无任何端点。前端逆向确认 lakesheet 是 SpreadJS 私有格式，数据加载走按需 chunk（`p__editor__routers__sheet` 模块 91452），接口未公开；CLI 无 sheet 命令；MCP 源码无 sheet 模块（只有 doc/note/resource/toc/search/user）
  - **用户要「表格不是文档」时的唯一路径**：生成本地 CSV（编码 `utf-8-sig` 带 BOM 防乱码；⚠️ 导出前把单元格内 `\n`/`\r` 替换成空格，否则导入器可能把多行单元格误判为行分隔）→ **放桌面交付用户**（用户偏好：`~/Desktop/<名>.csv` 自己上传）→ 指导网页端「+ 新建 → 数据表 → 导入 CSV」→ 数据表自动出现在当前目录节点。API 侧最多只能建 markdown 表格文档兜底（1300 行级体验差，先问用户）
  - ⚠️ 给用户解释时要讲清：这是平台能力边界（OpenAPI 未开放 Sheet 类型），不是「没找到工具」
- **语雀 MCP/CLI 都没有附件上传**（OpenAPI 层无该端点）——文档里的图只能外链 URL 或文字占位
- MCP 无删除工具（19 tools 无 delete），删除一律走 CLI
- `yuque doc create` 的 `--body` 直接传长文易 shell 转义问题 → 用 `--body-file`
- 知识库刚创建时 slug 路由可能未生效（网页 404），先建文档再测
- 大量调用会触发 429（CLI 自动退避重试，MCP 靠等）
- 语雀网页对 curl 默认 UA 返回 404（反爬），验证免登录访问必须带浏览器 UA + Accept 头（见选型 reference）

## 稿件清单子文档配方（2026-08-14 实测，100 账号 × 47k 条）

「索引父文档 + 每账号一个稿件子文档」是账号库稿件列表的标准挂法（TOC 支持 DOC 挂子 DOC）：
1. 解析账号 md：frontmatter（粉丝数/UID/稿件总数）+ 表格行（`|` 开头且非分隔线，去表头/分隔线后为数据行）
2. **12 列原始表 → 7 列精简**：`播放|点赞|收藏|标题|时长|发布|链接`——删掉全空的「逐字稿/选题分析」列（值全是 `—`）、合并互动数据列（投币/转发/评论），否则语雀表格被挤爆（和腾讯文档一个教训）；链接列提取 URL：`re.search(r'\((https?://[^)]+)\)', cell)`
3. 子文档命名 `NN-账号名-稿件清单`，正文 = H1 账号名 + `> UID/稿件总数/排序` 引用行 + `## 全部稿件清单` + 表格
4. 挂载链：先建索引父文档 → 挂到参考分组（TITLE）下 → 每账号稿件文档挂到**父文档**（DOC）下做子节点（`--target-uuid <父文档uuid>`）。父文档 uuid 从 `toc get --json` 里按 `doc_id` 匹配找（⚠️ doc_id 字段是字符串，比较前先 str()；`toc get --json` 返回的节点 `doc_id` 在 json 里可能为 `""` 空串——TITLE 节点没有 doc_id）
5. 数据完整性：frontmatter 说 424 条实际解析 423 条常见（`—` 过滤误伤/表头重复），批量前先核对总数再动手

## 相关

- **最终走向（2026-08-14）**：因数据表无 API 读写，用户整体转**飞书**。曾把内容复制到「B站内容 副本」Base 当主库，但**撞上 Base 文档块 10 个硬上限 + 行数限制（基础版单表 2000 行）后放弃**，整个副本已删除——最终方案 = 文档留飞书 Wiki 树、数据（账号索引 1298 + 稿件清单 423）留 Wiki 下原「B站对标账号索引」Base（`Ffagbvj5paLgvrsCi7CcIKsCn3g`）。飞书实操见 `feishu-cli-workflows`（含 wiki-base-migration + sheets + 硬限制 reference）
- 平台选型/权限模型/免登录验证：tencent-docs-mcp references/document-platform-selection.md
- 腾讯文档工作流：tencent-docs-mcp；飞书：feishu-cli-workflows
