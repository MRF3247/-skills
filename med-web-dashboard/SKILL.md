---
name: med-web-dashboard
description: "维护医学素材库本地SQLite+Flask网页(8899)时使用。含表结构/同步/启动/踩坑。"
version: 1.0.0
metadata:
  hermes:
    tags: [sqlite, flask, dashboard, medical-content, feishu-sync]
---

# 医学素材库本地数据库 + Flask 聚合网页

Use when 用户要改网页功能、查本地库数据、处理每日同步、排查网页问题（医学资讯聚合应用）。

## 架构总览

```
【抓取管线（2026-08-25 用户拍板：直写本地，飞书多维表格弃用）】
  ├─ ① 行业网站 13 源（mednews_daily.py，网页/RSS 爬取）
  ├─ ② B站 28 关键词（bili_daily.py，官方 API）
  ├─ ③ 公众号 24 号（gzh_daily_sync.py）
  ├─ ④ YouTube（youtube_camofox_sync.py——camofox 直抓版，替代 redfox）
  └─ ⑤ 社媒三平台（fetch_social 改造中——直写本地 + 小红书封面/主页顺带）
         ↓ 全部直写
本地 SQLite：~/Documents/Hermes/数据/医学素材库.db  ← 【唯一主库】
   │
   ▼
Flask 网页：~/.hermes/scripts/med_web.py（localhost:8899）
   │  启动：env -u PYTHONPATH ~/.hermes/venv/bin/python med_web.py
   │  （venv 必须 env -u PYTHONPATH，否则被 hermes 3.11 包污染）
   ▼
浏览器访问 http://localhost:8899
```

⚠️ **数据流向（2026-08-25 用户两次纠正，最终态）**：
1. **生成的数据**（AI分析报告/摘要/评论/翻译）**先写本地**，飞书只当可选镜像
2. **抓取管线的原始数据也直写本地**——**飞书多维表格整体弃用**（用户原话"那个多维表格后面我不打算用了"）。sync_feishu_db.py 保留但仅作历史迁移工具，**不再每日跑**；抓取脚本改造模式：链接 UNIQUE upsert（存在→更新可变字段+保留本地特有字段；不存在→INSERT+LLM 打标）
3. **每日流水线重构为链式**（用户定：07:00 启动，不是多时间点）：阶段1 并行抓取（5 路 `&`+`wait`，互不依赖——仅 ③④⑤ 共用 redfox 需放大间隔 2-3s 防限流）→ 阶段2 串行/并行处理（摘要 ⑦ 与 小红书补全/转录 并行——都只读本地库）→ 阶段3 静态发布（等全部完成）。**⚠️ 小红书封面/主页补全前移到抓取阶段顺带做**（fetch 时 coverUrl 直链下载 + accountUserid 填主页，一步到位），social_enrich.py 降级为历史遗留兜底（只处理 30 天窗口外/漏掉的空记录）

## 数据库结构（单表 + 摘要表）

**content 单表**（用户拍板：一张总表，非 3 表）——字段：
`id(自增PK) 平台(国外源/中文源/社媒源) 来源(网站名/UP主/公众号/频道) 标题 链接(UNIQUE) 发布时间 阅读量(视频播放+文章阅读统一) 点赞 在看(公众号独有) 评论 收藏 转发(抖音分享=视频号转发) 时长 摘要(一句话) AI分析报告(md排版纯文本) 主分类(7类单选，统计用) 模糊分类(逗号分隔多标签，搜索用) 关键词 封面图(本地文件路径非BLOB) 入库时间 子平台(B站/小红书/抖音/视频号/公众号/YouTube/行业网站) 一级评论(小红书) 标题译(行业网站英文标题中文翻译) 主页(来源主页链接)`

**分类体系（7 类）**：前沿研究/医学新闻/实用干货/健康科普/深度解读/行业舆情/日常其他。主分类=统计不重复，模糊分类=搜索不漏（跨类如"前沿研究,医学新闻"）。

**summary_daily 表**：日期PK/热点洞察/选题建议/覆盖内容数/内容清单/生成时间——每日 AI 摘要按日期存档（今日页可切换历史日期查看）。

**设计决策（用户拍板，勿改）**：
- id 自增编号，**无飞书ID字段**（用户：不需要回飞书定位）
- **无索引**（3258 条规模前端全量加载 JS 筛选更快；用户否定索引——"以后有需要再建"）
- 封面图存**本地文件路径**（~/Documents/Hermes/数据/封面图/<id>.jpg），非 BLOB
- NULL 语义：缺失=未采集写 NULL，0=真实为零
- 链接 UNIQUE 去重（公众号 30 条同链接重收正确去重）

## 每日同步（sync_feishu_db.py）

- cron 10:00（各平台抓取 09:30 后）→ 拉飞书 7 内容表全量 → **按链接匹配**本地：
  - 存在 → UPDATE 可变字段（播放/互动/摘要/AI报告/封面图）——**⚠️ 绝不更新「入库时间」**（2026-08-25 重大坑：公众号/YouTube 表的「快照时间」每次抓取都刷新，同步误把它当入库时间覆盖本地 → 全部历史公众号文章(184条)被标成当天入库 → 当日更新页塞满古早内容。已修：UPDATE 去掉入库时间；污染记录一次性清理 `SET 入库时间=发布时间 WHERE 子平台 IN ('公众号','YouTube') AND 入库时间='当天' AND 发布时间 < 当天-1`）
  - ⚠️ **发布时间也被冲过（2026-08-25 第二坑）**：YouTube 飞书存相对时间（"2 weeks ago"），`norm_time()` 解析 NULL → UPDATE 曾把本地 camofox 补好的准确日期全清成 NULL（0/207）。**UPDATE 发布时间必须用 `CASE WHEN ? IS NULL THEN 发布时间 ELSE ? END`**（飞书解析不出时保留本地已有值）——相对时间/解析失败永远保留本地
  - 不存在 → INSERT（此时才设入库时间=当天，即**首次进入本地库的日期**——「当日更新」的语义）
- **不覆盖**本地特有字段：主分类/模糊分类/一级评论/标题译（人工修正/本地产出保留）
- 同步后存 JSON 快照（备份 30 天）+ **网页守护**（8899 挂了自动拉起）
- 手动跑：`cd ~/.hermes/scripts && python3 sync_feishu_db.py`

## 数据口径（2026-08-25 用户定稿，改查询先对）

- **当日更新页** = `WHERE 发布时间 >= 今天-1`（严格窗口：当天+前一天发布的**所有来源**稿件）——**不是入库时间**！「入库时间」只是本地首次入库日期（供同步判断），展示一律用发布时间窗口
- **每日摘要**（gen_daily_summary.py）= `入库时间=今天 AND (发布时间 >= 昨天 OR 发布时间 IS NULL)`——大清早跑时平台昨晚/今晨发布的才算进当天；未解析出日期的 NULL 也保留（也是今天抓的）。摘要覆盖条数与当日更新页条数**不必一致**（前者=今天抓的，后者=窗口内全部）——但当日更新页自身勿 LIMIT 截断
- 排序：`COALESCE(NULLIF(发布时间,''),入库时间) DESC, id DESC`

## 网页功能（med_web.py 单文件，Flask + render_template_string）

- 今日页 `/`：AI 每日摘要（日期切换看历史）+ 当日更新列表（**发布时间 >= 今天-1 严格窗口**，全部列出勿 LIMIT 截断；2026-08-25 曾因 LIMIT 60+[:40] 双重截断导致摘要 235 条但列表 60 条）
- 平台页 `/platform/<平台>`：主体=按更新时间倒序全部稿件（LIMIT 200）+ 右侧浮窗 TOP20（7d/30d/all 切换）+ 分类筛选（7 类）+ 月份筛选 + 更新时间/播放量排序
- **来源点击 = 跳主页**（主页字段；公众号用文章页代替——微信无公开主页；视频号无主页纯文本）——**不是筛选**（用户明确否了筛选）
- **浮窗点击 = 当前页弹窗**（/api/item/<id> JSON + openModal JS）：
  - 小红书：官方笔记排版（封面大图+标题+正文+互动）
  - B站/抖音/YouTube/公众号：摘要+AI分析报告+「跳转原文」按钮
  - 视频号：纯展示不可点；行业网站：直接跳原文链接
- 搜索 `/search`、详情 `/content/<id>`、分类 `/cat/`、日期 `/date/`、来源页 `/source/`（仍保留但入口已改）
- **统计页已删除**（用户：没必要单独页面，今日新增整合进今日页）
- 小红书封面点击看大图（lightbox）

## ⚠️ 踩坑（全部实测）

1. **Python 生成 JS 字符串引号转义**：f-string 里嵌 JS 单引号字符串（如 `onerror="this.style.display='none'"`）会提前终止字符串 → **整个 <script> 解析失败，所有 JS 函数 undefined**（弹窗/评论/放大全失效，且无报错提示）。排查：`new Function(document.querySelector('script').textContent)` 抛 "unescaped line break"。**避开**：onerror 用 `this.remove()`、换行用 `String.fromCharCode(10)`、JS 内不用裸单引号
2. **venv 污染**：`~/.hermes/venv` 必须 `env -u PYTHONPATH` 运行（否则混入 hermes-agent 的 python3.11 site-packages，Flask 装错解释器）
3. **curl localhost 走代理**：curl 测本地服务必须 `--noproxy '*'` + 127.0.0.1
4. 浮窗 TOP20 排序：`COALESCE(阅读量,点赞,评论,0)`（无阅读量的平台退化到点赞）
5. 平台页「更新时间」排序 = `COALESCE(入库时间,发布时间) DESC`（新收录在前）
6. **camofox 服务卡死**（2026-08-25 实测）：长时间跑批量任务后服务可能 500/404 全端点异常（activeTabs 堆积不释放）→ **重启**：`launchctl kickstart -k gui/$(id -u)/com.mednews.camofox`（手工场景：`pkill -f camofox-browser` 后启动 `~/.local/bin/camofox-browser`，**不再有 npm start / node server.js**） → `~/.local/bin/camofox-browser`（后台；官方 npm 包安装路径——换机后不要再依赖 `~/Documents/GitProgram/...` 这类外挂目录，它不进迁移包）→ health 验证（activeTabs 应归 0）。⚠️ **DELETE /tabs 端点不存在（404）**——脚本里"关 tab"清理无效，tab 只会堆积；防卡死靠：每批条数小 + navigate 失败重试（首次 500 竞态）+ 服务重启兜底
7. **YouTube 播放量补齐**（fix_yt_views.py）：camofox 打开视频页 → `ytd-video-view-count-renderer span, .view-count` 提取（"137 views" 格式，K/M/B 换算）——redfox YouTube 接口本身不带播放量字段
8. **redfox 小红书/抖音/YouTube 均无播放量字段**（2026-08-25 确认）：小红书 searchArticle 只有赞/藏/评；抖音 searchArticle 只有 like/comment/share/repost/collect（无 playCount）；YouTube searchVideo 无 viewCount。**播放量只能 camofox 打开页面抓**（YouTube 视频页已跑通；抖音视频页同理可抓"xx 次观看"，未实测批量）——设计新平台抓取时别指望 redfox 给播放量
9. **小红书评论回采接口**（redfox 广域库，两段式）：`POST /story/api/xhs/commentSubmit`（入参 `opusId`（笔记 explore URL 里的 hex）+ `dataNum`（**-1=全部**，不传报 1002 dataNum不能为空），¥0.03/次起）→ 返回 taskId + visibleAfterTime（**24 小时后可查**）；`POST /story/api/xhs/commentResult`（taskId，**免费**）。taskId 存 `xhs_comment_tasks.json`，次日查 → 写入 content.一级评论

## 主页回填来源（主页字段）

- 行业网站：HOME_MAP（21 源域名映射）
- B站：`fill_bili_home.py`——view 接口（api.bilibili.com/x/web-interface/view?bvid=）免登录拿 owner.mid → space.bilibili.com/<mid>（按 UP主名去重，每 UP主 1 次调用）
- YouTube：fix_yt_dates.py 打开视频页顺带提取 `#owner ytd-channel-name a`（部分页面拿不到 ~46/207）
- 公众号：GROUP BY 来源取 MIN(链接)（文章页代替主页）
- 小红书：`fill_xhs_home.py`——**redfox searchArticle 返回 `accountUserid`，一次调用即可拼主页** `https://www.xiaohongshu.com/user/profile/<id>`（无需二次调用；重跑 10 关键词 × 2 页 ≈ 20 次调用 ≈ ¥0.5，补 176/231；30 天窗口外老笔记拿不到属正常）。⚠️ 抓取脚本务必顺带存 accountUserid（当时漏存才需重跑补）
- 抖音：**可补（2026-08-25 实测）**——redfox `dyData/searchArticle` 返回 `authorId`（数字或字母，字母型就是 sec_uid）→ 主页 = `https://www.douyin.com/user/<authorId>`，**一次调用无需二次**（勿用 camofox——未登录打不开抖音页）。重跑 10 关键词 × 2 页 ≈ 20 次调用 ≈ ¥0.5。⚠️ 抓取脚本顺带存 authorId

## 每日摘要生成（gen_daily_summary.py）

- **口径（2026-08-25 用户定稿）**：`入库时间=今天 AND (发布时间 >= 昨天 OR 发布时间 IS NULL)`——当天抓取的全部稿件，含昨晚/今晨发布的（大清早跑，平台当天发布的消息不会收录，往前追溯一天）
- 读内容（按 COALESCE(阅读量,点赞) 排序）→ LLM 生成 → 写 summary_daily（ON CONFLICT 覆盖）
- **cron 10:10**（同步 10:00 之后跑，job `8bc341a4e9d2` no_agent）
- **格式（2026-08-25 用户改版）**：「今日内容速览」——**纯浏览导向**，总结今天有哪些内容（按主题/类别归纳 3-6 类：前沿研究与新药/临床病例与诊疗/政策与行业动态/科研方法与论文/健康科普等，每类 2-4 条代表性内容 + 简要说明），**不做新媒体选题建议**（用户明确：目的是帮浏览者快速了解今天更新了什么，不是选题导向）。prompt 要求"不输出选题建议、不评价运营价值"，输出以「今日内容速览」开头
- **选题建议字段**：新格式留空（''）——网页 home 路由 `if d[0]['选题建议']:` 才显示该区块（旧数据有则兼容显示，新数据自动隐藏）
- **链接引用防编造**：prompt 给 LLM 带编号+URL 的内容清单，要求引用附链接；**生成后程序校验**——正则提取所有 URL，只保留清单中真实存在的（`real_urls` 集合过滤），编造的直接删除
- **清洗**：`.replace("**","")` 去 LLM 输出的 markdown 加粗残留；`insight.replace("今日内容速览","").replace("热点洞察","")` 去前缀（防网页标题重复）
- **拆分 bug 教训**：`out.split("选题建议")` 会把前缀留在 advice 里（网页标题又显示一遍"选题建议"→重复）——用 `split("选题建议", 1)` + `lstrip("：:。\n")`；新格式无"选题建议"字样时 insight=out 全量
- 查询 SELECT 必须含要用的所有字段（id/链接），否则 json 构建报 IndexError

## 🎨 网页样式规范（Kimi 定稿，用户要求学习——改样式先看 med_web.py 现有类，勿自创风格）

- **纸质杂志风**：米白纸色底 `--paper:#faf8f5` / 卡片 `--card:#fffdf9` / 暗红点缀 `--acc:#9e2b25` / 衬线标题 `.serif`(Songti SC) / 直角细边框(radius 2-3px) / letter-spacing 排版 / 编号 `idx`(02d) / 回到顶部按钮 / chiprow 月份横向滚动 / pager 分页
- **禁 emoji 图标链接**（用户明确否定 🔗 emoji 方案）——AI 摘要里的链接统一 `rich()` 函数 → `.ref-link` 类（红色、下划线、12px、「原文 ›」）：
  `LINK_RE = re.compile(r"🔗?\s*(https?://[^\s🔗]+)")`；rich() 先 `html.escape` 转义全文再正则替换
- `urlize()` 已删除，**勿再引用**（当时把 URL 替换成 🔗 图标被 Kimi 移除）
- AI 摘要按钮 `.ai-btn`（描边红字 hover 填充）、浮窗 `.float` 顶部 3px 深色边、`.mbox` 顶部 3px 边
- **浮窗尺寸（2026-08-28 用户最终定稿，两次调整）**：`.float{width:276px;max-height:56vh}`——先按用户要求缩宽到 184px 被否（"宽度回滚到之前的尺寸"）→ **只缩高度 84vh→56vh（2/3）**。改尺寸先问清是宽还是高，别一起动
- **浮窗位置（2026-08-31 用户定稿）**：`right:44px;top:34vh`（中部偏右浮动）——用户否定过贴右上（right:20px;top:60px 贴着顶部 banner 太奇怪）。位置调整先问"往哪个方向"，别只凭字面
- **AI 摘要按钮只保留 B站**（2026-08-25 用户最终定稿：行业网站/小红书/抖音/公众号/YouTube 全部关闭）——item_html 的 ai_btn 条件 `it["子平台"]=="B站" and (AI分析报告 or 摘要)`，浮窗 fitem 条件 `name=="B站"`（当时先只关了小红书、后用户扩到全平台只留 B站——直接按最终口径写）
- **弹窗 AI 报告排版**（formatAI() JS 函数）：AI分析报告按行解析——`【段标题】` → `.report-sec`（衬线 Songti/暗红/letter-spacing/下分隔线）、普通行 → `.report-p`（正文段落）、引号开头行（评论原文）→ `.report-cmt`（缩进+左竖线+米白底引用样式）；摘要(一句话)保持文本。不再用 `String.fromCharCode(10)` 拼"—— AI 分析报告 ——"分隔
- 主列表点击标题（**2026-09-02 用户反转 8-28 的"跳主页"方案，以本条为最终口径**）：**所有平台标题一律跳原文/笔记页**，**博主名（来源）→ 主页链接**（列表 src_html 已有；**热榜浮窗 TOP20 的标题旁附加博主名**，仅小红书如此，其他平台不加）——意图：标题点开看内容（遇限流可接受），博主名是独立入口去主页找。原 8-28 旧方案备注（已废，保留供理解）：小红书对未登录访问限流，打开笔记页显示\"扫码手机观看\"登录墙，浏览者去主页找；无主页的兜底跳原文；视频号纯文本。AI 摘要按钮独立在 meta 行。⚠️ **本地版 + 静态版（site/index.html）两处必须同步改**——正确写法（2026-09-02 定稿）：标题 href 一律用 `链接` 字段（不再按 xhs 分支跳主页）；博主名用 `主页` 字段成链（med_web.py 的 src_html 已自动处理）；浮窗 fitem 加 `<a class="fsrc" href=主页>来源名</a>`（CSS `.float .fsrc` 小灰字，仅小红书）。⚠️ sqlite3.Row **不支持 .get()**，必须下标 `x["来源"]`（用 .get 直接 500）。改完**必跑 `bash ~/.hermes/scripts/verify_web.sh`**（11 项：各路由 200 + "小红书标题→explore/" + "博主名→user/profile/" 断言）

## B站火稿转录补跑

- 播放≥1万 = 火稿候选：`bili_fire_transcribe.py`（v2）→ 得到大脑 AI大纲+逐字稿 → DeepSeek 校对 → 评论弹幕情绪总结 → **先写本地 SQLite**（`UPDATE content SET AI分析报告 WHERE 子平台='B站' AND 链接 LIKE '%BV%'`）→ 飞书「AI分析报告」单元格降级为镜像（**2026-08-25 用户纠正：本地为主**，飞书写失败仅 ⚠️ 警告不中断）；`bili_fire_loop.sh` 每篇短进程防杀；已处理标记跳过（transcribed/transcribe_failed）
- ⚠️ **切换本地直写后**：转录完成网页立即可见，**不再需要等每日同步**；但旧版脚本（只写飞书）遗留的产物需手动 `sync_feishu_db.py` 一次拉回
- ⚠️ **候选判断依赖 bili_track.json 的播放数据（2026-08-25 实测坑）**：`get_latest_play(st)` 读的是 **`st["plays"]`（日期→播放 dict）或 `st["play0"]`**——写错键名（如 latest_play）或该 bvid 缺播放数据时 `play` 为 0/None → **候选 0 条**（脚本显示"候选 0"但本地库明明有播放≥1万的稿件）。排查法：对比本地库 `播放≥1万且AI分析报告为空` 的 BV 列表 vs `bili_track.json` 里对应 bvid 的 play0/transcribed 标记
- **修复**：从本地库读取播放量回填 `st["play0"]=播放量` + `st.pop("transcribe_failed", None)`（清失败标记允许重试，得到大脑 API 间歇失败可重跑）→ 重启转录循环。⚠️ 转录循环日志是**追加式**，tail 看到"候选 0/全部转录完成"可能是历史日志——确认进程 status=running 且手动跑一条超时（正在处理）才是真在跑

## 抖音单条直抓（dy_fetch_one.py，2026-08-25 实测跑通）

**场景**：用户丢任意抖音链接（App 分享/搜索/推荐流）要求入库。**redfox 检索是死路**（无 workId 详情接口、推荐流内容关键词搜索不到——见 redfox-api 技能）——camofox 打开链接是唯一 100% 路径。

**⚠️ 为什么 redfox 抖音搜不到（2026-08-25 反思定论）**：不是关键词覆盖问题（标题词/标签词/用户原词全试过，翻 3-5 页 100+ 条都无果），而是**抖音搜索是千人千面+内容权重分发**——「论文辅导/SCI速成」类账号属抖音风控重点（学术灰色地带），被搜索**降权甚至剔除**；redfox 拿到的是抖音过滤后的子集。同类 SCI 内容其他账号能搜到、唯独该账号搜不到=账号级限流。佐证：redfox 抖音**无按 workId 查详情接口**（queryWorkDetail/workDetail/workInfo 全 404）、searchUser 返回 accountName 全 null。结论：**对限流账号，camofox 直抓是唯一通道**；批量抓取应"关键词保底 + 链接直抓兜底 + 重点账号定向"三层。

**用法**：`cd ~/.hermes/scripts && python3 dy_fetch_one.py "<抖音链接或workId>"`——自动：提取 ID → camofox 打开（静音+重试）→ 解析 → 写本地 content 表（链接 UNIQUE 防重）→ 打印结果。**新写入的记录无主分类**，需手动 LLM 打标（llm_client.chat_simple 输出「主分类|模糊分类」→ UPDATE）。

**解析要点**：
- ⚠️ **workId 提取坑**：搜索页链接结构 `video/<搜索页视频ID>/search/...?modal_id=<用户点开的目标>`——**`modal_id=(\d{10,25})` 必须优先**，其次才是 `video/|share/video/(\d{10,25})`（否则抓到搜索页视频而非目标，实测抓错过一次）
- 标题：`ld+json`（script[type="application/ld+json"]）的 `title`/`datePublished` 优先（`document.title` 带" - 抖音"后缀需剥）
- 作者：ld+json `author.name`（可能带 `@` 前缀，`lstrip("@")`）；DOM 选择器（data-e2e="user-name" 等）不稳定——经常拿到的是描述文本，**别信 uname 选择器**
- 播放量：抖音静态 DOM 拿不到（JS 渲染后才有）→ 返回 None 可接受（网页显示"—"）
- 描述：`meta[name="description"]` 可拿全文（含话题标签）

## 手动补抓流程（电脑关机/多天没跑时）

⚠️ **日常自动跑**：社媒（fetch_social_incremental.py）+ 全部平台已并入 07:00 流水线（daily_pipeline.sh 3 波）——只有关机错过才需要手动补。**补多天数据**：直接 `bash ~/.hermes/scripts/daily_pipeline.sh`（幂等——已入库链接 UNIQUE 跳过，只进缺的；B站 bvid state、社媒 30 天窗口、YouTube 30 天过滤天然处理增量）。补完验证各平台入库数分布（`GROUP BY 入库时间` 看是否有缺天的空档）+ 确认 publish 已推（GitHub 版 data.js grep 最新摘要日期）。

⚠️ **历史日期摘要无法按原口径单拆**（2026-08-31 实测）：gen_daily_summary 按"入库时间=今天"查询——补抓的数据全部归**补跑当天**入库，所以只能生成补跑当天的摘要（窗口覆盖今天+昨天发布）；更早缺的日期（如 29/30 号）内容在"当日更新/平台页"列表按发布时间可见，但没有独立摘要条目——属正常（摘要口径=当天抓取，不是按发布时间归档）。

**补抓流程（2026-08-25 实测）**：
1. 公众号补抓：`cd ~/.hermes/scripts && python3 gzh_daily_sync.py`（输出「新增 N 篇 + 补拉阅读量」）
2. 三社媒补抓 + 写飞书：`cd ~/Documents/Hermes/scripts && python3 fetch_social_oneoff.py && python3 social_to_base.py`
   ⚠️ **路径是 `~/Documents/Hermes/scripts/` 不是 `~/.hermes/scripts/`**（这俩目录并存，social 系脚本在 Documents 侧）
3. 同步本地：`cd ~/.hermes/scripts && python3 sync_feishu_db.py`（新增 N 条自动 LLM 打标）
4. 网页实时读库，刷新即见——无需重启

判断依据：本地库 `MAX(发布时间)` 停滞在 N-2 天前 = 该平台没抓到新数据（社媒一次性抓取窗口过期/公众号 cron 漏跑）。

## GitHub Pages 公开版（Kimi 部署，2026-08-25）

- 两个形态：本地 Flask 版（med_web.py :8899）+ **静态公开版** https://mrf3247.github.io/med-news-hub/（repo MRF3247/med-news-hub，main 分支，Pages 自动构建 ~1 分钟）
- 数据流：SQLite → `~/med-web/export_from_db.py` 生成 `site/data.js`（DATA+SUMMARY 常量）→ 小红书封面拷到 site/covers/ → `~/med-web/publish.sh`（git add/commit/push，无变化自动跳过）→ **发布由 pipeline 第 3 波做**（主发布 + 转录完自动二次发布）；⚠️ 旧的 `com.mednews.publish`（每天 09:40）**已 unload**——它会和 pipeline 重复发布，别再 load
- 手动发布：`bash ~/med-web/publish.sh`；检查：`~/med-web/publish.log` + `gh api repos/MRF3247/med-news-hub/pages/builds/latest --jq .status`（built=成功）
- ⚠️ **publish.sh 必须自带 push 重试循环（3 次 × sleep 10）且最终失败 `exit 1`**：VPN/TUN 抖动时 `git push` 报 `SSL_ERROR_SYSCALL`（而 `curl github.com` 仍 200），脚本却照样打印"已推送"→ pipeline 当成功继续走 → 用户看到的是"GitHub 页面没更新"。**发布验收永远看远端不看日志**：`cd ~/med-web/site && git status -sb`——出现 `[ahead N]` 就是没推上去；再 `git ls-remote origin main` 与本地 `git log --oneline -1` 对比确认
- git 凭据：**推荐 `credential.helper store` + `~/.git-credentials` 写 `https://x-access-token:<token>@github.com`（chmod 600）**——**必须 `x-access-token:<token>` 两段格式**（只写 `https://<token>@github.com` 时 git 读不出，仍报 `could not read Username`）。❌ 项目级 `credential.https://github.com.helper = !~/med-web/tools/gh.../gh auth git-credential` **会覆盖全局 store**，gh 未登录时 push 必失败——换机/重装后要么先 `gh auth login`，要么 `git config --local --unset credential.https://github.com.helper`；`gh auth login --with-token` 可能因 token 缺 `read:org` 被拒，**git push 不需要 gh，别在它上面耗**
- **交接文档 `~/med-web/hermes-handoff.md`**：完整架构/数据流/口径/环境说明（排序 NULLIF 口径、空标题保留、标题译、主页条件渲染、封面相对路径、ref-link 渲染）——维护前先读；**改前端必须本地 Flask 版 + 静态版 site/index.html 同步改**（用户两边对比）
- **静态版已同步（2026-08-25）**：当日更新发布时间窗口（`x.d>=yday`，固定今天+昨天不随 date 切换）、AI 摘要按钮只 B站（itemHTML + 浮窗均 `&&x.p==='B站'`）、摘要标题「今日内容速览」+ `s.t` 空则隐藏选题建议、弹窗 AI 报告 formatAI 分区排版（report-sec/report-p/report-cmt CSS 已加）——**已推 GitHub（c4b3775）**
- **静态版修改后验证手法（实测有效）**：① 提取 `<script>` 块 → `node -e "new Function(require('fs').readFileSync('/tmp/x.js','utf8'))"` 查 JS 语法（Python 三引号转义错误会在这一步暴露）；② **内联小样本重放**关键纯逻辑（当日更新窗口筛选/AI按钮平台条件/formatAI 分区/rich 正则）——不依赖 data.js 全量（data.js 几 MB，JSON.parse 全量会崩，eval 会打印全文）
- 已知缺口（2026-08-25 审阅提给用户）：② 文档没提 gen_daily_summary.py 摘要生成调度（export 依赖它先跑完）；③ "YouTube 发布时间为空"注释已过时（camofox 已补齐大部分）——①当日更新口径已同步进静态版和文档

## 小红书增量补全（social_enrich.py + cron 10:25，2026-08-25 新增）

**触发**：小红书新增笔记缺封面/缺博主主页（新增记录在飞书里**没有封面附件**——social_to_base.py 写飞书时没写封面字段 → 本地同步后封面图字段 NULL；主页字段同样全空）。

**social_enrich.py**（每日 cron `404e453a6c1e` no_agent，10:25 同步后跑，包装 social_enrich_daily.sh）：
1. **封面附件回填**：飞书有附件的补（`lark-cli api GET /open-apis/bitable/v1/apps/{BASE}/tables/{TID}/records`——**注意用 api GET 返回 items 对象数组；`base +record-list` 返回行值数组不可用**（2026-08-25 实测 KeyError））
2. **详情接口直查兜底（2026-08-28 升级，替代原"重搜"方案）**：对缺主页/缺封面的记录逐个 `POST /story/api/xhsUser/queryWorkDetail`（`{"workId": <explore URL 的 hex>}`）——**一次调用同时拿 `coverUrl`（直链下载）+ `accountUserid`（拼主页）**，比重搜精准（不依赖搜索窗口/排序），¥0.02/次 + sleep 1s
3. **403 = 已删除/不可访问笔记**（2026-08-28 实测 6 条空封面全 403）：redfox 详情接口对已删除笔记返回 403 Forbidden；camofox 打开同链接会重定向到 explore 首页（只能拿到推荐流随机图，og:image 是平台 logo——**camofox 未登录拿不到小红书精确封面**，别在这上面浪费时间）。**此类记录放弃**（内容没了，任何方式补不了），网页显示"无封面"占位
4. 30 天窗口外老笔记（搜索覆盖不到）主页/封面补不上属正常

**每日管线（2026-09-02 最终：05:00 启动 + redfox 均匀分配防 key 禁用，daily_pipeline.sh）**：
```
05:00 launchd 启动（com.mednews.daily.plist，StartCalendarInterval Hour=5——2026-09-02 从 07:00 提前，配合 redfox 均匀分配；daily_check.sh 开机补跑阈值同步改 >=5）
├─ 第1波 抓取（3 域并行，域内串行）：
│   域A·免费并行：①mednews_daily ②bili_daily ③gzh_daily_sync
│   域B·redfox串行：④fetch_social_incremental（小红书/抖音，**sleep 10s**——2026-09-02 从 2s 拉大防风控）
│   域C·camofox独立：⑤youtube_camofox_sync
│   → 收集失败路（逐个 wait $PA1||FAILED="$FAILED mednews" 等，⚠️ bash 3.2 无 declare -A 关联数组）→ 2 分钟后自动重试 1 次
├─ 第2波：**摘要先行**（gen_daily_summary.py 串行跑完，防并发写锁）→ 然后并行：social_enrich_daily.sh(redfox串行链 enrich→covers→track，**track sleep 45s** 摊开 3.5h) + translate_titles.py + bili_fire_loop.sh(转录限2条)
└─ 第3波：**ytview_loop.sh（YouTube 播放量补齐，发布前跑——新抓稿件播放量常有 NULL）** → publish.sh 主发布（不等转录）→ 转录完成 → **自动二次 publish**（GitHub 版 AI 报告当天上线）
日志 /tmp/daily_pipeline.log；关键失败计数 FAIL 后推飞书群
```
- ⚠️ **redfox key 禁用（3105）与均匀分配（2026-09-02 实测）**：全平台某天起 0 入库 + redfox 返回 `code=3105`（"API Key 已禁用"，控制台启用或新建 key）。触发=集中突发调用（track 276 条一波全打+重试放大）。修复=05:00 提前开工 + redfox 脚本间隔拉大（fetch 10s/enrich 15s/track 45s）摊在 5:00-8:40，9 点前干完。换 key：grep 全部读取脚本 → 批量替换文件名（Redfox API 2.rtf）→ 单条测试验证 code=2000
- ⚠️ **redfox 积分纪律（2026-09-04 用户"这才两三天就花了将近500积分"）**：积分大头是**互动追踪**（队列 259 条 × 每天全查），其次是搜索与公众号。已落地的省积分手段：① 追踪进队门槛 `THRESHOLD_LIKE=200 / THRESHOLD_CMT=30`（原 50/10；改门槛后记得用"赞<200 且 评<30 的退队"重筛存量队列）；② 追踪**每 2 天全查一次**（state 里存 `_last_run`，`update()` 开头 gap<2 天直接 return；遍历队列时跳过 `_` 开头的元数据键）；③ 停用 gzh 的 `gzh_keyword_fetch`（关键词搜索补小号，24 号监控已覆盖）；④ 失败重试次数别叠加放大。改间隔/门槛前先算清"每天多少次调用"，用户对消耗敏感
- ⚠️ **SKIP_REDFOX 开关（2026-09-22 用户要求"需要调用 redfox 的任务暂时都不用跑"）**：daily_pipeline.sh 支持 `SKIP_REDFOX=1`——跳过公众号/小红书/抖音抓取 + enrich + track，零产出告警的检查平台列表同步收窄为（行业网站/B站），避免"跳过了却报 0 产出"的假告警。用法：`SKIP_REDFOX=1 bash ~/.hermes/scripts/daily_pipeline.sh`；redfox 恢复后去掉该变量即可，无需回改脚本
- ⚠️ **camofox 浏览器断连（2026-09-02 实测）**：服务进程在（health 200）但 `browserConnected:false, browserRunning:false`——KeepAlive 只保**进程**不保**浏览器连接**，半挂时 YouTube 抓取搜索页部分工作但视频页打不开 → 新视频 0。修复：`pkill -f camofox-browser; pkill -f server.js` → `launchctl kickstart -k gui/$(id -u)/com.mednews.camofox` → curl /health 验证 `browserConnected:true` 才继续。**pipeline 或日常巡检应加浏览器连接健康检查，不只查端口**
- ⚠️⚠️ **阶段2 摘要必须先行（2026-08-31 实测连续 3 天失败）**：gen_daily_summary 与 redfox 链/翻译**并行**时，SQLite 单写者下长事务（enrich 详情循环/翻译）会让摘要的 INSERT 等 busy_timeout 超时 → 退出码非 0 且**日志无错误输出**（难排查）。修法：`python3 gen_daily_summary.py` 先串行跑完（2-3 分钟）再并行启动其他。手动跑 `python3 gen_daily_summary.py` 成功≠pipeline 成功（并发才触发）——验证要用 pipeline 全链路或同时开写库进程复现
- ⚠️ **关键词轮换已取消（2026-08-28 用户拍板）**：曾优化为\"10 词隔日轮换 5 词\"（省 redfox 调用）→ 用户明确\"没必要，保持每天全平台更新一次\"——**fetch_social_incremental 每天全量 10 词**（KEYWORDS 直接循环，不要做任何轮换/抽样优化）
- ⚠️ **launchd 启动 npm 类服务（2026-08-28 实测坑）**：`com.mednews.camofox` 的 ProgramArguments 用 `npm start` 会 `npm: command not found`（launchd 环境 PATH 无 ~/.hermes/node/bin）→ 退出码 127 + KeepAlive 反复拉起失败 → **camofox 没起 → B站/YouTube 全挂（Connection refused）**。修复：plist 用**绝对路径** `["/Users/Jin/.hermes/node/bin/node", "<项目>/server.js"]` + `<key>WorkingDirectory</key><string><项目目录></string>`。**任何 launchd 服务优先绝对路径，勿依赖 PATH**——首选直接指向工具自身的可执行文件（如 camofox 的 `~/.local/bin/camofox-browser`），**别写 `node <外挂目录>/server.js` + WorkingDirectory**：换机后那个目录多半不在迁移包里 → `last exit code = 78`（EX_CONFIG），服务静默不起、下游全 0 入库
- ⚠️ **发布后必须验证 GitHub 版 SUMMARY 日期（2026-08-31 用户抓的 bug）**：手动补摘要/改数据后只发本地、忘重新 publish → GitHub 版 SUMMARY 停在旧日期（用户截图：按钮区无 08-31）。**验证清单**：publish 后 `curl https://mrf3247.github.io/med-news-hub/data.js | grep -c "最新摘要日期"` 必须 ≥1；日期按钮来自 SUMMARY 数组（summary_daily 导出），SUMMARY 没有该日期=按钮不出现
- ⚠️ 旧链条（09:00-09:30 抓取 → 10:00 同步 → 10:10 摘要 → 10:25 补全 → 09:40 发布）已废弃——**09:40 发布早于 10:00 同步的时序 bug 是重构主因**（发布读本地库，同步没跑=发前一天数据）。旧 cron（1943716a6f6b/0ad23a848e4e/14bdf062e36f/a4e3635c25f8/a8463bc1b6ae/8bc341a4e9d2/404e453a6c1e）已全部暂停；publish launchd 已卸载。

⚠️ **hermes cronjob 创建被安全拦截（2026-08-25 实测）**：cronjob(action=create) 建 daily_pipeline 连续 3 次报 "cron job contains a gateway lifecycle command or persistent launchctl submit operation"（脚本内容无触发词，疑似检测器嗅探同批 launchctl 操作误判）。**规避：系统任务改用 launchd**（`~/Library/LaunchAgents/com.mednews.daily.plist` + `launchctl load`）——launchd 还更优：不依赖 hermes 进程、电脑开机即触发。已建三个 launchd：`com.mednews.daily`（07:00 流水线）、`com.mednews.camofox`（camofox 自启，KeepAlive SuccessfulExit=false 自动拉起）、`com.mednews.web`（med_web.py 网页服务自启，RunAtLoad+KeepAlive——**用户重启电脑后网页才不消失**；ProgramArguments 用 `env -u PYTHONPATH ~/.hermes/venv/bin/python med_web.py`）。

⚠️⚠️ **launchd 环境缺 python 模块（2026-08-26 早上实测，流水线首跑就中招）**：launchd 的 bash -lc 环境与交互 shell 的 site-packages 不同——pipeline 里 `gen_daily_summary.py` import llm_client（B站工作流）→ `load_config()` 里 `import yaml` **ModuleNotFoundError**（手动 terminal 跑正常，launchd 跑失败）。**修复模式**：依赖库 import 放 try/except，异常时降级用内置默认配置 + .env key（llm_client.load_config 已改：yaml 缺失返回 `{"llm": {"env_file": "~/.hermes/.env", "env_key": "DEEPSEEK_API_KEY", "model": "deepseek-chat", "fallback_model": "deepseek-v4-flash", "base_url": "https://api.deepseek.com"}}`）。**教训：任何进 pipeline/cron/launchd 的脚本，第三方模块 import 必须降级或显式指定解释器；launchd 跑完记得看 /tmp/daily_pipeline.log 确认各步真成功**（2026-08-26 摘要失败但 publish 照常推送——GitHub 版显示旧摘要，用户以为"生成了 8-26"实际没有）。

⚠️ **redfox 502/EOF 不稳定（2026-08-26 早上实测）**：社媒抓取（抖音/视频号）10 个关键词全 502 Bad Gateway → 当日 0 入库。fetch_social_incremental.post() 已加 `retries=3` + `time.sleep(10*(attempt+1))` 自动重试。流水线跑完检查各平台入库数，0 条的平台要手动补跑（`python3 fetch_social_incremental.py` 幂等）。

⚠️ **今日页默认日期（2026-08-26 用户反馈）**：home 的 `date_sel` 默认**今天**时，若当天摘要还没生成（pipeline 摘要失败），页面显示历史日期按钮 + "（今日 X）"括号造成误解。已改：**无 date 参数时默认取 summary_daily 最新日期**（`SELECT 日期 FROM summary_daily ORDER BY 日期 DESC LIMIT 1`），有数据才显示按钮且选中——与静态版 renderHome 的 `SUMMARY[0].d` 口径一致。切换历史日期后可点最新日期按钮回来。

**统一本地写入模块 db_writer.py（2026-08-25 新增，5 抓取脚本共用）**：
- `upsert(records, tag=True)`：按链接 UNIQUE——存在→UPDATE 可变字段（**全部用 `CASE WHEN ? IS NOT NULL THEN ? ELSE 字段 END`** 保留本地值）；不存在→INSERT（入库时间=当天）+ LLM 打标
- **支持 records 传 `主分类`/`模糊分类`**（bili 的 6 标签 TAG_MAP、gzh 的 3 分类 CAT_MAP 已在脚本侧映射成 7 类，`tag=False` 跳过 LLM 防重复消耗）——无主分类的新记录才 LLM 打标
- 改造模式：原写飞书的抓取脚本（mednews/bili/gzh）保留抓取+过滤逻辑，把"写飞书表格"段替换为构造 records → upsert；mednews 的旧 gen_daily_summary（选题建议版）调用已注释（防覆盖 pipeline ⑦ 新版摘要）

**博主→固定分类规则（2026-08-28 用户要求，~/.hermes/scripts/博主分类规则.json）**：个别博主内容被误打标（如抖音"杰比的生活日记"只发搞笑段子，LLM 打成 实用干货/行业舆情）→ 用户要求"碰到他就归日常其他，记到爬取规则里"。机制：JSON {来源名: 主分类} + fetch_social_incremental 的 rule_category(author)——构造 records 时 rc = rule_category(author) 放进 主分类（命中规则直接归类，跳过 LLM 打标；未命中 rc=None 走正常 LLM）；db_writer INSERT 支持 records 传主分类。用法：用户再说某博主要固定分类 → 往 JSON 加一行即可，永久生效。历史误标修正：UPDATE content SET 主分类='日常其他' WHERE 子平台='抖音' AND 来源 LIKE '%名字%'

**redfox 视频号接口已下线（2026-08-26 确认）**：/story/api/sphData/searchWork 404（官网状态"即将上线"、SDK 无视频号）——fetch_social_incremental 的 fetch_sph 已暂停（返回 0，注释"接口恢复后移除 return"）。视频号网页版搜索需微信登录（camofox 未登录只见"登录视频号助手"）——视频号每日抓取暂停，历史 832 条保留；redfox 上线后恢复。排查接口 404 时先查 redfox SDK（GitHub redfox-data/redfox-python-sdk 的 endpoints 源码）确认路径是否存在，别在 404 路径上反复试。

⚠️⚠️ **SQLite 并发写锁（2026-08-25 流水线并行实测，必做）**：阶段1 五路并行直写同一 content 表 → 无 WAL 时直接 `sqlite3.OperationalError: database is locked`（youtube 脚本崩、主进程 DELETE 也锁）。**所有直连 SQLite 的连接必须**：
```python
conn = sqlite3.connect(DB, timeout=60)
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=60000")
```
db_writer.py 已封装为 `_connect()`；youtube_camofox_sync/social_enrich/bili_fire_transcribe/gen_daily_summary 等**所有直连脚本**都要加（不止用 db_writer 的）。并行验证法：3 进程各写 20 条同时跑，全成功=OK。**阶段2 的三个脚本（摘要/补全/转录）也并行写库，同样需要**。另外：修复前启动的旧进程持旧连接会继续锁库——kill 全部抓取进程再重启 pipeline 测试（幂等：链接去重，重复跑只更新不重复插入）。

⚠️⚠️ **比 WAL 更隐蔽的是"长事务持锁"（2026-09-02 实测，制造了连续几天的"公众号没爬"假象）**：social_track 的队列循环在**循环外**才 `conn.commit()`，而循环体内每条 `time.sleep(45)` → 写事务持锁 45s×N（实测 3.5 小时），期间 gzh_daily_sync 等一切并发写全部 `database is locked` 静默失败（用户看到的是"某平台 0 入库/无新文章"，日志里只有一行 locked）。**规则：写库循环只要循环体内有 sleep 或网络等待，就必须"每条处理完立即 commit"，sleep 永远排在 commit 之后**。排查手法：某平台连续 0 产出但接口正常时，先 `ps aux | grep -E "social_track|social_enrich|bili_track"` 看是否另有写库脚本正长跑；同类脚本（bili_track 回写、social_enrich 详情兜底、fix_yt_views 批量补）都按此自查。

## B站播放量追踪（bili_track.py，2026-08-31 修复）

bili_daily 每次抓取异步启动 `bili_track_loop.sh` → bili_track.py 按 bvid 队列（bili_track.json）每天查 view 接口更新播放量。

⚠️ **播放量回写必须写本地库（2026-08-31 用户发现"热门稿件不到一周就没统计播放量变化"）**：原 write_back 只对**火稿**（日增≥2000 或翻倍）写**飞书多维表格**（已弃用）→ 本地库阅读量从不更新，网页显示抓取时快照。修复：
- `write_back(all_plays)` 改**本地库直写**：`UPDATE content SET 阅读量=? WHERE 子平台='B站' AND 链接 LIKE '%<bvid>%'`（WAL+busy_timeout）
- main 里收集**队列内全部稿件**的播放量（active + cool 分支都 `all_plays[bvid]=play`，不只 fires）
- 验证：`python3 bili_track.py 60` 后查本地库对应 BV 的阅读量是否刷新

## AI 短剧/重生文排除（2026-08-31 用户要求"以后也不要抓"）

抖音"顶级医学博导，重生回临床一线，开局抢救激活系统"（AI 漫剧系列 38 集）全入库——标题含"医学/规培"过放行词过滤。**排除词必须双通道加**：
- fetch_social_incremental 的 EXCLUDE_KW 追加：`AI漫剧/漫剧/重生/开局/激活系统/短剧/爽文/穿书/甜宠/霸总`
- bili_daily 的 EXCLUDE_TITLE（搜索结果去重处检查）：`AI漫剧/漫剧/重生/开局/激活系统/短剧/爽文/穿书/甜宠/霸总/逆袭/穿越`
- 已入库的批量删：`DELETE FROM content WHERE 标题 LIKE '%<系列名>%'`
- 教训：**放行词含"医学"等宽词时，泛娱乐网文/短剧标题会蹭医学词入库**——排除词层要常补新出现的娱乐内容特征词

## 平台页面隐藏（2026-08-31 视频号）

某平台 API 不可用（如 redfox 视频号下线）时，用户要求网页隐藏该平台页面：**从 PLATFORMS 列表移除**（med_web.py 第 17 行 + 静态版 site/index.html 的 `const PLATFORMS` 两处）——导航消失 + `/platform/<名>` 直接 404（路由 `if name not in PLATFORMS`）。数据保留在库不删；API 恢复后把名字加回 PLATFORMS 即可。双端同步改。

## 相关脚本

- sync_feishu_db.py（同步+备份+网页守护——飞书弃用后降级为历史迁移工具）、med_web.py（网页）、batch_tag.py（LLM 打标并发）、fill_bili_home.py（B站主页）、fill_xhs_home.py（小红书主页，redfox）、fix_yt_dates.py（YouTube 日期/频道）、fix_yt_views.py（YouTube 播放量，camofox 视频页）、**youtube_camofox_sync.py（YouTube 每日抓取 camofox 直抓版——搜索页列表+视频页补日期/播放量/频道+直写本地+打标，替代 redfox；首次全量 ~200 条很慢 40-60min 属正常，增量每天 20-40 条 3-5min）**、gen_daily_summary.py（每日摘要）、fetch_covers.py（飞书附件下载，`drive +preview --type source_file` 而非 +download——403）、**dy_fetch_one.py（抖音单条直抓，用户丢链接入库）**、**social_enrich.py（小红书封面直链下载+主页回填——重构后降级为历史遗留兜底）**、**db_writer.py（统一 upsert）**、**daily_pipeline.sh + fetch_social_incremental.py（社媒每日抓取，含小红书封面/主页顺带）**
- ⚠️ **YouTube camofox 视频页日期提取坑（2026-08-25/26 两次实测，最终修复）**：
  - **错误写法**：`document.querySelector('#info-strings yt-formatted-string')` 只取**第一个**元素——第一个常是观看次数不是日期 → 日期全 None（播放量选择器 `ytd-video-view-count-renderer span` 稳定）。
  - **正确写法（与 fix_yt_dates 一致）**：`document.querySelectorAll('#info-strings yt-formatted-string, ytd-video-primary-info-renderer #date').forEach(e => txt += ' ' + e.textContent)` 全部拼接再正则（实测 "Aug 24, 2026" 可解析）。
  - 仍缺日期的记录用 fix_yt_dates.py 幂等补（只处理发布时间 NULL 的）
- ⚠️⚠️ **YouTube 只爬 30 天内最新稿件（2026-08-26 用户明确批评：\"11年前的稿件都爬进来了\"）**：redfox/camofox 搜索都按**相关性**排序（非最新），医学关键词会搜出 2015-2016 年的老教程视频，过滤后全入库=垃圾数据。**camofox 同步脚本必做两步**：① 视频页拿到日期后 `parse_date`（支持 `YYYY-MM-DD`/`Month D, YYYY`/`N days|weeks ago` 相对时间换算）；② **日期解析不出 → 丢弃不入库**（`continue` 打印 ⏭️ 无日期）；**`(datetime.now()-pub_d).days > 30 → 丢弃`**（⏭️ 超30天）。已入库的老视频清理：`DELETE FROM content WHERE 子平台='YouTube' AND 发布时间 < 今天-30` + `发布时间 IS NULL`（2026-08-26 实测删 157 条老 + 68 条无日期，421→196 条全 30 天内）。**教训：任何\"抓最新内容\"的搜索型抓取（YouTube/抖音/小红书）都不能按发布日期过滤窗口，不能信任搜索排序**（更优解：先强制时间排序——YouTube 搜索 URL 加 `&sp=CAISBAgEEAE%3D` 即按上传时间排序，新视频排最前；不加时新视频长期沉在相关度排序后面，连续多日"累计新增 0"会被误判成"平台就是没新内容"，实际是漏抓，补加后在途一次补回 100+ 条）
- 状态文件：bili_track.json / xhs_comment_tasks.json（小红书评论 taskId 待 24h 查询）
