---
name: free-site-publishing
description: Use when 把本机网站发到公网（免费、不买域名）：快照推 Pages。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [publishing, github-pages, cloudflared, tunnel, static-snapshot, launchd]
    related_skills: [medhot-medical-news-site, thinkhot-thought-news-site, daily-scraping-automation]
---

# 把本机网站发到公网（免费、不买域名）

## When to Use

- 用户有一个跑在本机的站（Flask / SSR 前端 / 静态目录），想「发给别人看 / 挂到网上」
- 用户问「必须买域名吗」「有什么简便手段」「能不能今天就用上」
- 要给已有的站配自动更新（定时 / 每次改动后）

## 先定路线（别一上来就开挖）

用户在这个课题上的取向很固定：**免费、不买域名、地址固定、能自动更新就行，不强求实时**。按这个取向的默认推荐是「静态快照推 GitHub Pages」，其次才是真·实时方案。

| 路线 | 何时选 | 代价（要如实说） |
|---|---|---|
| **静态快照 → GitHub Pages 子路径**（默认） | 内容小时/天级更新即可；要固定地址、要能给别人长期用 | 不是实时（粒度=推送频率）；生成它的机器要开机；没抓到的深链接 404 |
| Cloudflare 快速隧道 `cloudflared tunnel --url` | 现场演示、只看一眼、要真·实时且不介意地址变 | 地址每次重启就换；页面**零可用性保证**，到边缘的链路一断整站打不开；`/admin` 一起暴露 |
| Tailscale Funnel（`*.ts.net`） | 要固定地址 + 真·实时，又不买域名 | 要装并登录 Tailscale；同样依赖那台机器在线，且要网络能连 Tailscale |
| 小 VPS + Caddy | 要 7×24 稳、与个人机器解耦 | 每月几美元起；要维护 |

不要在没有验证的情况下对用户说「更新是自动的、地址稳定」——隧道方案两样都不成立。

## 静态快照 → GitHub Pages：做法

前提：目标仓库是**公开**的（私有仓库的 Pages 要付费），且本机能 `ssh -T git@github.com` 认证成功（`gh` 没装也能推，用 SSH 就够）。

### 1. 定抓取范围

SSR / 服务端渲染的站，HTML 本身就是成品，直接抓页面即可（不需要 Puppeteer）。范围要**有界**：

- 固定页：首页、列表页、关于类页面（各自的路由清单）
- 详情页：从榜单页 / 首页 / 列表页里挖链接，每类限条数（例：榜单事件页全要 + 首页 25 条 + 日报最近 6 期）
- 不管客户端路由（React Router / Next 的 `.data` 单次请求）→ 「点进去是 404」是可接受后果，但要**提前告诉用户**

用 `scripts/snapshot.py`（本技能自带，已在 SSR（React Router v7）站验证）：

```bash
python3 scripts/snapshot.py --base http://127.0.0.1:3100 --prefix /medhot --out /tmp/site-medhot
# --prefix 必须等于 Pages 子路径（项目站 = /<repo 名>）
```

要**全量**（用户说「把本地的数据都推上去」）别靠挖链接，用站自己的清单：

```bash
python3 scripts/snapshot.py --base http://127.0.0.1:3100 --prefix /medhot --out /tmp/site-medhot --sitemap --deep-all
```

- `--sitemap`：`/sitemap.xml` 里的 `<loc>` 就是站点自己声明的可索引页（实测 MedHOT 1107 条）。注意 sitemap 常被前端截断：MedHOT 只列 489 个条目，而列表其实有 2000 条
- `--deep-all`：读列表页 SSR 载荷里的 `pageCount` 自动翻页，把分页里出现的条目页也挖下来（MedHOT → 2907 页）
- 查询型 URL 要**映射成目录**，否则静态站上 `/all?page=3` 只会回到第一页：`/all?page=3` → `/all/p3/`、`/all?category=x` → `/all/c/x/`、`/?category=x` → `/c/x/`（脚本内置 `route_out()`，页面对应链接会自动改写）
- 全量体积要算清：MedHOT 2907 页 = 273MB，其中 **135MB 是每个条目页的 og 分享预览图**（`og/items/*.png`），正文 HTML 只 118MB。要砍体积，最先砍它（正文/导航完全不受影响，只是分享链接没预览图）

### 2. 推之前必须先本地验一遍

把产物放进「以 prefix 命名的父目录」再用静态服务器打开 —— 这样才暴露子路径改写错误（直接当根目录打开会把 bug 藏起来）：

```bash
mkdir -p /tmp/pagesroot && cp -r /tmp/site-medhot /tmp/pagesroot/medhot
cd /tmp/pagesroot && python3 -m http.server 8897 --bind 127.0.0.1
# 浏览器打开 http://127.0.0.1:8897/medhot/ —— 看渲染/图片/样式/文案，别只看 HTTP 200
```

### 3. 发布：独立 git 仓库 + 孤儿分支 + force push

不要把快照写进代码仓库的工作区。用一个状态目录自己的 git 仓库（避免污染代码仓的分支与工作区），并**保留它的 `.git`** —— 清工作区时别 `rm -rf` 整个目录（用 `find "$SNAP" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +`）。保留 .git，下次 push 才有共同基底、只传变化的文件；每次重建成孤儿提交会让每次推送都全量重传上百 MB。

**一次推上百 MB 在这类网络下会被掐断**（`send-pack: unexpected disconnect while reading sideband packet`；实测一个 110MB 的推送连续两次失败，定时任务因此空转），所以用 `scripts/push-pages.py` 分批推 + 单批重试：

```bash
python3 scripts/push-pages.py --dir .publish/pages --remote git@github.com:<user>/<repo>.git \
    --branch gh-pages --message "snapshot $(date '+%F %H:%M') · $pages 页" --max-batch-mb 20
```

- 按体积切批（默认 20MB/批、最多 400 文件/批），**资源先推、HTML 页最后推** → 最后一批推完站点才是一致的
- 每批 `git add -A -- <批内文件>` → commit → `push -f`，失败按 15/30/45… 秒退避重试（默认 5 次）；单批失败不影响其他批，退出码 1 让定时任务下轮再试
- 实测 MedHOT 全量 273MB：**16 批 / 10 分钟**推完（同内容一次推 = 失败）；稳态增量（每次只有时间戳等少量页变化）**9 批 / 92 秒**，整轮 2 分钟

地址 = `https://<user>.github.io/<repo>/`。**推完必须从外部 curl 一次**。实测（2026-10，`MRF3247/medhot`、`thinkhot` 两个公开仓库）：向仓库推 `gh-pages` 分支会**自动开启 Pages**，推完 1–2 分钟地址就 200，不需要点任何设置。没自动开时才让用户去 **仓库** 页 Settings → Pages → Source 选 `gh-pages` 分支 → Save（一次性）。⚠️ 用户自己摸「Settings → Pages」时很容易停在**账号级**的那个 Pages（页面是 Verified domains / Add a domain）——那是管自定义域名和发布白名单的，跟仓库发布无关，要主动纠正，别让他卡在那儿。

### 4. 定时（launchd）+ 自愈

`templates/launchd-3x-daily.plist` 是可直接改的模板（`StartCalendarInterval` 数组 = 9:00 / 12:00 / 15:00）。要点：

- 脚本自己检查本地 API / 生产 web 在不在，不在就拉起来 —— 否则「那次没推」会变成静默空档
- 日志落文件（`.publish/snapshot.log`），别接管道
- 装完 `launchctl load -w ~/Library/LaunchAgents/<label>.plist`；改 plist 后 `unload` 再 `load`

### 5. 快照前把 `SITE_URL` 设成最终公网地址

SSR 的 canonical / og:image 用启动时的 `SITE_URL`（浏览器里才用 `location.origin`）。给隧道起过的进程会把死掉的隧道地址烘进每一页，所以起生产 web 时要显式给 Pages 地址，并把用过的值记在标记文件里（例 `.publish/web.site_url`），不一致就重起：

```bash
WEB_PORT=3100 API_BASE_URL=http://127.0.0.1:3001 SITE_URL=https://<user>.github.io/<repo> nohup node server.ts >web.log 2>&1 &
```

## 坑（每条都真踩过）

1. **必须用生产构建，不能用 dev server 对外**：`react-router dev` 有 Host 白名单，走隧道/子路径会被 `Blocked request. This host is not allowed` 挡成 403。`npm run build` + `node server.ts` 没有这个检查。
2. **签名/代理图片必须落成本地文件**：页面上的图常来自 `/api/img-proxy?u=...&sig=...&exp=...` 这类**带过期签名**的地址。不改写、不落地，快照几天后图片全裂；要下载进快照并换成本地路径。**命名必须用 `u=` 里的原图 URL 算哈希，不能用整条签名 URL** —— 签名每次渲染都变，按整条 URL 命名会让每次快照换一批文件名，页面引用与已下载文件永远对不上（实测：12 个头像引用全 404，而仓库里躺着 10 个名字对不上的文件）。
3. **改写 HTML 时不能只顾属性，SSR 载荷里是 JSON 字符串**：`&` 被写成 `\u0026`、URL 结尾紧跟 JSON 的转义反斜杠（`...sig=abc\"`）。抓取时把 `\u0026` / `&amp;` 还原成 `&`，改写时**必须把结尾那串反斜杠原样写回** —— 直接 string replace 会吃掉转义、把 hydration 载荷写坏（白屏/报错）。
4. **根绝对路径是子路径站的最大杀手**：站内所有 `"/..."`（含 CSS 的 `url(...)`、内联 JSON-LD）都要改写成 `{prefix}/...`；改完自检「残留 `/api/` 引用 = 0」。
5. **别把「起了后台服务」的脚本输出接 `tail`/`head`**：后台进程继承管道写端 → 管道永不 EOF → 命令挂到超时被杀，连带把服务一起带走（症状：服务不在、公网 502）。重定向到日志文件，再读日志。
6. **bash：`$VAR` 后面紧跟中文标点会被并进变量名**（`$WEB_PORT）` → `WEB_PORT）: unbound variable`）。中文句子里的变量一律写 `${VAR}`；新脚本先 `bash -n` 过一遍再跑。
7. **杀端口监听者要加 `-sTCP:LISTEN`**：`lsof -ti tcp:PORT` 会把连着这个端口的隧道/代理进程一并列出来（ESTABLISHED），误杀后地址就废了。
8. **快速隧道没有可用性保证，地址随进程死亡**：进程一挂，那个域名很快在 DNS 上消失（症状是 `Could not resolve host`），旧地址**永久作废**、只能重起拿新地址。所以：别把隧道地址当长期链接发出去；每次给出去之前从外部 curl 验证；看到 `Registered tunnel connection` 也不算成功，要真请求一次。
9. **交付时如实报口径**：快照站 = 「整页 HTML + 图片 + 样式，点到没抓的页会 404」，不是「完整站」；定时 = 「每天 N 次」，不是「实时」。用户按这个预期用它才不会误判。
10. **`og:image` / canonical 是带站点域名的绝对 URL**（因为起 web 时 `SITE_URL` 就是最终公网地址）：只匹配 `"/..."` 的正则会漏掉它们，结果页面里引用的 og 图在托管上 404（正文正常，但分享预览破图）。要把 `pages_url` 开头的绝对 URL 也当站内资源抓下来（`--pages-url`）。
11. **放一个 `.nojekyll`**：GitHub Pages 默认跑 Jekyll，空文件即可关掉，省一次构建也避免它动你的文件。
12. **交付前用脚本对账**，别只看 HTTP 200：扫所有 HTML 里引用的站内资源，逐个查文件是否存在，要求**缺失 0**（注意 JSON 载荷里的路径尾巴带转义反斜杠，比较前先 `rstrip("\\")`）。实测 2026-10：MedHOT 全量 2907 页 / 引用站内资源 1081 个 / 缺失 0（有界 50 页时是 79 个）；线上再随机抽 25 页复验，24 页 200、1 页是瞬时网络抖动、重试 200。
13. **改写用的正则绝不能把 `/>` 当路径**（血案，在 head 里肉眼看不出来）：匹配「站内绝对路径」的字符类必须把 `<`、`>` 一起排除，收尾字符集也要含 `<`。否则自闭合标签的 `/>` 会被当成路径再前置一层前缀 → 全站每个 `/>` 变成 `/{prefix}/>`。在 head 里（`<meta .../>`）浏览器把它当垃圾文本丢掉、截图也看不出；body 里的就近就是可见的 `/{prefix}/` 文本，最坏会写坏 hydration 载荷。**写完必跑回归**：拿 `<meta property="og:image" content="/og/x.png"/>` 和 `<img src="/assets/a.png"/>` 两个样例过改写，断言输出里没有 `/{prefix}/>`；全站扫一遍 `grep -ro "/{prefix}/>" . | wc -l` 要求为 0。
14. **推送失败必须看得见**：launchd 那次失败只在 `.publish/snapshot.log` 留了一行 `❌ 推送失败`，站点静默停更了好几个小时。定时任务的成功/失败都落日志，交付时主动抽查「上一次定时任务是不是真推成功」（看日志里有没有 ✅ 那行 + 从外部 curl 一次）。
14b. **发布脚本里 push 要带重试，别指望一次成**：走 VPN/代理的机器上 `git push` 会偶发 `SSL_ERROR_SYSCALL`/`Couldn't connect to server`（同一时刻 curl 却能 200），而 `set -e` 之外的包装容易把它当成「已推送」。固定写法：循环 3 次 `git push origin <branch>`，失败 `sleep 10` 重试，三次都失败 `exit 1`，并把成功/最终失败各打一行带时间戳的日志。多机共推同一仓库时还会 non-fast-forward：先 `git fetch` 拿到远程真实 HEAD；静态站快照属生成物，确认「本地数据源（数据库/导出）比远程快照新」后直接用 `push --force` 覆盖，不必 rebase 生成文件。
15. **HTTPS 推送（不用 SSH）的凭据三件事**：① `~/.git-credentials` 每行必须是 `https://x-access-token:<token>@github.com` —— 只写 `https://<token>@github.com` 时 store helper 取不出密码，`git push` 报 `could not read Username for 'https://github.com': Device not configured`（看起来像没配凭据，其实格式错）；② `git config --global credential.helper store` 配完用 `printf "protocol=https\nhost=github.com\n\n" | git credential fill` 验一次；③ **项目级 `credential.https://github.com.helper` 会覆盖全局 store**，若它指向一个未登录的 gh helper（`gh auth login` 被 token scope 拒过就会这样），推送永远失败——`git config --local --unset credential.https://github.com.helper` 后重试。token 文件 `chmod 600`，不要把 token 写进 remote URL（会落在 .git/config 且到处可见）。

## 支持文件

- `scripts/snapshot.py` —— 可复用的快照抓取器（有界/全量：固定页 + sitemap 清单 + 列表分页挖详情页；镜像资源含签名头像；子路径改写 + 查询型 URL 映射成目录；残留自检）。
- `scripts/push-pages.py` —— 分批 + 重试的分支推送器（大仓库在这类网络下一次推会被掐断，必须分批）。
- `templates/launchd-3x-daily.plist` —— 每天 9:00 / 12:00 / 15:00 的 launchd 模板，改 Label/路径即可。
