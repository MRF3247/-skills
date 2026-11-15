<!-- 由 feishu-lark-cli 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/productivity/feishu-lark-cli -->

---
name: feishu-lark-cli
description: Use when installing/configuring the Feishu CLI (lark-cli).
---

# Feishu / Lark CLI (lark-cli)

官方文档（open.feishu.cn 会拦截 web_extract，用 curl + 浏览器 UA 抓取，存到工作目录）：
- 安装指南: https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md
- 完整能力指南: https://open.larkoffice.com/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu.md
- 开源仓库: https://github.com/larksuite/cli
- 本地已存的抓取副本: /Users/Jin/Documents/Hermes/feishu_cli_guide.md 和 feishu_cli_guide_full.md

## 安装
1. `npm install -g @larksuite/cli` → 二进制 `lark-cli`（node 在 ~/.local 时装到 ~/.local/bin/lark-cli）
2. `npx -y skills add https://open.feishu.cn --skill -y` → 一批 lark-* skills 装进 ~/.agents/skills/，自动 symlink 到 Hermes Agent；装完需重启 AI 工具才能完整加载
3. 验证: `command -v lark-cli` + `lark-cli --version`

## 在 Hermes 机器上配置（核心坑点）
- `lark-cli config init --new` 在 hermes 上下文里会被拒："would create a parallel app and shadow the existing hermes binding"——这是设计行为不是 bug。两条路：
  - 绑定到 Hermes 的飞书平台应用: `lark-cli config bind --source hermes --identity <preset>`（推荐）
  - 用户明确要独立应用: `lark-cli config init --new --force-init`
- bind 从 Hermes 环境读 FEISHU_APP_ID（~/.hermes/.env）。注意：插件目录存在（~/.hermes/hermes-agent/plugins/platforms/feishu/）≠ 凭证已配置——绑定前先检查 env / config.yaml / .env 里到底有没有 FEISHU_APP_ID/SECRET。
- bind 必须获得用户明确确认身份预设（CLI 拒绝静默绑定），用大白话给用户两个选项：
  - `bot-only`: 更安全默认。AI 只能以应用机器人身份发消息/建文档，碰不到个人日历/邮件/云盘
  - `user-default`: 冒充用户身份，可访问个人日程/邮件/妙记/私信，权限更大
  - 用户拿不准就默认 bot-only。同一应用后续只改身份策略用 `lark-cli config strict-mode`，不用重新 bind
- 凭证写入: 追加到 ~/.hermes/.env（FEISHU_APP_ID / FEISHU_APP_SECRET），chmod 600，printf 追加。用户重视密钥安全：写配置文件，绝不回显明文（连截断回显也尽量避免）。

## 登录授权（device flow）
- `lark-cli auth login --recommend` 把 verification_url 打到 stderr，然后阻塞最多约 10 分钟。用 background=true 跑，poll 一次提取 URL，原样交给用户。
- URL 规则: verification_url 是不可修改的 opaque string——原样发送，不做任何 URL 编码/解码、不加空格标点。
- 绝不用浏览器工具代开授权链接——授权必须在用户自己的浏览器里完成。
- 绝不要短 timeout 反复重试/重启该命令——每次重启会作废上一轮 device code，用户手里的链接就失效。
- 非阻塞替代: `lark-cli auth login --no-wait --json` 拿 device_code + verification_url，把 URL 发给用户并结束本轮；用户回复已授权后，再 `lark-cli auth login --device-code <code>` 续上轮询。不要在同一轮展示 URL 后立刻阻塞执行 --device-code。
- 二维码: `lark-cli auth qrcode <url> --output <name>.png`（PNG 路径必须相对当前目录）或 `--ascii` 输出到 stdout。CLI 平台：ASCII 二维码是终端里唯一能直接展示的形式；PNG 存工作目录并告诉用户路径（CLI 上 MEDIA: 标签不生效）。
- 验证: `lark-cli auth status`、`lark-cli auth check`、`lark-cli auth scopes`、`lark-cli config show`。

## 用 lark-cli 建批量内容清单文档（实测）

`lark-cli docs +create --title "..." --doc-format markdown --content @/tmp/xx.md --parent-position my_library`
- `--content @file` 读文件，避免 shell 转义损坏；`--parent-position my_library` 放个人云空间；成功返回 `data.document.url` 直接给用户
- **本地图片可用**（实测 17 张一次成功）：markdown 里写 `![alt](@./images/x.png)`，路径必须是 **cwd 下的相对路径**，所以先 `cd` 到含 `images/` 的目录再跑命令。创建后返回的 `data.document.new_blocks` 里 image 块数量应与图片数一致（可据此验证没被静默丢弃）。
- **放进知识库**：`--parent-token <wiki 父节点 node_token>` 可直接把新文档建为 wiki 子节点（区别于 `--parent-position my_library`）。建完用 `lark-cli wiki +node-get --node-token <obj_token>` 复核 parent_node_token/space_id。
- **核对写入结果**：`lark-cli docs +fetch --doc <id> --doc-format markdown` 后数标题层级（`^### `）、表格分隔行（`^\|[-| ]+\|$`）、链接次数，比肉眼翻页可靠。
- **外链图片会被静默丢弃**：飞书服务器拉不到 ytimg/YouTube 等外链图，markdown 里的 `![](url)` 消失（degrade_code=2108 warning）——需要图就本地下载后用 `+media-insert` 逐张插，或只留文字+链接
- 验证内容完整性：`lark-cli docs +fetch --doc <id>`（用 flag 不用位置参数），数关键字出现次数

## 往飞书文档里写大表格（踩过的坑）
- **单表单元格上限 2000**（`DOC_TABLE_CELL_LIMIT`，报错 actual/limit）：164 行 × 14 列 = 2310 格直接报错。对策：按 50–55 行切片，每片一个小节 + 完整表头（55×14=770 格安全）。
- **markdown 表格的行必须连续**：表头/分隔行/数据行之间不能有空行，否则整张表会被当成一堆普通段落插进去（只有文字没表格）。做法：把整表拼成一个字符串（行间单个 `\n`），再和其他块用空行分隔。
- **单元格内容里的 `|` 必须转义为 `\|`**（包括 `[链接文字](url)` 里的文字）——漏了会导致该行多出一格、后面所有列错位、尾列被挤掉。写完先自检：按 `(?<!\\)\|` 切分，每行格数应等于表头列数。
- 单元格内换行用 `<br/>`（实测可用）；单元格内的 `[文字](url)` 超链接可用，但**链接文字里不要再套 `**粗体**`**（会被拆成 3 个链接）。
- **`overwrite` 适合“把自己刚建坏的文档推倒重来”**（保留原链接/节点位置），比删了重建省事。

## 改已有文档里的表格（实测：整表转置）
1. `docs +fetch --doc <id> --detail with-ids` → 从返回里取 `<table id="...">` 的 block id（markdown 导出会把复杂表格原样输出成 HTML，可当源数据）。
2. 用 bs4 解析 → 单元格里可能是 `<p>` 纯文本、`<p><a href>` 或 `<ul><li><a>` 列表；转换时：去掉所有 `id=`、文本转义 `& < >`、href 里的 `&` 转回 `&amp;`、空段落保留为 `<p></p>`。
3. `docs +update --doc <id> --command block_replace --block-id <table block id> --content @file.xml`（xml 格式）；表头行用 `<thead><tr><th>`，其余 `<tbody><tr><td>`，列宽用紧跟在 `<table>` 后的 `<colgroup><col width=".."/>`。
4. 先用 `--dry-run` 看 body，再执行；改完重新 fetch，数 `rows × cols`、`<a href=` 数量与原文一致才算成功（同一 block 的多处改动合并成一次 block_replace，旧 block id 会失效）。
5. 坑：原表末尾常带整行空白 → 转置后会变整列空白，先删；`--content @file` 只收 cwd 下相对路径。

## 命令约定
- `lark-cli <domain> +shortcut` — 高层任务快捷命令，优先用（如 `lark-cli calendar +agenda`）
- `lark-cli schema <service.resource.method>` — 调用前查参数/类型/scope/示例
- `lark-cli api <METHOD> <path>` — 原始逃生口，任意 HTTP 路径
- `--jq <expr>` 过滤 JSON 输出；`--dry-run` 预览请求不真正执行
- 每个命令 --help 标注风险等级 read | write | high-risk-write；high-risk-write 需用户确认后加 `--yes`
- 业务域: im(消息群组), docs(云文档), drive(云空间), sheets(电子表格), base(多维表格), calendar(日历), minutes(妙记/会议纪要), mail(邮箱), task(任务), wiki(知识库), slides(幻灯片), board(画板), okr, approval(审批), attendance(考勤), contact(通讯录), mindnotes, note
- 多应用: `lark-cli config` 子命令管理（bind/remove/show/strict-mode/default-as/risk-control/keychain-downgrade）
