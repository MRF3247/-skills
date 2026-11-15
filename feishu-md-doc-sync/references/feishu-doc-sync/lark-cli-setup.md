# lark-cli 安装与 Hermes 绑定（2026-08 实测）

## 安装
```shell
npm install -g @larksuite/cli   # → ~/.local/bin/lark-cli（node 装在 ~/.local 时无需 sudo）
npx -y skills add https://open.feishu.cn --skill -y   # 装 22 个官方 lark-* skills 到 ~/.agents/skills/ 并 symlink 到 Hermes
```
官方指南：https://open.feishu.cn/document/no_class/mcp-archive/feishu-cli-installation-guide.md
扩展能力指南：https://open.larkoffice.com/document/mcp_open_tools/feishu-cli-let-ai-actually-do-your-work-in-feishu.md
（open.feishu.cn 会被 web_extract 拦为 "private network"；用 curl 加浏览器 UA 直接抓 .md 原文）

## 凭证
写入 ~/.hermes/.env（chmod 600）：
```
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```
用户重视密钥安全：直接读写配置文件，不在聊天/终端回显明文；校验只回显前几位。

## Hermes 上下文绑定（关键坑）
- 检测到 hermes context（~/.hermes 存在）后，`lark-cli config init --new` 会被拒：
  "would create a parallel app and shadow the existing hermes binding"
- 正确路径：`lark-cli config bind --source hermes --identity <preset>`
  - 必须先让用户确认身份预设：`bot-only`（安全默认，不能碰个人日历/邮件/云盘）vs `user-default`（可代用户操作个人数据，功能全）
  - user-default 绑定输出会警告"AI 将以你的名义操作飞书"，勿把该机器人分享/拉入群聊
  - 绑定是一次性同步，Hermes 配置后续变更需重跑 config bind；同应用改身份策略用 `config strict-mode` 不需重绑
- 用户明确要独立应用才用 `config init --new --force-init`

## 设备流授权
- `lark-cli auth login --recommend`：stderr 打出 verification_url 后阻塞等待（最长约 10 分钟）
- 必须生成二维码：`lark-cli auth qrcode "<url>" --output qr.png`（PNG 输出路径限相对路径）或 `--ascii`
- 授权链接视为 opaque string 原样发给用户（勿 URL 编码/加空格/改标点；勿自己用 browser 打开——须在用户浏览器完成）
- 不要在同一轮展示 URL 后又阻塞执行 --device-code；每次重启会作废上一轮 device code，链接失效
- 标准姿势：后台跑 login → poll 拿 URL → 生成二维码 → 发给用户 → 用户完成后 auth status 验证
- 验证：`lark-cli auth status`（identity user / tokenStatus valid / offline_access 自动续期约一周）；`auth check` 查 scope

## 其他常用
- `lark-cli config show` / `auth logout` / `auth login --domain <domain>` 补权限
- 官方 vendor skill 随 CLI 版本匹配：`lark-cli skills read lark-doc`（操作前 MUST 读，勿从 --help 猜工作流）
- 删除云文档：`lark-cli drive +delete --file-token <token> --type docx --yes`（重复删报 "file has been delete." 属正常幂等）
- `--content` 支持 `@相对路径文件`（限 cwd 内）和 `-`（stdin），绕开 shell 转义
