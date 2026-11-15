# 语雀 API 细节与生态笔记（2026-08-14 调研）

## 官方 AI 生态仓库（github.com/yuque 组织）

| 仓库 | 定位 | 成熟度 |
|---|---|---|
| yuque-mcp-server | 官方 MCP（npm: `yuque-mcp`） | ★223，19 tools |
| yuque-ecosystem | 知识管理 Skills 分发仓（8 个：smart-search / smart-summary / reading-digest / note-refine / knowledge-connect / stale-detector / style-extract / daily-capture） | ★210 |
| yuque-plugin | Claude Code 插件（personal 4 skills + group 6 skills） | ★74 |
| yuque-chrome-extension | 浏览器插件 | ★546 |
| sdk / yuque-go / yuque-open-cli / yuque-cli | Node/Go SDK + CLI | 齐全 |

## MCP 19 工具面（capability-scope.md 官方契约）

- 用户/搜索：yuque_get_user、yuque_search（type 限 doc/repo）
- 知识库：list/get/create/update_book（update 支持 name/slug/description/public）
- 文档：list/get/create/update_doc（format 限 markdown/lake/html；update 的 markdown body 不能与 title/slug/public 同次调用，报错提示分两次）
- 目录：get/update_toc
- 小记：list/get/create/update_note
- 画板：get/create/update_resource（仅 mindmap/flowchart/architecturediagram；doc_id 和 url 二选一，resource_id 必须传 raw id 不带 board:// 前缀）

## ⚠️ 官方 Out of Scope（capability-scope.md 白纸黑字，契约测试锁定）

- 文档评论读写
- 附件上传或文件管理
- 权限、成员、协作设置管理
- 文档分段读取或增量 section update
- 除 board 以外的结构化资源类型

注意：yuque-plugin README 宣称 25 tools，但官方契约文档是 19——以契约文档为准（plugin 描述可能过时）。

## CLI 33 命令（yuque-open-cli，比 MCP 多出的）

- 删除：doc delete / book delete（带确认，脚本需 --yes）
- 版本历史：doc versions / doc version
- 成员：group members / group member set / group member remove
- 统计：stats group/members/books/docs
- 分页：--all 自动翻页；doc get 支持 --page/--page-size
- 输出：--json 全量 payload；稳定退出码 0成功/1API错/2用法错/3认证错/4未找到/5限流；限流自动退避重试
- auth：ping / auth status；配置 YUQUE_TOKEN / YUQUE_HOST（空间域名）/ YUQUE_TIMEOUT_MS

## 建库/文档常用命令速查

```bash
# 建库（public: 0私密 1公开 2 org-only；--enhanced-privacy 限制仅管理员）
yuque book create <login> --name <名> --slug <slug> --public 1 --description <描述>
# 建文档（--body 或 --body-file）
yuque doc create <login>/<slug> --title <名> --body <内容>
# 文档正文可含 markdown 表格/标题/列表
yuque doc get <login>/<slug>/<doc-slug>  # 读 markdown body
# 目录操作见 SKILL.md 核心工作流（toc update 全套）
```

## 权限细节

- public 字段：book get --json 返回 `public: 0|1|2`
- 「公开但不可被搜索」= public=1 + 网页端关「允许被搜索引擎收录」（`enable_search_engine` 字段存在于网页内嵌数据，但 API 不暴露）
- `max_doc_nologin_pv`：普通用户 500 次/文档，会员 null（无限制）——从官网 HTML 内嵌 JSON 挖出
- 用户侧限制（网页内嵌数据）：max_book_number 100（普通）/1500（会员）；max_single_image_size 10MB（普通）/50MB（会员）

## 认证与安全

- token 创建页：https://www.yuque.com/settings/tokens
- 鉴权头：`X-Auth-Token: <token>`（HTTP API）；MCP/CLI 用环境变量（见 SKILL.md 环境变量名坑）
- 用户偏好：token 存 `~/Documents/Hermes/APIs/` 文件夹的 rtf 文件，代理读取不打印明文
