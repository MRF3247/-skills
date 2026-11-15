---
name: medhot-medical-news-site
description: Use when 运行/维护 MedHOT（AIHOT 医学版热点站；用户已停用，勿擅自重启）。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [medical-news, self-hosted, postgres, news-aggregator, content-pipeline]
    related_skills: [med-web-dashboard, daily-scraping-automation, content-data-hub, medical-news-scraping]
---

# MedHOT（AIHOT 医学版热点站）

## When to Use

- 用户要看 / 启停 / 排查 MedHOT 医学热点站（localhost:3000）
- 要改 `industry/` 行业包（信源、分类、评分标准、提示词），或再做一个新行业版
- 要跑它的自测，或解释事件聚簇 / 热度榜 / 日报的行为


自建全球医学新闻聚合站，框架来自开源项目 AIHOT（MIT）：信源 → 机械判重 → 模型预筛 → 同一标准独立打两次分 → 过门槛进精选 → 写中文标题/摘要/理由 → 同一件事聚成事件 → 按独立来源算热度 → 每天 08:00 出日报。

## 位置与端口

- 医学版（工作仓库）：`/Users/Jin/Documents/GitProgram/MedHOT`（自带 git，本地提交，无远端）
- 原项目快照：`/Users/Jin/Documents/GitProgram/AIHOT`（对照用，不改）
- 姊妹站（社科版，同源代码）：`/Users/Jin/Documents/GitProgram/ThinkHOT` —— 见下「姊妹站 ThinkHOT」
- 行业包（改这里就够了）：`industry/` —— site.ts / taxonomy.ts / topics.json / sources.json / selection.ts / features.ts / prompts/*.md
- 端口：3000 网站 · 3001 API · 5433 PostgreSQL；后台 `/admin`（密码在 `.env` 的 `ADMIN_PASSWORD`）

## 姊妹站 ThinkHOT（社科版，同源代码）

同一套 AIHOT 框架的第二份实例。

> ⚠️ 用户只说「localhost:xxxx 打不开」时先认站：**3000/3001 = MedHOT，3020/3021 = ThinkHOT**；先 `lsof -nP -iTCP:<端口> -sTCP:LISTEN` 看是哪个仓库的进程，别默认是 MedHOT。

- 仓库 `/Users/Jin/Documents/GitProgram/ThinkHOT`；启停 `./thinkhot.sh start|stop|restart|status|logs`（**镜像 medhot.sh，连坑都一样**）
- 端口：**3020** 网站（`/`、`/all`、`/hot`、`/daily`、`/changelog`、`/story/<public_id>`）· **3021** API · **3120** 生产 web（快照用）· **5434** PostgreSQL
- 公网 https://mrf3247.github.io/thinkhot/（launchd `com.thinkhot.snapshot`，9/12/15 点）
- 主题是社科思想（心智与意识/社会与制度/历史与记忆/…），**历史类事实多** → 「已知 bug」第 6 条那个 Invalid Date 真发作过（1516 年威尼斯隔离区、1891 年布拉格病例两页 503）
- **代码与脚本同源**（`publication/stories.ts` 等公共代码两边各一份），坑也同源：改公共逻辑、修 bug、改启动脚本时**两个仓库都查**
- 已装同样的守护：`watchdog.sh` + `com.thinkhot.watchdog`（探 3021 `/api/health` + 3020 `/`）；快照 plist 也已加 `AbandonProcessGroup=true`
- **`web` 的 `API_BASE_URL` 必须显式喂**（`thinkhot.sh` 里 `env_value` 读 `.env`）：前端兜底值是 `127.0.0.1:3001`，那是 MedHOT 的 API —— 不喂就安静地渲染成医学主题（页面照样 200，看着正常，其实是另一个站的数据）

## 仓库与 README（GitHub: MRF3247/medhot）

- README 已是**本站自己的版本**（2026-10 重写），不再是上游 AIHOT 原文（AI 行业 + aihot.news + 模型榜/Codex + Docker 那套）。写之前先读现值：`industry/sources.json`、`taxonomy.ts`、`selection.ts`、`.env`（HOT_WINDOW_HOURS）——文档里的数字极易过期，本机的《MedHOT-本地运行说明.md》就滞后过（页面段还写着旧名「热点榜」）。
- 顶部横幅是自制的（本站 logo 四角星 + 配色，浅/深两版 2560×640）。生成脚本在 `~/.hermes/cache/scratch/banner/make_banners.py`（HTML + Chrome `--headless=new --screenshot --force-device-scale-factor=2 --window-size=1280,320`）。**别用 `docs/assets/banner-*.png` 的上游原图**——那是 AIHOT 的品牌宣传图（AIHOT logo + aihot.news 域名），挂在仓库首页会认错门。
- 仓库简介/主页/topics 用 GitHub API 设置（本机没装 gh）：简介与主页走 `PATCH /repos/MRF3247/medhot`，**topics 必须走单独的 `PUT /repos/{o}/{r}/topics`**（PATCH 里带 topics 静默无效）。token 在 `~/.hermes/.env` 的 `GITHUB_TOKEN`，别打印出来。
- **推送坑（两种，都踩过）**：(a) `push-pages.py`/`snapshot.sh` 会**静默冻结**——见下「已知 bug」第 3 条，公网页面半天不更新时先 `ps aux | grep push-pages` 看有没有卡死的进程；(b) `git reset --soft HEAD~1` 在本分支已落后 origin 时，会把远端已有的提交从本地历史里丢掉（症状：`git push` 报 `behind 1`）。动手前先 `git fetch && git status -sb`；要重做提交用 `git reset --soft origin/main`，别用 `HEAD~1`。

## ⚠️ 已整体停用（用户主动终止，勿擅自重启）

MedHOT 已按用户要求下线，现状：`com.medhot.snapshot` + `com.medhot.watchdog` 已 bootout、plist 移到 `~/Library/LaunchAgents/_disabled/`；web / worker / api 与专用 PostgreSQL（5433）全部停止；端口 3000 / 3001 / 5433 无监听。

- **看到站点打不开、快照没更新、日志停在某天 —— 都不是故障，不要排障、不要 `./medhot.sh start`、不要把 plist 移回去。** 它现在的「静默」就是正确状态。
- 只有用户明确说恢复时才做：plist 从 `_disabled/` 移回 `~/Library/LaunchAgents/` → `launchctl load` 两个 job → `./medhot.sh start` → 等 worker 跑一轮再 `./snapshot.sh` 补页。
- 代码、`.pgdata`、已入库条目（数千条稿件 / 精选）都保留在原位，没删；别再问「要不要清理」。
- 公网 https://mrf3247.github.io/medhot/ 是 Pages 快照，停用后不再更新，仍可访问旧内容。
- **ThinkHOT（社科版）是独立站点，不受此停用影响**，照常维护。

## 启停（仅恢复后使用）

```bash
cd /Users/Jin/Documents/GitProgram/MedHOT
./medhot.sh start|stop|restart|status|logs [api|worker|web] [行数]
```

## 运行环境（非标准，容易踩）

- 本机无 Docker/Homebrew，Postgres 16.2 是从 `pgserver` 预编译包里拆出来的：二进制在 `/Users/Jin/pgsql/16/bin`，`.dylibs` 必须在 `bin` 的上两级 → 路径**不能带空格**（原来放在 `Open Programs/` 下会构建失败）。数据目录 `MedHOT/.pgdata`，只监听 127.0.0.1:5433。
- 两处本地补丁（换 Docker 官方镜像后都不需要）：
  1. `pg_trgm` 扩展缺失，用 16.2 源码现场编译。捆绑的 PGXS 里 `PG_SYSROOT` 指向已不存在的 Xcode SDK，必须覆盖：
     `make USE_PGXS=1 PG_CONFIG=/Users/Jin/pgsql/16/bin/pg_config PG_SYSROOT=$(xcrun --show-sdk-path) && make ... install`
  2. `database/migrations/0034_lz4_toast.sql`：该 PG 未编译 lz4，已加降级到 pglz（`EXCEPTION WHEN invalid_parameter_value OR feature_not_supported`）。
- **不要用 `npm run start -w ...` 起进程**：该脚本不加载 `.env`，会连错库。用 `node --env-file=.env apps/{api,worker}/src/main.ts`。
- web 必须**在 `apps/web` 目录里**起（`npx react-router dev --port 3000 --host 127.0.0.1`），否则报 `React Router Vite plugin not found in Vite config`。

## 自测

```bash
PGBIN=/Users/Jin/pgsql/16/bin
$PGBIN/dropdb -h 127.0.0.1 -p 5433 -U postgres medhot_test; $PGBIN/createdb -h 127.0.0.1 -p 5433 -U postgres medhot_test
DATABASE_URL="postgres://postgres@127.0.0.1:5433/medhot_test" node scripts/migrate.ts
DATABASE_URL="postgres://postgres@127.0.0.1:5433/medhot_test" npm test   # 136 项，约 4 分钟
npm run typecheck
```

**每次必须先重建 `medhot_test`**：复用旧库会因上一轮留下的日报数据导致 `report-candidates` 等用例误报失败（不是代码坏了）。

## 改行业包时必查的坑

AIHOT 的代码和测试里硬编码了 AI 行业口径，改医学版时这些地方会漏（都踩过）：

1. **提示词的行业词**：`report-daily-lead.md` / `report-period.md` 写的是「入选的 AI 动态」→ 日报/周报会按 AI 行业口径写。改完要通读 `industry/prompts/` 全部文件，别只看常用的那几个。
2. **前端文案**：`routes/hot.tsx`（「AI 圈讨论最多的 N 件事」）、`features/report/format.ts`（「N 件 AI 大事」）、`ReportPaper.tsx` / `report-latest.tsx`（「AI 日报」）、`routes/topics.tsx`（「按主题看 AI」+ 描述）、表单里的 OpenAI 占位符。统一用 `industry/site.ts` 的 `withSubject(noun)`，别硬编码行业词。
3. **测试桩按提示词标题路由**：测试用 `system.includes("...")` 判断这是哪个步骤（预筛/评分/理解/结构化）。改写提示词后匹配失效 → 请求被当成别的步骤 → 一直重试到 120 秒超时。改提示词标题必须同步改 `tests/analyze.test.ts`、`tests/analyze-shutdown.test.ts` 的路由关键词。
4. **测试桩返回的枚举值**：类别/内容类型/标签/主体 id 都来自 `industry/taxonomy.ts`，换成医学词表后桩里的旧值会让 `chatJson` 报 `invalid_value`。
5. **身份守卫（防张冠李戴）**只认 `IDENTITY_LEXICON` 里登记过的实体：测试用例也要换成医学实体（如 Pfizer/辉瑞），否则守卫永远返回 pass。
6. **改提示词只影响新条目**：提示词版本号是内容哈希，旧分析不会自动重算。

## 发布到公网（免费、不用买域名）

**首选做法：静态快照 + 定时推 GitHub Pages**（用户拍板，取代隧道）—— `./snapshot.sh`（launchd `com.medhot.snapshot` 每天 9:00 / 12:00 / 15:00 自动跑）。地址固定 https://mrf3247.github.io/medhot/ ，不依赖隧道、不受本机链路影响；代价是「不是实时」+ 本机开机那次才推。仓库根目录已有 `snapshot.py` + `snapshot.sh` + `com.medhot.snapshot.plist`。

- 快照范围（**全量**，2026-10-10 起）：sitemap 清单 + 列表分页里挖出的**全部条目页** —— 固定页（首页/大事榜/全部动态/日报/主题/预印本/Agent/关于/更新日志）+ 全部事件页 + 全部条目页 + 列表分页页（`/all/pN/`）与分类页（`/all/c/<类>/`）→ 实测 **2907 页 / 273MB**、5740 个文件。要瘦身最先砍 `og/items/*.png`（135MB，只影响分享预览小图）。
- 推送走 `python3 push-pages.py --dir .publish/pages --remote git@github.com:MRF3247/medhot.git --max-batch-mb 20`：**必须分批**，一次推上百 MB 会被链路掐断（`send-pack: unexpected disconnect`，实测 110MB 连失两次、定时任务静默空转）。首次全量 16 批 / 10 分钟；之后稳态每轮 9 批 / 92 秒（含抓取整轮约 2 分钟）。
- `.publish/pages/.git` **不要删**（快照工作区清理时保留它），删了下次 push 要全量重传。
- 改了前端要重建：`./publish.sh build`（快照脚本发现 build 不存在会自己重建）。
- **完整配方、坑与可复用脚本见技能 `free-site-publishing`**（子路径改写、签名图片落地、SSR 载荷转义、`/>` 被误当路径的血案、分批推送、Pages 自动开启）。脚本口径：`snapshot.py`（`--sitemap --deep-all` = 全量）+ `push-pages.py`（分批推），两者都在仓库根目录。

**备选（真·实时，但要当心）：Cloudflare 快速隧道** —— `./publish.sh build|start|restart|reload|web|stop|status|logs`（生产 web 端口 3100 + 隧道，地址写 `.publish/url.txt`）。页面直接读本机数据、不需要推送，但地址每次重启都换、且到 Cloudflare 边缘的链路一断整站打不开（本机网络常常挡着 QUIC/UDP 7844 与边缘 TCP 443）——**不要当长期链接发给别人**。改了前端代码：`./publish.sh reload`（重建 + 只重启 web，隧道不动、地址不变）；只重启 web 用 `./publish.sh web`。

坑（都踩过）：

1. **不能用 dev server 对外**：`react-router dev` 有 host 白名单，隧道域名会被 `Blocked request. This host is not allowed` 挡成 403。必须 `npm run build` 后用 `node server.ts`（生产服务器没有这个检查）。build 只要 3 秒。
2. **`SITE_URL` 要在起进程时给成公网地址**：`lib/seo.ts` 的 `siteUrl()` 在浏览器里用 `location.origin`，但 SSR 出来的 HTML（爬虫、微信/Twitter 链接预览读的那份）用 `SITE_URL`；不给就是 canonical/og:image 指向 localhost。og 图本身由 API 现成提供（`/og/site.png`、`/og/pages/*.png` 都 200，不是静态文件）。
3. **`lsof -ti tcp:<端口>` 会连隧道进程一起杀掉**：隧道对本地端口有 ESTABLISHED 连接，会一并列出来（症状：地址突然 530 错误 1033，日志 `Initiating graceful shutdown due to signal terminated`）。杀监听者必须加 `-sTCP:LISTEN`。
4. **bash 里 `$VAR` 紧跟中文标点会被当成变量名的一部分**（`$WEB_PORT）` → `WEB_PORT）: unbound variable`）。中文句子里引用变量一律写 `${VAR}`。
5. **快速隧道地址每次重启都换**，且地址是进程一启动就打印、这时还没连上 Cloudflare 边缘 → 脚本要等日志里出现 `Registered tunnel connection` 再接客（不等会拿到 000/530）。**隧道没有任何可用性保证**：进程一挂，那个域名很快从 DNS 消失（`Could not resolve host`），旧地址永久作废。所以 (a) 给用户地址前必须从外部 curl 验一次；(b) 对外长期用的站用快照推 Pages（见上），别用隧道。要固定地址的实时方案：域名挂 Cloudflare 用命名隧道（要买域名 ¥50-100/年），或上 VPS（`docker-compose.yml` + `deploy/Caddyfile` 已备好）。
6. 公网会一起暴露 `/admin`（有登录，302 到 `/admin/login`）；只想要只读页面的话要在前面加一层挡 `/admin` 的反代。
7. **别把 `./publish.sh` 的输出管道给 `tail`/`head`**：web 由脚本 nohup 起在后台，会继承这个管道写端 → 管道永不 EOF → 命令一直挂着，最后被超时杀掉，连带把 web 一起带走（症状：`status` 显示 web 不在、公网 502）。要少看输出就它自己就够短，别接管道。

## 大事榜（/hot）：按「值得看」排，不按讨论人数

榜单口径是**重要度**，不是讨论热度：取窗口内每个事件所有公开报道里**最高的 AI 精选评分**（`publications.score`）作为排序键，同分按时间新近兜底。热度（`story_heat_hourly`）降级成卡片上的徽章／附注，只作上下文。

- 规则版本：`HOT_RULE_VERSION = "importance-v1-maxscore"`（`packages/backend/src/events/hot.ts`）
- 窗口：`HOT_WINDOW_HOURS`（`.env`）。医学事件更新慢 → MedHOT 设 **168**（7 天）；不设默认 48 小时。
- 为什么改：原来的门槛是「≥2 个独立信源且至少 1 个编辑部性质源，48 小时窗」。医学信源绝大多数是独家（767 个事件里只有 24 个曾有两家独立源），于是**热榜长期空榜**——不是故障，是规则跟信源结构不匹配。
- 立刻重算：`node --env-file=.env scripts/hot-now.ts`（不用等 worker 的 5 分钟一批）。
- **取分必须走 facts/fact_articles 关联，不能只看 `publications.story_id`**：库里 2137 条 publications 有 1321 条 `story_id` 为空（未落组/重分组滞后），只按它筛会漏掉大半事件。
- 前端：`routes/hot.tsx`（大字显示「精选评分」）、`features/feed/HotTopics.tsx`（首页条带「值得看的大事」）、nav/more/story/agent/preprints/llms.ts 的「热点榜」全部改叫「大事榜」。

### 排查「为什么某件大事没上榜」

用户会拿「诺奖这种大事怎么没有」来问。按三层查，别先怀疑抓漏 —— 实测 2026 诺贝尔生理医学奖没进榜，三层全占了：

1. **抓取层**：`select count(*) from articles where title ilike '%关键词%' or body_text ilike '%关键词%'`。诺奖 = 27 篇（Nature/STAT/MedPage/BBC/NYT 都有）→ 抓得很全。
2. **分析层**（最易被忽略、影响最大）：`processing_state`。**失败稿没有评分 → 结构上不可能上榜**。实测近 7 天 520 analyzed / **250 failed** / 20 blocked ≈ **32% 失败**；诺奖 27 篇里 16 篇失败（59%）。错误多为 `receipt NNNN outcome unknown`（分析请求没拿回结果），`processing_attempts` 到 1–4 次后不再重试。
3. **评分/分组层**：榜单取窗口内每件事**最高 AI 精选评分**排序取前 10（见上节）。诺奖最高只有 42 分，而同窗口 389 件事里第 10 名门槛 71 分、前 25 名清一色 FDA 批准 / III 期达终点 / 指南 —— **评分口径偏「临床可操作」，行业标志性事件（诺奖 / 指南更新 / 重大公卫）天生低分**；同一件事还会被拆成多条事件（诺奖被拆成 4–5 个），分数进一步摊薄。
   ⚠️ 探针要对准真实链路：`curl /api/site/hot` 看实际排名；只按 `publications.story_id` 分组会低估（1321/2137 条 story_id 为空，榜单实际走 facts/fact_articles）。
4. 顺手确认「它其实在站上」：用 `publications.article_id` 拼条目页 URL（`https://mrf3247.github.io/medhot/items/<article_id>/`）能开 → 只是没进榜，不是没收录。

改善选项（按性价比，需用户拍板）：① 补跑失败分析（最根本）② 同类报道合并成一个事件 ③ 评分加「行业标志性事件」维度 ④ 榜单加人工置顶位（表 `editorial_overrides` 现成）。

## 从一个话题挖稿件、做内容选题（内容作者视角）

用户会拿「MedHOT 上关于 X 的新闻」要选题包或文案。固定五步：**库内检索 → 事件聚合 → 官方一手源核验 → 事实骨架表 → 按受众分工选题**。SQL 与命令配方见 `references/content-mining-queries.md`。

1. **关键词一次铺开再判「有没有」**：英文通用名 + 商品名 + 试验代号 + 中文译名一起 OR，用 `count(*) filter (where ...)` 一条 SQL 出各路命中数。库里中文稿极少，**只查中文名会误判成「站上没有这条新闻」**。
2. **别只查 articles**：模型写的中文标题/摘要在 `analyses.title_zh` / `summary_zh`（**不是** `title_cn`），`selected=true` 即当天入选精选，`score` 是精选评分。同一件事的多篇报道走 `facts` → `fact_articles`，**不要用 `publications.story_id`**（大量为空）。
3. **`body_text` 是整段单行长文本**：`read_file` 只给开头一截（还会标 truncated=false），要全文就落文件再 `python3 -c "import textwrap;print(textwrap.fill(open(p).read(),120))"`。
4. **一个话题常常只有 1 个事件、1–2 篇有效稿**——医学信源绝大多数是独家，这是常态不是抓漏，向用户交代清楚。低分稿（20–40 分）别直接丢：串烧式日报稿的标题串里常有一句带过某适应证扩大，可当线索，**但不能当信源**。
5. **硬事实必须回官方一手源**（FDA 通知 / 药企新闻稿 / 论文或会议摘要 / ClinicalTrials.gov），媒体转述只作线索；跨站口径冲突时以官方页面为准。
   用户下一个问题几乎必然是「这个新闻最权威的论文出处是哪个」——权威层级、题录核验、免费全文与存档 PDF、交付前的「核心情报覆盖自查」，见 `medical-evidence-sourcing` 的「从一条新闻回溯到原论文」一节。
6. **给用户的站内链接**：条目页 `https://mrf3247.github.io/medhot/items/<article_id>/`、事件页 `.../story/<story.public_id>/`（public_id 从 `stories` 表取；本地可拿 `.publish/pages/story/` 下的目录名核对）。发出去之前用浏览器打开一次。

## 本地站静默变 503 的两个 launchd 坑（2026-10-14 实际踩到，站点挂了 2 天）

症状：`http://localhost:3000` 打不开（503/000），`./medhot.sh status` 显示 api/worker/web 全「未运行」。代码没改、数据库好好的，就是进程死了没人管。两个根因叠加：

1. **`medhot.sh` 用 `npx` 起 web → launchd 下必然失败**：launchd 的 PATH 只有 `/usr/bin:/bin`，没有 node/npx → 日志里只有一行 `./medhot.sh: line 33: exec: npx: not found`。后果：快照任务（09:00/12:00/15:00）发现 api 挂了就调 `./medhot.sh start`，但**只有 api/worker 起来了，web 永远起不来**。已改成绝对路径（`$NODE $ROOT/node_modules/.bin/react-router dev ...`），并用 `env -i PATH=/usr/bin:/bin /bin/bash medhot.sh start` 实测通过。
2. **launchd 任务结束会杀掉 job 进程组里剩下的进程**：plist 没写 `AbandonProcessGroup`（默认 false）→ 快照脚本顺手拉起的 api/worker 在任务结束时被 TERM（日志实锤：`worker stopping`）→ **每次快照跑完本地站就死一次**。已在 `com.medhot.snapshot.plist` 加 `AbandonProcessGroup=true`（仓库里和 `~/Library/LaunchAgents/` 两份都要改，改完 `launchctl unload && load`）。

**已加服务守护（治本）**：`watchdog.sh` + `com.medhot.watchdog.plist`（`StartInterval 300`，`AbandonProcessGroup=true`）——每 5 分钟 curl `/api/health` 与 `/`，任一失败就 `./medhot.sh start`（幂等，只补缺的）。演练验证过：`pkill -f "apps/api/src/main.ts"` → 守护自动补起 → 200。临时停用：`touch .logs/paused`。

排查口诀：**先 `./medhot.sh status`看进程，再看 `.logs/{api,web,worker}.log`，然后 `ps -eo pid,etime,command | grep -iE "react-router dev|apps/(api|worker)"` 看进程有没有「活了很久」**。另外别用 `launchctl kickstart` 去手动触发快照任务——它的子进程会随 job 结束被杀（要手跑就 `./snapshot.sh`，从自己的 shell 起）。

## 「内容变少 / 感觉停更」的四层排查（按影响排序）

用户报「新闻变少/页面没更新」时，从下往上查，别一上来怀疑抓漏：

1. **分析层（最常见、最容易被忽略）**：`select processing_state, count(*) from articles group by 1`。`failed` 的稿件不会出现在站上（站点只收 `relevance=pass` + 中文标题/摘要）。实测一次积压 **512 条 failed**（占当周 1/3），原因全是回执 `outcome unknown`（LLM 请求 >120 s 未取回结果，被自动放行后稿件一直躺 failed）。修法：`node --env-file=.env scripts/requeue-failed.ts`（= 后台「运行」页的「全部重跑」），重跑通过率 ~93%，一次回收 62 条精选。
2. **抓取层**：`sources.health` + 最近 `fetch_runs`。两类硬伤：**配置白名单**（源每次抓取直接抛错，见下）和**网络受阻**（timeouts / 403）。注意 `ok` 但不代表有新内容：`found_count>0 new_count=0 ` 表示饲料里全是旧条目（周刊登一次、周末停更都正常）——想看真伪就 `curl` 原始 feed 比最新 pubDate。
3. **门槛层**：`an.selected` 恒为 false 时看打分分布 `select count(*), avg(score), max(score) from analyses ...`。精选门槛 T1=60 / T2=76（`industry/selection.ts`），而模型给「可读的临床新闻」普遍 62 分左右、wire 稿（MedPage/Medscape）封顶 71–73 —— T2 源几乎永不入选，于是首页「最新精选」可以停更好几天而系统一切正常。**这是口径问题不是故障**，要改得用户拍板。
4. **发布层**：快照推送卡死（见下）。

用户给的日期（如「只更新到 10 月 9 日」）要落到具体页面去看：首页「最新精选」停更 = 门槛层；`/all` 没内容 = 抓取/分析层；公网没更新但本地有 = 发布层。三者的修复动作完全不同。

## 已知 bug 与修复（2026-10 排查所得）

0. **故事详情页 503（Invalid Date）**：`publication/stories.ts:102` 写的是 `f.occurred_at?.toISOString() ?? null`——`?.` 只挡 null，挡不住「不是 null 但无效」的 Date。社科的 ThinkHOT 有一条 1516 年的事实，时间戳形如 `1516-03-29 00:05:43+08:05:43`（历史时区的**含秒**偏移，古代当地平太阳时），Node 的 PG 驱动解析不了 → Invalid Date → `toISOString()` 抛 `RangeError: Invalid time value` → 整页 503。MedHOT 是**同一行代码**，只是库里没有 1900 年前的事实（0 条）所以从没触发；哪天抓到医学史事件就会同样挂。修法：加 `Number.isNaN(d.getTime())` 判断。

1. **配置白名单漏键 → 源静默停更**：`sources/config-keys.ts` 的 `NESTED._aihot` 白名单必须包含 `collect.ts` 已经实现的全部键（现在四个：`initialBackfillLimit`/`initialBackfillMonths`/`intervalMinutesLock`/`maxItemsPerRun`）。漏一个的后果不是忽略配置，而是 `collectSource` **每次抓取直接抛错**（`unsupported config: _aihot.maxItemsPerRun`）→ bioRxiv/medRxiv 因此停了 12 天（47/45 连败）而无人察觉（周报里只是「抓取失败的点」）。加了键要**重启 worker** 才生效。定期体检：`node --env-file=.env scripts/audit-config.ts`（列出所有含不支持键的源，正常输出 0 个）。回归测试 `tests/source-throttle.test.ts`。
2. **放行回执不把稿件放回队列**：`admin/runs.ts` 的 `release()` 原来用 `purpose === "analyze_article"` 判断这条回执属于稿件，而稿件步骤的 purpose 实际是 `prefilter_article`/`score_article`/`structure_article`/`understand_article`…**根本没有 `analyze_article`**，于是「放行即回队」这条路径从来没生效过：自动放行只把回执标成 failed，稿件永远躺在 `failed`，只能靠人工「全部重跑」。已改为按 subject 前缀判断（`/^article:([^@]+)@/`）。回归测试 `tests/receipts.test.ts`。
3. **快照推送无超时 → 站点静默冻结**：`push-pages.py` 的 `git push` 原来没有 timeout，ssh 链路卡住时进程 25 小时不返回；`snapshot.sh` 不退出 → **launchd 不会启动同一 job 的第二个实例**（`StartCalendarInterval` 在实例仍在跑时静默跳过）→ 12:00/15:00 和次日的定时全部没跑，公网停在半推状态。已加 `timeout=600` 重试 + `GIT_SSH_COMMAND` 的 `ServerAliveInterval/ConnectTimeout`。看到「快照日志停在某批次」时：`ps aux | grep -E "snapshot.sh|push-pages"`，杀掉整条链（bash → python → ssh）再手动 `./snapshot.sh`。
4. **运维脚本必须收尾 `stopBoss()`**：`scripts/` 下直接连库+入队的脚本（`requeue-failed.ts`、`release-receipts.ts`）末尾要 `await stopBoss(); await closeDb();`，只 `closeDb()` 会被 pg-boss 的连接吊住不退出（症状：命令超时但活已经干完）。
5. **launchd 的进程组回收 → 服务静默消失**：`snapshot.sh`（launchd 任务）发现 api 不在时会顺手 `./medhot.sh start` 把 api/worker/web 拉起来 —— 但**这些进程是该 launchd job 的子孙，job 一结束会被 launchd 一起回收**。识别特征：`worker.log` 里只有 `worker started` + `worker stopping`、没有任何崩溃栈，看着像它自己退的。所以常驻服务只在**交互 shell** 里起（或给它们建独立的 KeepAlive launchd job）；用 `launchctl kickstart` 手动跑一次快照任务后，别以为服务还在。已按此修：plist 加 `AbandonProcessGroup=true` + 独立的 `com.medhot.watchdog`（见上「本地站静默变 503」节）。**通用机制、plist 与 watchdog 模板、杀-等-起演练脚本见技能 `launchd-service-supervision`。**核对：`./medhot.sh status` + `lsof -nP -iTCP:3001 -sTCP:LISTEN`。
6. **`x?.toISOString()` 挡不住「无效日期」→ 单页 503**：历史事实的时间戳带**含秒的时区偏移**（如 `1516-03-29 00:05:43+08:05:43`，古代当地平太阳时），postgres.js 解析不了 → 得到 Invalid Date；`?.` 只挡 `null`/`undefined`，Invalid Date 调 `.toISOString()` 直接抛 `RangeError: Invalid time value` → API 挂 → 那个事件/故事的详情页整页 503（同站其他页正常）。`packages/backend/src/publication/stories.ts` 的 `storyContent` 里就是这么写的，**ThinkHOT（社科版）同源同病**：它有历史日期事实所以真发作过，MedHOT 没有 1900 年前的数据所以至今没触发。自查：`select count(*) from facts where occurred_at is not null and occurred_at < '1900-01-01';`（两个库都该查）。**代价不只是「一页打不开」：API 503 → 快照抓不到这页 → 公网该页直接 404（内容等于丢了）**——核对：`.publish/pages/story/<public_id>` 不存在就是没抓上，修完必须**重跑一次快照**缺页才会补上。修法：`!Number.isNaN(d.getTime())` 判断后再 `toISOString()`、无效给 `null`，同一处的 `firstReportAt`/`publishedAt` 也顺手加。**两个仓库同源，改这类公共代码时两边都查。**

## 一批源同时抓不到：先查出网（VPN 掉线），再怀疑源

症状：多个源同时 `timeout` / `403` / `ENOTFOUND`，而且横跨完全不同的域名（新闻站和 Europe PMC 一起挂）——这几乎一定是**本机出网**的问题，不是源的问题。

⚠️ **实测教训**：一次同时「挂」了 12 个源（BBC/NYT/Guardian 三个新闻站 + MedCity 的 403 + 8 个 Europe PMC 超时），当时按「被墙 / WAF」写进了本技能；**VPN 重连后全部一次即通**，包括那个 403。别在没确认代理状态前就判「源被墙」。

排查三步（顺序别换）：

1. 代理活着吗：`ps aux | grep -iE "clash|surge|v2ray|singbox|mihomo|xray"`、`scutil --proxy`（本机 VPN 是 **TUN 模式**，没有系统代理，DNS 返回 `198.18.0.x` 假 IP 段是正常的）。
2. 直接 curl 复测那几个 feed：`curl -s -o /dev/null -w "%{http_code} %{time_total}s" --max-time 25 -A "Mozilla/5.0" <feed url>`。**VPN 掉线时才会失败**：此时 `dig` 给 Facebook/Twitter 段假 IP（`69.171.234.48`、`199.59.149.234`）、curl 给 000/超时；AliDNS DoH 同样返回污染结果、手工喂真 IP + `--resolve` 也会在 TLS 握手被断（exit 35）——这些现象**只能证明当时没走代理，不能证明「被墙」**。
3. curl 通了就清零健康状态复抓，别改配置、别换源：
   ```sql
   update sources set health='unknown', fail_count=0, next_fetch_at=now() where id in (...);
   ```
   再 `node --env-file=.env scripts/collect.ts <源id...>`（打印 found/created/revised）。复抓成功的源 health 立刻回 `ok`：`select id, health from sources where health<>'ok'` 应为空。

两个附带的坑：

- **403 别急着判 WAF 拦死，先看代码用的什么 UA**：MedCity News 用浏览器 UA 会 403、用本站 crawler UA（`DEFAULT_UA`）反而 200。
- **超时不要先调大**：fetch 超时是 25 s（`sources/rss.ts` / `json-list.ts`），29 个 Europe PMC 源每小时后同时到期时会顶到上限。这类间歇超时通常下一次自己恢复——先查 VPN，再考虑别的。

只有确认代理正常、curl 仍然失败时，才谈换源或单独配代理。

## 信源

现在 **59 个**：30 个原始信源（期刊 RSS/预印本/监管与公卫/行业媒体/临床媒体/大众健康）+ **29 个 Europe PMC 期刊源（论文带 DOI）**。

### 加医学期刊论文源（首选做法：Europe PMC，不要抓出版社网页）

Europe PMC 免费官方接口，收录 PubMed 全量，一次拿到 DOI + 摘要，**绕开付费墙与反爬**（Nature/Elsevier 页面抓不住）。信源类型 `json_list`，配置照抄任意 `epmc-*`：

```
url: https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ISSN:<刊号>%20AND%20SRC:MED%20AND%20HAS_ABSTRACT:Y&format=json&pageSize=25&sort=FIRST_PDATE_D%20desc&resultType=core
itemsPath: resultList.result · titlePaths: [title] · summaryPaths: [abstractText]
summaryIsBody: true            # 摘要即正文 → 不再去抓出版社页面
publishedAtPath: firstPublicationDate · externalIdPath: doi
urlTemplate: https://doi.org/{doi} · urlTemplateFallback: https://pubmed.ncbi.nlm.nih.gov/{id}/
ingestNoiseFilter.dropMarkersTitleOnly: [erratum, corrigendum, author correction, correction to, issue information, table of contents, in this issue, editorial board]
tags: [期刊, Europe PMC] · tier: T1 · participation_mode: editorial · interval_minutes: 60
```

四个必须记住的点（实测踩出来的）：

1. **必须 `HAS_ABSTRACT:Y`**：只有真研究论文才有摘要，来信/勘误/社论/新闻自动被挡，省掉一堆噪声（NEJM 8.8 万条 → 有摘要的 1.2 万条）。
2. **排序必须 `FIRST_PDATE_D desc`（最早发表日期）**，不要用 `P_PDATE_D`（印刷日期）：论文常先在线发表、几个月后印期，用印刷日期会一直看到旧文（Gastroenterology 印刷日期最新只到 5 月，换在线日期立刻 9 月）。`sort=CREATION_DATE` 不支持，返回 0 条。
3. **用 ISSN 查，不要用 `JOURNAL:"刊名"`**：刊名匹配不可靠；ISSN 在 PubMed 期刊页可查。
4. **摘要里有 HTML 实体**（`m&lt;sup&gt;6&lt;/sup&gt;A`）：`stripTags` 不反转义，标题会留 `m<sup>6</sup>A`。模型能读懂，不影响产出，但别拿原始标题当成品用。

加刊流程：后台「信源 → 新建」选 `json_list`，或往 `industry/sources.json` 追加后 `node --env-file=.env scripts/seed.ts`（幂等），再把 `next_fetch_at` 设成 `now()` 触发首抓。

已知取舍：
- **同一篇论文可能进两次**（出版社 RSS 与 Europe PMC 链接不同，判重按 URL），但事件层会合并成同一件事——这是多源热度算法的正常行为。
- T1 期刊论文过 60 分门槛太容易（实测入选率约 46%，原值是给 AI 新闻调的）→ 门槛校准变得更必要。

### 信源分区：让某一类信源不进「全部动态」的混排

预印本（medRxiv / bioRxiv）数量大、质量参差、精选率 0，所以单独成区：

- `industry/taxonomy.ts` 的 `SOURCE_SECTIONS` 定义分区（现在是 `{ tag: "预印本", path: "/preprints", label: "预印本" }`），**按 sources.tags 圈定信源，不是加第 8 个 category**——那些 category key 会进 URL，动了旧链接全废；预印本横跨所有内容领域，只能按「信源类型」分。
- 后端 `loadPool` 支持 `sourceIds` + `sourceMode`（`"only"` / `"exclude"`），并返回 `hiddenTodayCount`；API 参数是 `?sourceTag=预印本` / `?excludeSourceTag=预印本`。
- 前端：`/all` 默认传 excludeSourceTag，列表底部渲染「另有 N 条预印本更新 →」；`/preprints` 是独立页（`routes/preprints.tsx`，用 sourceTag=only），导航在「更多」组（`components/shell/nav.ts`）+ `MORE_PATHS`。
- `hiddenTodayCount` 跟当前筛选（category/tag/topic）走、不跟搜索词 q 走，所以搜索时会隐藏这行提示。

加第二个分区（比如「撤稿与科研诚信」「会议摘要」）：在 `SOURCE_SECTIONS` 加一条、给对应信源打同样的 tag、复制 `preprints.tsx` 改成新路径、`routes.ts` 注册、nav 加入口。

### 压住「量大但低价值」的源（预印本降压配方）

自动调度会**按产量把活水源调到最短 15 分钟**（`adaptIntervals`，每天 04:20 跑），所以手动改 `interval_minutes` 会被覆盖。两个配置键（写在 `sources.json` 的 `config._aihot`，也要同步更新库里那行）：

- `intervalMinutesLock: 240` —— 锁定间隔，自动调度不再改（`intervalLockMinutes()`）。注意间隔只影响**检查频率**，不影响导入总量（饲料里有几条就进几条）。
- `maxItemsPerRun: 10` —— 每次导入上限，**只能调小不能放大**全局 60（`maxItemsPerRun()`）。这才是真正压量的旋钮；配合 `sortByPublishedAt: true` 保证留最新。
- `initialBackfillLimit: 3` —— 首次导入回补条数（直接决定首跑模型成本）。

改完必须同步改数据库（`scripts/seed.ts` 是 ON CONFLICT DO NOTHING，不会更新已存在的源）：
```sql
update sources set interval_minutes=240, config = jsonb_set(config,'{_aihot}','{"intervalMinutesLock":240,"maxItemsPerRun":10,"initialBackfillLimit":3}'::jsonb) where id in ('rss-medrxiv','rss-biorxiv');
```
（一条 UPDATE 里不能对同一列赋值两次，多个 jsonb 改动要嵌套 `jsonb_set`。）

### 原始 30 信源的其他坑

- medRxiv 只有 `https://connect.medrxiv.org/medrxiv_xml.php?subject=all` 能解析（旧的 `/relate/content/181` 会 feed parse error）。
- 国内医学媒体（医脉通/健康界/生物谷/梅斯/澎湃健康）**没有可用 RSS**。收中文两条路：后台建 `mp_account` 信源（需「极致了」key，按次计费有熔断），或用 `external` 推送接口把已有抓取脚本结果 POST 进来（配 `INGEST_TOKEN`）——B站/小红书/抖音/视频号走后者。

## 日报窗口与陷阱

- 日报窗口是**北京时间当天 08:00 往前 24 小时**，所以刚装好的当天窗口内没有内容。
- **不要为了看效果手动 compose 明天/未来日期的日报**：会把当天事实标记为「已被覆盖」，导致第二天 08:00 的真日报变空。

## 下一步（待用户拍板）

1. 门槛校准：`selection.ts` 现在沿用 AIHOT 在 AI 领域校准的默认值（60/65/76），**不是医学校准结果**。做法是人工标 100–200 条跑 `scripts/eval-selection.ts`（样本格式 `industry/gold.example.jsonl`），先改评分标准再动门槛。
   **用户已拍板：暂不校准、保持现在的严格口径** —— 不要再主动推校准方案，他问起才做；真要动必须先用真实稿件出前后对比（看「涨的是不是该涨的」，不看平均分）。
2. 中文信源接入（见上）。
3. 配 `EMBEDDING_*`（或 `DASHSCOPE_API_KEY`）给事件归组加一路向量召回；不配也能跑，只是跨语言同一件事可能归不到一起。

细节文档：项目根目录 `MedHOT-本地运行说明.md`。
