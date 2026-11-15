---
name: yuque-docs
description: "Use when 操作语雀：建知识库/文档/目录、迁移内容到语雀、设链接免登录访问。"
version: 1.0.0
metadata:
  hermes:
    tags: [yuque, 语雀, knowledge-base, mcp, cli, toc]
    category: productivity
---

# 语雀知识库操作（yuque-docs）

Use when 用户在语雀（yuque.com）建知识库/文档/目录、把本地内容迁到语雀、或设置「同事点链接免登录访问」类权限。两条通道：MCP（AI 交互）+ CLI（脚本/批量），**建议双装**。

## 接入状态

- **MCP 通道（首选，实测可用）**：工具名 `mcp__yuque__yuque_*`（19 tools：user/search/books/docs/toc/notes/resources）。参数名不统一，别凭记忆填：`yuque_list_books` 要 `login`；`yuque_get_toc`/`yuque_update_toc`/`yuque_create_doc`/`yuque_get_doc` 要 `repo_id`（namespace `liink/yishi` 或数字 id 都行）。漏参数时工具会回显 schema，照补一次即可
- **账号与主库**：`login = liink`（显示名「不卷」），主库「医时知识库」= `liink/yishi`（id 82378239）。不确定 login 先 `yuque_get_user`
- **CLI 通道（非必需）**：`yuque-open-cli`，bin 在 `~/.local/bin/yuque`。**先 `command -v yuque` 确认存在再写 CLI 命令**；不在就直接用 MCP，别花时间找/装 CLI——日常建文档挂目录 MCP 全覆盖，CLI 只多出删除、版本历史、成员、统计
- **token**：`~/Documents/Hermes/APIs/语雀 API.rtf`（用户所有 API token 统一放该文件夹）；读取用 python 正则去 RTF 控制符后 `re.findall(r'[a-zA-Z0-9_\-]{20,}', text)[0]`，**全程不打印明文**
- ⚠️ **环境变量名坑**：MCP 读 `YUQUE_PERSONAL_TOKEN`；CLI 读 `YUQUE_TOKEN`。两个名字不一样，配置时别混
- ⚠️ **MCP 需 token 才能握手**（启动参数非运行时参数）；CLI 交互版 `yuque-cli` 与脚本版 `yuque-open-cli` 是不同 npm 包，装后者才有 33 命令
- CLI 独有 MCP 没有的能力：删除（doc/book delete）、版本历史（doc versions）、成员管理（group members）、统计（stats）、`--json`+稳定退出码+`--all` 翻页
- 能力边界（共用语雀 OpenAPI）：**无附件上传、无权限管理、无分段编辑**——图片/表格精调/文档级权限别指望语雀 API

## 核心工作流 A：MCP 建文档 + 挂进目录 + 做成子文档（实测链路）

1. **看现状**：`yuque_get_toc(repo_id="liink/yishi")` → 每个节点带 `uuid`/`doc_id`/`level`。先读懂已有分区再决定放哪，别硬塞进不相关目录
2. **建文档**：`yuque_create_doc(repo_id, title, body, format="markdown")` → 返回 `id`/`slug`。URL = `https://www.yuque.com/<login>/<book-slug>/<doc-slug>`
   - ⚠️ **`create_doc` 没有 parent 参数**，新文档会自动以 `level 0` 追加到 TOC **根级**——不移动就堆在库根目录
3. **建分区标题节点**（纯分组、无文档页）：
   `yuque_update_toc(toc_data='{"action":"appendNode","action_mode":"child","target_uuid":"","type":"TITLE","title":"4. 医学资讯译文"}')`
   - `target_uuid` 空串 = 根级；`action_mode` 必填（child/sibling）
4. **把已建文档挪进分区**：同一条 `appendNode`，**用 `node_uuid` 代替 `type`**：
   `{"action":"appendNode","action_mode":"child","target_uuid":"<分区uuid>","node_uuid":"<文档节点uuid>"}`
5. **做子文档**：再套一次 —— `target_uuid` = 父文档 uuid，`node_uuid` = 子文档 uuid。TOC 里该节点 `level` +1 即生效，语雀侧显示为父文档的子文档
6. **核对**：每次 `update_toc` 都回传完整新 TOC，看返回值里的 `level` 层级即可，不用再 get 一次；再 `yuque_get_doc` 抽查标题/正文

> 医时知识库（liink/yishi）现有顶层分区：1. 产品资料 / 2. 内容增长 / 3. 视觉参考 / **4. 医学资讯译文**。外文报道中译一律进「4. 医学资讯译文」：父文档=中文译文，子文档=英文原文。文档骨架见 `references/translation-doc-template.md`。

## 核心工作流 B：CLI 建库 + TOC 骨架（CLI 可用时）

1. **建库**：`yuque book create <login> --name <名> --slug <slug> --public 1 --description <描述>` → 返回 book id
   - login 查 `yuque auth status`（本机 = `liink`）
2. **建分区文档**：`yuque doc create <login>/<book-slug> --title <名> --body <内容>` → 返回 doc id + doc slug
   - 骨架分区先建「00-索引」等真实文档（含目录结构说明），其余用 TITLE 分组节点
3. **建 TITLE 分组节点**（如 01-素材库 / 02-选题分析）：
   `yuque toc update <book> --action appendNode --action-mode child --type TITLE --title <名>`
   - ⚠️ **`--action-mode` 必填**（child/sibling），缺了报 `missing action_mode (the request parameters were rejected by the Yuque API)`
4. **挂子节点**（如 01-素材库 下挂 B站/小红书/抖音/公众号/时效性素材）：
   `yuque toc update <book> --action appendNode --action-mode child --target-uuid <父节点uuid> --type TITLE --title <子名>`
   - 父节点 uuid 用 `yuque toc get <book> --json` 拿（TITLE 节点的 `uuid` 字段）
5. **挂 DOC 节点**（把已建文档挂进目录）：
   `yuque toc update <book> --action appendNode --action-mode child --type DOC --title <名> --doc-ids <doc id>`
6. **验证**：`yuque toc get <book>` 看树形输出（缩进=层级）；`yuque book get <book> --json` 看 public/items_count

> 完成的骨架结构（医时知识库，2026-08-14）：01-素材库（B站/小红书/抖音/公众号/时效性素材）+ 02-选题分析 用 TITLE 节点；00-索引/03-产品资料/04-内容增长/05-视觉参考/99-归档 用 DOC 节点。TITLE 节点是纯分组（无文档页），DOC 节点指向真实文档。

## 权限模型（用户需求「同事免登录访问 + 不对全网公开」）

| public 值 | 语义 | 同事免登录 |
|---|---|---|
| 0 | 私密 | ❌ |
| **1** | **公开** | ✅ 链接直达免登录 |
| 2 | org-only（**不是**「公开但不可被搜索」） | ❌ |

- **正确组合**：`public=1` + 语雀网页端关闭「允许被搜索引擎收录」开关（**该开关 API/CLI 不暴露**，需 UI 手动关一次，整库生效）= 链接可访问 + 全网搜不到
- ⚠️ **`max_doc_nologin_pv` 免登录访问上限**：普通用户单文档 **500 PV 封顶**，**会员无限制**（从官网 HTML 内嵌数据挖出）——用户已充会员，此方案成立；判断「同事免登录」可行性先确认会员身份
- 验证免登录可见性：`curl -sL -A "<浏览器UA>" -H "Accept: text/html" -H "Accept-Language: zh-CN,zh;q=0.9" <文档URL>` → HTTP 200 + 标题含文档名 + 无 passport/login = ✅
  - ⚠️ curl 默认 UA 会 404（反爬）；API 层 /api/v2 无鉴权一律 401，别用 API 验证网页可见性
- 命令：`yuque book create/update <book> --public <0|1|2>`；测试库用完 `yuque doc delete` / `yuque book delete`（CLI 有删除，MCP 没有）

## 坑

- 知识库刚创建时 slug 路由可能未生效（无登录 curl 404），先往库里写一篇文档再测文档 URL
- `toc get` 不带 --json 只显示标题树（无 uuid）；要 uuid 必须 `--json`
- MCP 工具重启 Hermes 会话才注入（无热加载）
- 顶层 TITLE 分区节点总是**追加在末尾**，顺序天然正确（3.x 之后接 4.x），不用手工排序
- 建完文档立刻看 TOC：不在 TOC 里的推断都是错的；靠 `level` 判断父子，别靠缩进猜
- 「医时知识库」为公开 + **密码保护**：curl 验证会拿到 HTTP 200 的「输入密码 · 语雀」页——这**不是**文档不存在或建失败，是库的访问设置（要验内容用 `yuque_get_doc`）
- 语雀 API **不能传图片/附件**（无上传接口），原文配图搬不过来：先在正文标注「图：xxx」，需要真图时另想上传通道或用外链
- 语雀全文/API 细节（生态仓库清单、19 工具面、Out of Scope 原文）见 `references/yuque-api-notes.md`

## 相关

- 平台选型对比（腾讯/语雀/飞书）与推荐逻辑：tencent-docs-mcp skill 的 `references/document-platform-selection.md`
- Obsidian 侧迁移源：`obsidian-vault-organization` skill
