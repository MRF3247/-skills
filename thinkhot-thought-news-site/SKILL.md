---
name: thinkhot-thought-news-site
description: Use when 运行/维护 ThinkHOT 社科思想热点站。
---

# ThinkHOT 人文社科思想热点站

用开源 AIHOT 框架改的人文社科版热点站，与 MedHOT（医学版）同源。三份代码在 `/Users/Jin/Documents/GitProgram/`：
`AIHOT`（原版参考）· `MedHOT`（医学版）· `ThinkHOT`（本项目）。

## 仓库与 README（GitHub: MRF3247/thinkhot）

- README 已是**本站自己的版本**（2026-10 重写），不再是上游 AIHOT 原文。写/改之前先读现值：`industry/sources.json`（现 140 个）、`selection.ts`（现 T1 58 / T1_5 62 / T2 62）、`taxonomy.ts`、`topics.json`。
- **本仓库里的《ThinkHOT-本地运行说明.md》是校准时点的旧快照**（写的是 129 个信源、T2 72、中文源全部不过线），与现在的 140 个源 / T2 62 不一致；引用它之前先核对，别直接抄数字。另：仓库里还留着一份多余的 `MedHOT-本地运行说明.md`（建站时复制进来的，已跟踪未清）。
- 顶部横幅是自制的（本站 logo 四角星 + 配色，浅/深两版 2560×640）。生成脚本在 `~/.hermes/cache/scratch/banner/make_banners.py`（HTML + Chrome `--headless=new --screenshot --force-device-scale-factor=2`）。**别用 `docs/assets/banner-*.png` 的上游原图**（AIHOT 品牌宣传图）。
- 仓库简介/主页/topics 用 GitHub API 设置（本机没装 gh）：简介与主页走 `PATCH /repos/MRF3247/thinkhot`，**topics 必须走单独的 `PUT /repos/{o}/{r}/topics`**（PATCH 里带 topics 静默无效）。token 在 `~/.hermes/.env` 的 `GITHUB_TOKEN`。
- **推送坑**：`git reset --soft HEAD~1` 在本分支已落后 origin 时，会把远端已有的提交从本地历史里丢掉（症状：`git push` 报 `behind 1`）。动手前先 `git fetch && git status -sb`；要重做提交用 `git reset --soft origin/main`。

## 启停

```bash
cd /Users/Jin/Documents/GitProgram/ThinkHOT
./thinkhot.sh start|stop|restart|status|logs [api|worker|web] [行数]
```

- 网站 <http://localhost:3020> · 后台 <http://localhost:3020/admin> · API `3021` · PostgreSQL `5434`（库名 `thinkhot`）
- 与 MedHOT 的 3000/3001/5433 错开，两个站可同时跑。`thinkhot.sh` 兜底清理用绝对路径匹配，不误杀 MedHOT。
- PostgreSQL 16.2 在 `/Users/Jin/pgsql/16/bin`（二进制要求 `.dylibs` 在 bin 上两级，路径不能带空格）。

## 安全阀（改完务必还原）

`.env` 里两个开关，做冒烟测试/验证连通性时关掉它们可以**零成本**跑完整采集链路：

- `COLLECT_ENABLED=false` → 不抓取
- `MODEL_CALLS_ENABLED=false` → 只采集不调模型（资料入库但不分析）

验证顺序：先 `COLLECT_ENABLED=true` + `MODEL_CALLS_ENABLED=false` 跑一轮，看 `fetch_runs` 表逐源成败；
确认无误再开模型调用。改完 `.env` 必须 `./thinkhot.sh restart`（进程只在启动时读）。

## 改造面几乎只在 industry/

信源/分类/门槛/提示词/品牌全在 `industry/`：`site.ts`（站名、行业词、主题色）· `taxonomy.ts`（分类、标签白名单、主体名录、身份词典）·
`topics.json`（主题页）· `sources.json`（信源）· `selection.ts`（门槛）· `prompts/*.md`（预筛/评分/写作/翻译/归组）· `brand/`。
`apps/` 与 `packages/` 基本不动。改完跑 `npm test`（138 项）+ `npm run typecheck`。

## 坑（都踩过，别重踩）

1. **`thinkhot.sh` 启动 web 时必须喂 `API_BASE_URL`**。web 由 `npx react-router dev` 起，不认 node 的 `--env-file`；
   不喂就掉到默认 `127.0.0.1:3001`，**那是 MedHOT 的 API**——页面照样 200、看着正常，其实渲染的是另一个站的数据。
   已改成 `start_web()` 用 `env` 显式注入 `API_BASE_URL`/`SITE_URL`/`WEB_PORT`。症状：`/topics/<slug>` 全 404 或页面显示医学主题。

2. **Crossref 的 `title` 是数组**，`json_list` 采集器的 `firstString` 只认字符串 → `titlePaths` 必须写 `["title.0"]`，
   否则整批源报 `no items mapped (check title/url paths)`。作者同理：`author.0.family` 只能拿到第一作者姓。

3. **`sources.json` 的配置键有白名单**（`packages/backend/src/sources/config-keys.ts`），填了不认识的键 seed 会整批拒收。
   `_aihot` 嵌套对象只允许 `initialBackfillLimit` / `initialBackfillMonths`；`intervalMinutesLock`、`maxItemsPerRun` 不支持（MedHOT 的 sources.json 里有，会卡住 seed）。

4. **`topics.grp` 有 CHECK 约束**，只认 `company`/`field`/`genre`。加新分组（如选题池 `pitch`）要先加迁移
   `database/migrations/0039_topic_group_pitch.sql`；前端 `apps/web/app/routes/topics.tsx` 的 `GROUPS` 数组是**硬编码**的，也要同步加。

5. **主题页路径是 `/topics/:slug`（复数）**，不须 `/topic/`。导航入口写在 `apps/web/app/components/shell/nav.ts`；
   父路径 `/topics` 已在 `MORE_PATHS` 里，子路径不用再加。

6. **首次导入的存量条目不进当天**：框架的「旧文不刷屏」规则把首轮回补的内容按原文时间归档，
   所以**建站当天日报是空的**（`composeDaily` 返回 `entries: 0`），首页仍会显示。不是故障。
   手动触发日报：临时脚本 `import { composeDaily } from "@aihot/backend/reports/compose"` + `beijingDate`（正式是每天 08:00 的 cron）。

7. **Crossref 并发超过 ~4 会被限流**（HTTP 429）。批量核验 ISSN 要限并发 + 重试。

8. **`scripts/collect.ts` 必须带源 id 当参数**（`npx tsx scripts/collect.ts <id> <id> ...`）；不带参数会静默什么都不做、退出码 0。
   脚本直接读 `process.env`，所以要先 `set -a && . ./.env && set +a`，否则会去连默认的 5432 报 ECONNREFUSED。
   返回字段是 `found` / `created` / `revised`（不是 `inserted`）。

9. **`npm run seed` 只加不覆盖**（输出 `N added, M already there`），所以补信源只要往 `industry/sources.json` 追加再 seed，
   不用清库重来，已有的分析结果不会丢。

10. **抓取会“整批扎堆到同一分钟”**——每次调间隔都会把 `next_fetch_at` 重置成“此刻”，于是 129 条源同时到期，
    `scheduleDueSources` 每分钟最多入队 40 条 + `FETCH_CONCURRENCY` 默认 8 → 同一分钟几十个抓取一起出网，
    直接撞回 429。修法：`collect.ts` 的 `phaseMinutes(id, interval)` 给每条源算一个稳定的相位，
    `adaptIntervals` 每天 04:20 连 `next_fetch_at` 一起重排；再加 `.env` 的 `FETCH_SCHEDULE_BATCH=12` / `FETCH_CONCURRENCY=4`。
    实测单分钟抓取从 40–47 降到 1–3，失败归零。测试见 `tests/source-throttle.test.ts`（禁止扎堆的断言）。

11. **`.env` 里含花括号/空格的 JSON 值必须加引号**。`LLM_EXTRA_JSON={"thinking":{"type":"disabled"}}` 用 `--env-file` 读没事，
    但脚本一旦 `set -a && . ./.env`，shell 会吃掉引号 → `{thinking:{type:disabled}}` → 模型调用报
    “LLM_EXTRA_JSON must be a JSON object”。同时：跑测试前要 `export DATABASE_URL="${DATABASE_URL%/*}/thinkhot_test"`，
    否则 `tests/setup.ts` 会因库名不以 `_test` 结尾而直接抛错（看着像“测试全挂”，实际只是库没指对）。

12. **推 GitHub 时，含 `.github/workflows/*` 的仓库需要令牌有 `workflow` 权限**，只有 `repo` 会报
    `refusing to allow a Personal Access Token to create or update workflow ... without workflow scope`，而且**整条 ref 被拒**。
    历史里只要有那个文件就卡死（不是删了文件就行）。两条真出路：①给经典令牌补勾 `workflow`（值不变，不用换令牌）；
    ②用 SSH 推（**不受这个限制**）——`ssh-keygen -t ed25519` 后把公钥贴到 github.com/settings/keys。
    不要为此改写历史：这两个仓库的价值就在于能跟 AIHOT 上游对比差异，改写 SHA 会断掉这条路。

13. **改了 `prompts/*.md` 之后，已有分析不会自动失效**。评分凭据（回执）按提示词版本哈希，改完提示词再跑
    `scripts/enqueue-analysis.ts --all` 就会真调用一次。但 `--all` 会**漏掉一批**（pg-boss 的 `singletonKey` 去重）：
    实测首批只覆盖 1784 条中的 1054 条。补漏用 `scripts/_requeue-stale-score.ts`——它按「最新一条分析不是当前评分版本」筛选，
    并用 `<id>:rescore` 当 singletonKey 绕过去重。**改完提示词必须用「不符条款数 = 0」来验收**，不要看队列空了就算完。
    重跑本身很便宜：提示词没改的那几步直接命中回执，只有改过的那一步真花钱。

14. **评分模型根本不做五轴加权计算**，别信提示词里的公式。要求「在心里算 sig/nov/cred/reson/act 再加权」+「只输出一个分数」
    的结果是 `{"attentionScore": 62}`，`completion_tokens: 7`——模型直接给一个直觉分。
    后果：分数被量化在少数几个值上（实测 62 占 18%、22 占 14%），源的最高分常常正好是 62.00。
    **所以校准必须按实测分布做，不能按提示词推导**；想让评分真正可控，得把五轴改成输出字段、加权在代码里算（未做，属架构改动）。

15. **`llm` 每分钟预算 300 次**（`budgets` 表），后台 worker 常年吃掉 293 次/分钟。跑 `eval-selection.ts` 之前
    **先 `./thinkhot.sh stop worker`**，否则大批 `Budget for llm exhausted (minute)`。
    另：`receipt_attempts.status` 的成功值是 **`received`**（还有 `completed`），不是 `ok`——用 `status<>'ok'` 统计会把成功全算成失败（踩过）。

16. **Crossref 里有「预注册占位稿」**：密歇根大学出版社的 Ergo、Philosophers' Imprint 会先把文章注册成
    `Title Pending 9683` 这种占位题名，且它们的 `published` 日期最新 → 按 `sort=published` 取 `rows=15` 时**全是占位稿**，
    入库后正文 389 字、摘要 0、评分 0.00。两处都要改：`config.ingestNoiseFilter.dropMarkersTitleOnly` 加 `"title pending"`（子串匹配），
    并把 `rows` 加大到 40 让真文章进窗口。改完要**直接 update 数据库里的 source.config**——`seed.ts` 是 `ON CONFLICT DO NOTHING`，
    对已存在的源不覆盖。验收：查 `articles.title ilike 'title pending%'` 为 0。

17. **跑完测试后 `export` 的 `DATABASE_URL` 会污染后续的服务进程——这个坑很隐蔽。**
    终端的环境变量是**跨命令保留**的，跑测试时惯常会 `export DATABASE_URL="${DATABASE_URL%/*}/thinkhot_test"`；
    之后再用 `./thinkhot.sh restart`，新进程就**继承了这个测试库**。Node 的 `--env-file` **不覆盖已存在的环境变量**，
    于是 api/worker 静默连上了空库：症状是 **`/api/site/topics` 返回 `{"topics":[]}`、所有 `/topics/<slug>` 都 404**，
    但 `/` `/all` `/hot` 照样 200（它们查的表在测试库里也有或走了降级），极难看出是连错库。
    重启用 **`unset DATABASE_URL && ./thinkhot.sh restart`**；验证用
    `ps eww $(pgrep -f apps/api/src/main.ts) | tr ' ' '\n' | grep '^DATABASE_URL='`——正常应该**什么都打不出来**（说明只用 `.env`）。
    另：测试库 `thinkhot_test` 的 `topics` 表是空的（题额由各测试自己插），所以主题页必 404。

## 发布到公网（免费、不用买域名）

**当前正式方案：静态快照定时推 GitHub Pages —— `./snapshot.sh`（launchd `com.thinkhot.snapshot` 每天 9:00 / 12:00 / 15:00）。地址固定：https://mrf3247.github.io/thinkhot/**，仓库 `MRF3247/thinkhot` 的 `gh-pages` 分支（推分支会自动开 Pages）。

- 快照范围（**全量**，2026-10-10 起）：`snapshot.py --sitemap --deep-all` —— sitemap 清单 + 列表分页里的全部条目页，实测 **3292 页**；引用站内资源缺失 0。
- 推送走 `push-pages.py`（默认 20MB/批 + 重试）：**必须分批**，一次推上百 MB 会被链路掐断（`send-pack: unexpected disconnect`）。`.publish/pages/.git` 不要删，否则下次全量重传。脚本：仓库根目录 `snapshot.py` + `push-pages.py` + `snapshot.sh` + `com.thinkhot.snapshot.plist`；日志 `.publish/snapshot.log`。
- 它会把生产 web 起在 3120（`SITE_URL=https://mrf3247.github.io/thinkhot`）；app 代码改动不用管，脚本发现 build 不在会自己重建。
- **完整配方、坑与可复用脚本见技能 `free-site-publishing`**（含 `/>` 被误当路径的血案、分批推送、签名图片落地、query → 目录映射）。

**旧方案（云隧道）已废弃**：`publish.sh` + cloudflared 快速隧道实测不可用——2026-10 本机到 Cloudflare 边缘 TCP/QUIC 全超时（网络/VPN 分流），地址每次重起都变，旧 `*.trycloudflare.com` 地址已永久失效。下面这段只当历史参考，别再用：

`./publish.sh build|start|restart|reload|web|stop|status|logs` —— 生产版 web（端口 3120，避开 MedHOT 的 3100）+ Cloudflare 快速隧道，公网地址写在 `.publish/url.txt`。公网流量打回本机 `127.0.0.1:3120`，页面照旧读本机 API/库，**数据更新自动生效，不用推送**。

改了前端代码后跑 **`./publish.sh reload`**（重建 + 只重启 web）；只重启 web 用 `./publish.sh web`。两者都不动隧道 → **公网地址不变**。

坑（都踩过）：

1. **不能用 dev server 对外**：`react-router dev` 有 host 白名单 → 隧道域名被 `Blocked request. This host is not allowed` 挡成 403。必须 `npm run build` + `node server.ts`（生产服务器无此检查）。
2. **`SITE_URL` 要在起进程时给成公网地址**（SSR 出来的 canonical/og:image 用它；浏览器里会用 `location.origin` 自纠）。
3. **`lsof -ti tcp:<端口>` 会把隧道进程一起杀掉**（隧道对本地端口有 ESTABLISHED 连接）→ 症状是地址变 530（Cloudflare 1033）、日志 `graceful shutdown due to signal terminated`。杀监听者要加 `-sTCP:LISTEN`。
4. **bash 里 `$VAR` 紧跟中文标点会被并入变量名**（`WEB_PORT）: unbound variable`）→ 中文句子里的变量写 `${VAR}`。
5. **快速隧道地址每次重启都换**，且地址先于边缘注册打印 → 要等日志出现 `Registered tunnel connection`。要固定地址：域名挂 Cloudflare 用命名隧道，或上 VPS（compose + Caddy 已备好）。
6. 公网会连 `/admin` 一起暴露（有登录，302 到登录页）。
7. **别把 `./publish.sh` 的输出管道给 `tail`/`head`**：web 由脚本 nohup 起在后台并继承管道写端 → 管道永不 EOF，命令一直挂到超时被杀，连带把 web 一起带走（症状：`status` 显示 web 不在、公网 502）。

## 大事榜（/hot）：按「值得看」排，不按讨论人数

榜单口径是**重要度**：取窗口内每个事件所有公开报道里**最高的 AI 精选评分**（`publications.score`）作为排序键，同分按时间新近兜底。热度（`story_heat_hourly`）降级成卡片徽章／附注，只作上下文。

- 规则版本：`HOT_RULE_VERSION = "importance-v1-maxscore"`（`packages/backend/src/events/hot.ts`）
- 窗口：`HOT_WINDOW_HOURS`（`.env`），ThinkHOT 不设 → 默认 **48 小时**（社科选题节奏快于医学）。
- 为什么改：原门槛「≥2 个独立信源 + 至少 1 个编辑部性质源」在思想类信源上几乎不可能满足（586 个事件里仅 3 个有第二家独立源）→ 长期空榜，是规则跟信源结构不匹配，不是故障。
- 立刻重算：`node --env-file=.env scripts/hot-now.ts`。
- **取分必须走 facts/fact_articles 关联，不能只看 `publications.story_id`**（很多行 `story_id` 为空，只按它筛会漏掉大半事件）。
- 前端文案「热点榜」已全部改叫「大事榜」（nav/more/story/agent/preprints/llms.ts/hot.tsx/HotTopics.tsx），行业包自己的「选题榜」入口（`/topics/pitch-strong`）保留不动。

## 信源现状（140 个，2026-10 逐个实测）

67 个顶刊走 Crossref（按 ISSN）· 6 个 OSF 预印本平台 · 4 个 arXiv 分类 · 7 个智库与数据 ·
13 家思想媒体 · 3 家学会与学术生态 ·
**7 个中文源**（澎湃思想市场 / 澎湃上海书评 / 爱思想 RSS / 知识分子 RSS / 中国社会科学网·中国哲学 / 经济观察报书评与观察家）·
12 家增补思想媒体（Works in Progress / Paris Review / New Atlantis / American Affairs / Liberties / The Nation /
The Conversation / Guardian Long Read / The Drift / Undark / JSTOR Daily / Science News）·
4 家学术生态（Blog of the APA / Retraction Watch / PsyPost / Futurity）·
4 家智库机构（Bruegel / Crisis Group / CSER / Santa Fe Institute）· 2 个 Nature 学科 feed ·
**11 个哲学源**（Daily Nous / Notre Dame Philosophical Reviews / The Philosopher / Philosophy Now / 3:AM Magazine /
Brains 心灵哲学博客 / The Splintered Mind / Australasian Journal of Philosophy / Ergo / Philosophers' Imprint / JAPA）；
哲学已有源：9 本顶刊（Mind、Noûs、Philosophical Review、Journal of Philosophy、Philosophy & Public Affairs、Ethics、Analysis、BJPS、Synthese）
+ arXiv hist-ph + Aeon/The Point/Noema/Crooked Timber/3 Quarks + 中国社会科学网·中国哲学 + Blog of the APA。

**哲学站里实测抓不到的**：PhilPapers 403 · PhilArchive 403 · Leiter Reports 403 · 斯坦福哲学百科无 RSS（是百科不是新闻源）·
Philosophy Bites 405（播客站）· Wiley 系（Ratio、European J. of Philosophy）被限流。

**实测抓不到、因此没纳入的**：Brookings、SSRC、Urban Institute、ASA、APA、Marginal Revolution、Cato、
Annual Reviews、Cambridge、Sage、Wiley（403 / TLS 被重置）；Dissent、Jacobin、Heritage（ECONNRESET）；
Journal of Political Philosophy、Diacritics（Crossref 两种 ISSN 都取不到）。
这几家的**本机网络**不通，换机部署时值得重测。

## 中文源抓法（实测可用，别再假设抓不到）

- **澎湃是 Next.js 服务端渲染，条目就在 HTML 里**，`parseMode: "html"` + `itemSelector: "div.ant-card"` + `titleSelector: "h2"` 实测抓到 20/19 条。
  2026-10 曾误判为「JS 渲染抓不到」并写进了交付文档，实际是自己没实测。
- 澎湃列表页日期是相对时间（"8小时前"），`parseLooseDate` 不认 → 必须配 `detail.publishedAtRegex` 去详情页抠 `"pubTime"`。
- 澎湃卡片里评论链接带 `?commTag=true`，选择器要写 `:not([href*="?"])` 排掉，否则产生一批带 query 的重复条目。
- 经济观察报列表链接是绝对 URL 且带 `http://`（非 https），白名单 `allowUrlPrefixes` 要按实际写。
- 中国社会科学网链接是 `./202609/xxx.shtml` 相对路径 → 必须配 `baseUrl`。
- 其他陷阱：Marginal Revolution 用 `/feed`（带斜杠 403）；The Nation 必须带 `?post_type=article`；Paris Review 用 `/blog/feed/`。
- **判断一个站能不能抓，唯一可信的方法是抓下 HTML 用 cheerio 跑一遍选择器数条目**，不是看它像不像 SPA。

## 评分偏低是怎么修的（2026-10 已校准，方法论可复用）

首轮：中文源平均 22 分、哲学源平均 27.7 分（160 篇仅 5 篇入选），T2 门槛 72 → 几乎全灭；英文/期刊源平均 40+。
两层病因，**都不是“门槛太高”那么简单**：

**第一层：`cred` 轴的定义把「纯思辨」列在低分端。** `prompts/selection-score.md` 原文：“…还是相关性分析、便利取样、单一案例、
纯思辨、个人立场”——任何纯理论工作在 `cred` 上被判死，而 `theory_argument` 的 `cred` 权重是 2，直接封顶。
另一条噪声规则“没有数据或材料支撑的宏大断言，`sig ≤ 3`”也会误杀严谨但无数据的哲学论文。
修法：`cred` 改成**按内容类型两种读法**（经验类看证据形态 / 论证类看论证质量：推理链、概念澄清、是否回应最强反驳），
并在「事件口径校正」末尾加两条：⑦不得因“没有数据”压低理论工作的 `cred` 与 `sig`；⑧但不能反向放水，术语堆砌仍要给低分。

**第二层：来源分级门槛与模型偏好叠加。** 配置本意是“媒体门槛更高”，但模型对媒体稿**系统性给低约 10 分**
（期刊条目读起来像“研究公告”，媒体长文不是）。实测 T2（思想媒体）538 篇里只有 7 篇过 72（1.3%）——而配置注释自己写着
“思想媒体正是本站的主要产出”。故 `selection.ts` 把 T2 对齐 T1_5 的 62。

**实测效果（1591 条真实稿件重跑）**：哲学源 5 → 29 条入选（1.9% → 11.5%）、思想媒体 6 → 70 条（1.3% → 13.4%）、
总量 445 → 633（+42%）。T1 / T1_5 未动。

**方法论要点**：
1. 改标准先做**前后对比实验**：`eval-selection.ts --gold .data/gold-phil.jsonl`（gold 全填 `decision: "either"`
   就能只拿分数、不靠人工标注），同一批稿子改前跑一遍、改后跑一遍。
2. 看的是**“涨的是不是该涨的”**，不是平均分：实测涨的正是严谨理论稿（“Reason is more than a tool” 22→50），
   而征稿启事 6→4、会员访谈 8→8 没被放水——这才叫定向修复。
3. 改动门槛后，用**“不符条款数 = 0”**验收：拿库里的 `selected` 与“按门槛重算”的结果对起来（实测 2012 对齐 0 不符）。

**已知未做（架构级）**：评分模型不做五轴计算（见坑 14），所以分数依然是直觉分、被量化在几个值上。
真正的修法是让模型输出五轴、加权在代码里算——那是改评分契约，动 `analyze.ts` 的解析，需单独立项。

## 选题榜（本站特有）

内容理解那一步额外判定「能不能做成一条面向大众的内容」（四条判据：能讲给外行听 / 有反直觉或冲突 / 有具体的人和场景 /
能接上当前公共讨论），打 `选题-强`、`选题-中` 标签，由 `topics.json` 里的 `pitch-strong` / `pitch-pool` 两个主题收口。
**零额外模型调用**。提示词见 `prompts/content-understanding.md`。

## 校准（已做一轮，仍可继续）

`selection.ts` 现行门槛 T1 58 / T1_5 62 / **T2 62**（2026-10 校准，T2 原为 72）。
再校准的方法：挑 100–200 条人工标「该选/不该选」→ `node --env-file=.env scripts/eval-selection.ts --gold .data/gold.jsonl --label "社科第二版"`。
先改 `prompts/selection-score.md` 的标准，再动门槛，改完记得重跑分析（见坑 13）。
拿真实稿件做前后对比集时，`publishedAt` **必须是完整 ISO（`+08:00` 而不是 `+08`）**，否则 `new Date()` 抛
`RangeError: Invalid time value`、整批 36 条全废（用 `json_build_object(..., published_at, ...)` 直接传 timestamptz 即可）。

`eval-selection.ts` **默认会把这次运行导入 SelectBench**（`selectbench_runs` / `selectbench_results`，admin 页面会显示），
所以做前后对比实验时加 `--no-import`，否则往评测库塞一堆参考记录。若已经误导（比如 gold 文件报错导致 36 案例全 error）：
`delete from selectbench_runs where id='...'`（`selectbench_results` 是 CASCADE）。
SelectBench 是给**人工标注 gold（该选/不该选）**用的准确率对比；全填 `either` 的无标注 run 在里面准确率恒为 0，别导入。
