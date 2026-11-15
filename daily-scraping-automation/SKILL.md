---
name: daily-scraping-automation
description: "Use when 搭建每日自动抓取/监控管道（定时爬取→入库→推送）。"
version: 1.0.0
metadata:
  hermes:
    tags: [cron, scraping, camofox, anti-bot, feishu, bitable, pipeline]
---

# 每日定时抓取管道（daily-scraping-automation）

搭建「每天自动抓取 → 处理 → 入库 → 推送」的任务时使用。本 skill 沉淀 2026-08 实测跑通的架构（医学资讯 8 源 + B站 22 关键词稿件，双 cron 每日运行）。

## 架构演进（2026-08-26 实测：流水线 + 直写本地，弃飞书多维表格）

多平台（≥4 路）每日抓取时，从「cron no_agent 单脚本 → 飞书多维表格」演进为**单入口 launchd 流水线 + 直写本地 SQLite**（用户拍板：飞书多维表格弃用，所有数据先写本地）。实测拓扑：

```
launchd com.xxx.daily（StartCalendarInterval 07:00，bash -lc 跑 daily_pipeline.sh）
├─ 第1波 抓取（3 域并行，域内串行）：
│   域A·免费通道并行：网页爬取/官方API 路（互不冲突）
│   域B·redfox 串行：社媒平台（任何时刻全流程只有 1 个 redfox 任务在跑）
│   域C·camofox 独立：单浏览器独占（如 YouTube）
│   ↓ 失败路 2 分钟后自动重试 1 次（幂等：链接 UNIQUE 防重复）
├─ 第2波 处理（redfox 与 LLM 分域并行）：
│   域B·redfox 串行链：enrich → covers → track（顺序执行，绝不并发）
│   域D·LLM 限 2 路：摘要 ∥ 翻译（不叠加得到大脑/慢 API）
├─ 第3波 发布：
│   ① YouTube 播放量补齐（ytview_loop，见下方"YouTube 播放量需定期补跑"）
│   ② publish 主发布（不等转录，早上尽早上线）
│   ③ 转录（限 2-3 条/天，慢任务后置）
│   ④ 转录完自动二次 publish（静态版当天也有 AI 报告）
失败计数 >0 → 推飞书群告警
```

> 现状：B站稿件日报（`bili_daily.py`，22 关键词 → LLM 打标 → 播放量追踪 → 推群）已按用户要求下线，不再随流水线跑。要恢复就把四个耦合点改回来（见下「下线流水线里的一路」）。

**3 波编排原则（2026-08-26 用户认可）**：冲突的本质是**共享资源**不是任务类型——按资源域分组（免费通道/redfox/camofox/LLM），域间并行、域内串行。redfox 全并行实测 502 全挂；LLM 全并行实测 deepseek 慢响应 + 得到大脑失败率上升。

### 为什么用 launchd 而非 hermes cron
- **不依赖 Hermes 进程**：launchd 是系统级，电脑开机即触发；cron 要求 Hermes 应用在跑。
- **长流水线**（2-3 小时含 B站 28 关键词）远超 cron 单脚本友好时长；launchd 无超时。
- cronjob create 可能被安全拦截（"gateway lifecycle command"误判，多发生在同会话刚做过 launchctl 操作时）——此时直接 launchd 是正路。
- plist 写法：`ProgramArguments` = bash -lc + 脚本路径；`StartCalendarInterval` Hour/Minute；日志 StandardOutPath/StandardErrorPath。
- **launchd 环境坑**：`bash -lc` 环境下 python 可能缺用户 pip 包（实测 `import yaml` 失败导致摘要任务静默失败）——依赖库（如 llm_client 读配置）要加 **try/except 降级**（yaml 缺失用内置默认配置 + .env key），不要在 launchd 脚本里依赖 site-packages。
- **launchd 找不到 npm/node（实测 camofox 全挂）**：`ProgramArguments` 用 `npm start` 时 launchd 环境报 `npm: command not found`（用户 shell 的 PATH/nvm 不加载）→ 服务静默不起、下游全挂（B站/YouTube 0 入库）。**修复：ProgramArguments 写绝对路径**——首选指向工具自身的可执行文件（如 camofox 官方包 `/Users/<user>/.local/bin/camofox-browser`），**别写 `node <外挂目录>/server.js` + WorkingDirectory**：换机后该目录不在包里 → `last exit code = 78: EX_CONFIG`，kickstart 也救不回来（用户隔天才发现"怎么没更新"）。排障：`launchctl print gui/$(id -u)/<label> | grep "last exit"` → 78/127 都指路径或权限问题 → 让 plist 的命令与手工跑通的命令完全一致。启动后 curl 健康端点验证，别只信 launchctl list。
- **write_file 重写 shell 脚本后执行位丢失 → launchd exit 126（2026-09-02 实测，当天整条流水线没跑）**：`bash -lc <script>` 的语义是**把脚本路径当 -c 的命令字符串执行**（不是读文件执行）→ 脚本必须有**执行权限**（-rwxr-xr-x），write_file 默认写 -rw-r--r-- → 当天 05:00 launchd 触发但 `last exit code = 126`（cannot execute），全天无日志、用户早上看到完全没更新。**修复：write_file 重写任何被 launchd/cron 调用的 .sh 后必须 `chmod +x`**。排查：`launchctl print gui/$(id -u)/<label> | grep "last exit"` 看 126/127 → `ls -la` 查执行位。同会话内 launchctl kickstart（立即触发一次）+ 手动 bash 跑会**并行双实例**（track 双开打同一个付费 API + 状态文件竞争）——补跑只用一个入口。

### 多进程并行直写同一 SQLite（关键坑）
- 多路抓取并行写同一库 → `database is locked`（WAL 未开启时全库写锁）。
- **修复**：所有写库连接 `PRAGMA journal_mode=WAL; PRAGMA busy_timeout=60000`（每个脚本/每个连接都要，包括后续阶段与抓取并行的处理脚本）。
- 统一写入模块（db_writer.py 模式）：按**链接 UNIQUE upsert**——已存在→更新可变字段（阅读量/互动/封面/主页），**不覆盖**本地特有字段（主分类/模糊分类/一级评论/标题译/入库时间）；不存在→插入+LLM 打标（或 records 自带主分类则跳过 LLM）。
- **写 summary 表的任务（每日摘要）要先于写 content 的任务执行（2026-08-31 实测）**：阶段 2 并行（摘要 ∥ redfox 补全链 ∥ 翻译）时，redfox 链/翻译持续写 content（长事务），摘要的 INSERT OR REPLACE 写 summary_daily 要等数据库级写锁 → busy_timeout 60s 超时 → 摘要进程静默失败（日志无 traceback，只有 `❌ 每日摘要失败`；手动跑却成功——典型并发写锁特征）。修复：摘要**串行先行**（2-3 分钟，跑完再并行其他），或给摘要脚本单独更长 busy_timeout。

### 跨天补抓（电脑关机错过 N 天定时）
开机后发现多天 cron 没跑（关机）→ 直接跑完整流水线即可补：各脚本按**链接 UNIQUE 幂等**，已入库的自动跳过，只有缺失日期区间的新内容进来（全平台同理）。验证：按 `入库时间` 和 `发布时间` 两个维度分布核对（补抓后入库时间都集中当天，发布时间分布覆盖缺失的几天）。注意 YouTube 30 天过滤与社媒 30 天窗口对\"补更早的\"天然限制——补抓只保证最近窗口内的数据，更早的拿不到是正常的。

### 抓取平台要点
（换机后的恢复清单：外挂代码目录缺失、launchd exit 78、git 凭据重配、双机推送分叉 → 见 `hermes-backup-migration` 的"换机后首次验收与排障"）
- **YouTube 用 camofox 直抓而非 redfox**（redfox 缺发布时间/播放量，还得二次补；camofox 一次拿全且免费）——详见 `references/youtube-camofox-scraping.md`（日期提取选择器陷阱、30 天过滤、老视频清理）。
- **搜索页 URL 必须带「按上传时间排序」参数（实测漏抓重灾区）**：YouTube 搜索默认按相关度排，高播放老视频霸占前排，**窗口内的新视频沉底、整段漏抓**（表现为连续多日「累计新增 0」，隔着几天才发现 9 月上旬整段没入库；改排序后一次补回 100+ 条）。固定写法：`https://www.youtube.com/results?search_query=<kw>&sp=CAISBAgEEAE%3D`（`sp=CAISBAgEEAE` = 按上传日期排）。同一规则适用于其他平台的搜索页：默认排序跑出来「总是 0」时，先换排序方式再下「确实没新内容」的结论。
- **redfox 接口可能下线**：某平台接口 404 时先核对官网（redfox.hk 导航"即将上线"）与 GitHub SDK（redfox-data/redfox-python-sdk），确认后暂停该分支并注释，接口恢复再开；不要反复试错。
- **redfox 502/EOF**：3 路并行共用 redfox 时把请求间隔放大到 2-3s，且 post 加重试（502/EOF sleep 10s × 3）。
- **redfox 接口路径快照（2026-08-26 实测）**：小红书作品详情=`/story/api/xhsUser/queryWorkDetail`（workId，¥0.02）；抖音作品详情=`/story/api/dyData/queryWork`（workId；`queryWorkDetail`/`getWork` 均 404 别试）；视频号 searchWork 已下线（官网"即将上线"）。接口路径变了先从 GitHub SDK（redfox-data/redfox-python-sdk，`redfox/endpoints/*.py` 源码里 grep `/story/api/`）找，别猜路径。
- **Agent Key（MCP，agentkey 工具）可作社媒数据应急备用通道**：有小红书全套（Rnote 详情/搜索/评论/用户，详情接口返回封面）等 2000+ 工具目录（find_tools 语义搜索 + describe_tool 看参数/成本 + execute_tool 执行，`agentkey_account` 免费查余额）。免费计划额度很小（实测仅个位数 credits，Rnote 详情 cost=2/次）——**撑不起每日批量**，只适合少量应急（如某平台 redfox 挂掉时补几条）；批量前先查余额。

### redfox API key 被禁用（3105）→ 均匀分配调度（2026-09-02 实测）
**症状**：某天起小红书/抖音全 0 入库，但 redfox 返回 `code=3105`（不是 2000）——**3105 = "API Key 已禁用"**（redfox 错误码文档，控制台密钥管理页可启用或新建）。不是没新内容，是抓取通道被掐。**别按"没钱了"处理**：3105 是 key 状态码（禁用/风控），余额耗尽是另一回事——先让用户登控制台看密钥状态页；**用户确认前不要擅自停掉依赖该 key 的任务**（公众号/社媒/追踪共用同一个 key，停用范围必须让用户拍板）。

**触发原因分析（推断）**：付费 API 也带风控——我们**集中突发调用**（早上 07:00 一波：追踪队列 276 条全查 + 搜索 + 补全详情 ≈ 500-800 次/天，失败重试还 ×3 放大）被判定异常流量。8-31 补抓 + 追踪队列膨胀（162→276）后调用量陡增是触发点。

**修复/预防（用户拍板方案：每天全量一次但均匀摊开）**：
- **启动提前到 05:00**（launchd StartCalendarInterval Hour=5），9 点前干完
- **redfox 脚本间隔拉大均匀分配**：社媒抓取 sleep 10s（原 2s）、补全详情 sleep 15s（原 1s）、互动追踪 sleep 45s（原 1s）——追踪 276 条 × 45s ≈ 3.5 小时摊在 5:00-8:40，平均 ~1.5 次/分钟，风控触发概率大降
- **量估算**：总调用量 / (窗口分钟数) = 所需间隔；追踪队列是大头（每条 sleep 决定总时长），队列涨超 ~350 条会超 9 点——需动态调间隔或调高进队门槛
- **转录限 2 条**保 9 点前收尾；转录本身在二次发布环节（主发布不等转录）
- **key 更换流程**：用户给新 key 文件（如 "Redfox API 2.rtf"）→ `grep -ln "旧文件名" ~/.hermes/scripts/*.py ~/Documents/Hermes/scripts/*.py` 找全部读取点 → 批量替换文件名（同名字符串替换，注意大小写）→ 单条 API 测试验证（`code=2000` + 返回条数）

### 整批任务必须在时间上散开：给每条源一个固定相位（防限流）

**症状**：定时管道“整体在跑”，但限流频发（Crossref 429）、失败集中在同一分钟、成功率忽高忽低。

**根因（通用机制）**：调度器只存一个「下次到期时刻」。每次改动抓取间隔（每日自适应调间隔、首次 seed 导入）
都把到期时间重置成“此刻”→ 整批源（实测 129 条）在同一分钟全部到期，一分钟内 40–47 个请求一起出网。

**修法**：不要用「重置为 now」，给每条源算一个**落在自己间隔内的固定相位**
（稳定散列，如 `FNV-1a(id) % interval`），写间隔时**同时**写 `下次到期 = now() + 相位`。
这样 N 条源自动摊在 interval 分钟上，平均每分钟 N/interval 条，且相位可重现。

**配套节流旋钮**（进程启动时读，改完必须重启）：全局并发数 8→4、单分钟入队上限 40→12。

**验收三件**：① 按 `date_trunc('minute', next_fetch_at)` 分组看**最挤一分钟**的条数（应是个位数；实测 40 / 47 → 6）；
② 看运行记录里每分钟的实际数（实测 40–47 → 1–3），并看调度心跳间隔是否稳定（应恒定一个周期，如 60 秒）；
③ **把“不扎堆”写成断言测试**（如“任一分钟不超 8 条”）——相位是散列性质，测性质比测具体数值稳，
且以后有人改回“重置为 now”会当场报错，而不是等下次限流才发现。

### `.env` 含 shell 特殊字符的值必须加引号（两种读法结果不同）
同一个 `.env` 被两种方式读：主程序用 `--env-file`（原样读），脚本/测试用 `set -a && . ./.env`（shell 会处理）。
值里的引号在 shell 下会被吃掉：`X={\"a\":1}` 变成 `{a:1}` → 报“必须是 JSON 对象”，而**主程序照常跑**，极易误判成代码 bug。
- **修法**：值里含 `{}`、引号、空格、`#` 的条目一律加单引号（两种读法都正确）。
- **排查**：对比文件里的原值与 `source` 之后 `os.environ` 里的值，不要只盯着代码。

### 医学过滤要"放行词 + 排除词"双层（2026-08-26 用户批评）
裸放行词会误伤：MED_KW 里裸词"论文"匹配了"高中**议论文**写作"（高中作文笔记入库，用户点名删除）。修复：
- 放行词用**精确科研语境**（论文写作/学术论文/期刊论文/毕业论文/综述），不用裸词（论文/写作/科研这种太宽）
- **EXCLUDE_KW 排除词层**：命中即丢弃（高中/中考/高考/作文/语文/提分/素材/艺考/公务员/教资/旅游/美食/穿搭/游戏/明星/八卦等）——非目标人群内容只要蹭到医学边缘词就进来的问题靠这层挡
- 验证：用被误抓的样本断言 `is_medical(样本) == False`，同时断言正常样本不误拦
- **AI 虚构内容要单独挡（2026-08-31 用户批评）**：AI 短剧/重生爽文（"顶级医学博导，重生回临床一线，开局抢救激活系统"——38 集全抓入库，标题带医学词但内容是虚构爽剧）——排除词补 AI 内容特征：`AI漫剧/漫剧/重生/开局/激活系统/短剧/爽文/穿书/甜宠/霸总/逆袭/穿越`。**B站通道也要加同样的标题排除**（bili_daily 在去重后加 EXCLUDE_TITLE 检查），别只加社媒通道。

### 弃用飞书多维表格后：全项目 grep 残留写入点（2026-08-31 实测）
"直写本地"改造常漏掉**追踪/转录等后处理脚本**的写飞书残留——表现：某机制"在跑"（日志正常、状态文件在更新）但**本地库对应字段从不更新**（用户发现"热门稿件播放量发布不到一周就停止统计"）。排查与修复：
- `grep -rn "record-batch-update\|record-create" ~/.hermes/scripts/*.py` 定位所有飞书写入点（含 base 域；读飞书 +record-list 无妨但确认 main 不再依赖）
- bili_track 实测：write_back 还在 `lark base +record-batch-update`（飞书表格）→ 播放量只进状态 json 不写库。修复：write_back 改 `UPDATE content SET 阅读量=? WHERE 子平台='B站' AND 链接 LIKE '%bvid%'`（WAL+busy_timeout），且**收集队列内所有稿件播放量（不只火稿）**
- 收尾：跑一次 sync_feishu_db.py 全量拉飞书（不覆盖本地保护字段）把飞书里更新鲜的字段（阅读量/互动/AI分析报告）收编本地 + 备份 JSON；之后飞书多维表格零写入（飞书群通知保留——那是消息不是表格）

### 社媒互动数据追踪（门槛版，对齐 B站播放追踪）
小红书/抖音新稿件互动追踪（赞/评/藏增长）：**发布满 2 天观察 → 赞>50 或 评>10 达标 → 进 7 天队列 → 每日查详情更新本地 → 满 7 天退队**。详见 `references/social-track.md`。

### launchd 开机防漏（错过定时点）
StartCalendarInterval 错过不补跑（开机已过 07:00 则当天跳过）→ 加第二个 plist（RunAtLoad=true）：检查当天日志有没有跑过（grep 当天日期 $LOG），没跑且已过启动点则补跑整套。
⚠️ **补跑完成时间必须评估（2026-08-28 实测）**：开机补跑 07:05 触发但完整跑完要 4 小时（B站 28 关键词 + YouTube 增量 + 转录），用户早上 8-9 点打开 GitHub 时补跑还没发布 → 用户以为"没跑"。**防漏机制本身有效 ≠ 用户能及时看到数据**。缓解：① 补跑时把发布提前（抓取完先 publish 主数据，转录/慢任务后置）② 或限制补跑范围为核心路（跳过转录等慢任务）③ 用户问"没跑"时先查日志时间线（两次运行记录）再下结论，别只看启动时间。

### redfox 详情接口做补全兜底（2026-08-28 升级）
社媒平台的**作品详情接口**（小红书 `/story/api/xhsUser/queryWorkDetail`、抖音 `/story/api/dyData/queryWork`，均 workId 参数）比搜索接口更精准——**一次调用同时拿封面直链（coverUrl）+ 作者 ID（拼主页）**，不受搜索窗口/排序影响。做封面/主页兜底时优先详情接口逐个直查（¥0.02/次 + sleep 1s），替代"重搜关键词碰运气"。**403 = 已删除/不可访问内容**（小红书实测：详情接口 403 + camofox 打开重定向首页双重证实）——放弃该条，别反复试；camofox 未登录也拿不到未登录平台（小红书）的精确封面（重定向首页只能拿推荐流随机图）。

### 关键词覆盖：每天全量（用户 2026-08-27 否决隔日轮换）
曾提过社媒关键词池分 A/B 两批隔日轮换省 redfox 调用——**用户明确否决**（"我觉得没必要，还是保持每天全平台更新一次"）。**用户偏好：每天全平台全量更新，不要自作主张降低单日覆盖**。维持全量 10 词/天；省调用优先靠"门槛过滤"（如追踪队列只在达标稿件上花钱），不靠砍覆盖。

### 流水线 v2 加固：健康检查前置 + 零产出告警 + 慢任务后台化（2026-09-02 复盘落地）
用户每天会问"怎么没更新"——复盘系统性根因是**失败静默**（平台 0 产出只记日志无人发现）。pipeline v2 加四道防线（launchd 05:00 单入口）：
1. **健康检查前置**：开头 curl camofox `/health` 查 `"browserRunning":true`（断连则 pkill + launchctl kickstart 重启，KeepAlive 只保进程不保浏览器连接）；redfox 测试调用一次（code=2000？失败仅告警不阻塞——fetch 自带重试）
2. **零产出告警**：第 1 波后 SQL 查各平台今日入库，为 0 的平台推飞书群告警——**注意排除增量本来就少的平台**（YouTube 30 天窗口常 0 是正常，留它会误报）；告警后需人工区分"真异常"vs"平台窗口内无新内容"（看抓取日志有无 `累计新增 0`）。**被排除告警的平台必须另有看护**：告警不看它，它的故障（如 camofox 浏览器断连）就会静默多日——给依赖的浏览器服务加独立的小时级 watchdog（查 `/health` 业务字段 + 运行时堆积阈值，见 `launchd-service-supervision`），比告警更根本。
3. **慢任务后台化**：social_track（45s×276 条 ≈ 3.5h）从主链拆出 `nohup bash -c "track && publish"`——主发布不被它阻塞（早上 6:00 前内容上线），track 完成后自动二次发布互动数据
4. **摘要完整性检查**：发布前查 summary_daily 有没有今天，缺则先补生成再 publish（GitHub 是快照，漏发布=用户看到旧摘要）

"补数据后必重发布"：手动补摘要/播放量/任何库修正后，GitHub 静态版不会自动出现——**必须再跑 publish.sh**（曾漏发导致用户截图 08-28 旧摘要）。

### 失败自动重试（bash 3.2 兼容陷阱）
- 并行路失败收集：**不要用 `declare -A`**（macOS 自带 bash 3.2 不支持关联数组，报 `declare: -A: invalid option`，且后续取名字全错）——用**逐个 `wait $pid || FAILED="$FAILED 名字"`**（wait 按 pid 等各自退出码，bash 3.2 安全）。
- 失败路 sleep 120 后重跑 1 次（脚本幂等：链接 UNIQUE 防重复）。
- 每路加 60 分钟硬上限（`( sleep 3600; kill -9 $pid ) &` 后台 killer；macOS 无 GNU timeout 命令）。

### 静态版 = 快照，二次发布才上线（用户理解纠偏）
- **本地 Flask 实时读库**：转录/补全完成后刷新即出现，零操作。
- **GitHub 静态版 = publish 那一刻的导出快照**：转录等后处理结果不会自动出现，必须**再次 export+push**。
- 方案：主发布不等转录（早上尽早上线）→ 转录完成后脚本自动二次 publish（git push 幂等，无变化自动跳过）——两边当天都有完整内容。

### YouTube 播放量需定期补跑（2026-09-02 实测）
camofox 抓 YouTube 时**视频页观看次数元素（ytd-video-view-count-renderer）未登录偶发不渲染**——一次尝试失败播放量就存 NULL（标题/日期照存），批量下可能大面积缺失（实测 210 条只有 1 条有播放量）。**修复：专门补跑脚本（fix_yt_views.py + ytview_loop.sh，重试逻辑）进 pipeline 第 3 波发布前**，每天自动补新抓的；camofox 断连（服务进程在但 browserRunning:false）时先重启服务（launchctl kickstart）再补跑。

### 关键词复盘需要字段支撑（2026-09-02 用户要求复盘产出少的检索词）
按关键词统计产出量来优化检索词的前提：**抓取入库时必须存\"关键词\"字段**（records 加 `\"关键词\": kw`）——B站/公众号抓取通常存了（bili 有 kw），**小红书/抖音 fetch 脚本容易漏存**（实测 0/441 无关键词，历史无法复盘只能等下次抓取积累）。复盘维度：高产（≥80 条）、中产、低产（<30 条）分档 + **低产词抽查相关性**（产出少但全相关=高价值词保留；产出少且低相关=删/换，如\"医生丑闻\"10 条里 9 条是泛社会新闻、\"真实世界研究\"仅 2 条但全对口科研人群——数量≠价值）。关键词池优化对照目标受众调（科研向缺 Meta分析/生信/统计/投稿词就补）。

### 博主→固定分类规则（用户逐条积累）
用户会指定某些博主的固定分类（如"杰比的生活日记 只发搞笑段子 → 日常其他"）。实现：`~/.hermes/scripts/博主分类规则.json`（`{来源名: 主分类}`）+ 抓取时 `rule_category(author)` 命中直接归类（**跳过 LLM 打标**，省钱又准）；同时把该博主**历史稿件**批量 UPDATE 到规则分类。规则文件 JSON 随时加博主，永久生效。

### 平台展示与限流体验（2026-08-28 决策 → 2026-09-02 被用户反转，以新规为准）
小红书对未登录访客强限流：**直链打开笔记页 → 重定向登录墙（"扫码用手机看"）**，浏览者体验差。用户最初决策（8-28）：小红书标题点击跳作者主页。**但 2026-09-02 用户反转此设计，最终定稿**：
- **列表/热榜：标题一律跳笔记原文**（所有平台统一，标题不再跳主页）
- **博主名（来源）→ 主页链接**（列表 meta 行已有；**热榜 TOP20 标题旁附博主名**，仅小红书如此，其他平台不加）
- 意图：标题点开看内容（遇限流可接受），博主名是独立入口去主页找
- 实现注意：**sqlite3.Row 不支持 .get()，必须用下标 x["来源"]**（用 .get 直接 500）
- **改 med_web.py / site/index.html 后必须立即自测**：`bash ~/.hermes/scripts/verify_web.sh`（11 项：各平台路由 200 + 小红书标题→explore/ 链接 + 博主名→user/profile/ 断言）——本会话曾改完不测导致小红书页 500，被用户抓到。双端（本地 Flask + GitHub 静态版）逻辑必须同步改。

### 写库并发铁律：循环内 sleep 前必须 commit（2026-09-02 实测，最隐蔽的锁源）
有 WAL + busy_timeout 仍可能 `database is locked`：**循环里 UPDATE 后不 commit 就 sleep，会把写事务持有 N×sleep 时长**（social_track 实测：276 条循环外才 commit + 每条 45s sleep → **写锁占 3.5 小时**，公众号/翻译等所有并发写全 locked，公众号表现为"无新文章"误报——实际是写库失败静默）。
- **铁律：凡循环内有 `time.sleep`，UPDATE 后必须立即 `conn.commit()`**（sleep 前释放锁）
- 症状识别：某脚本"跑了但 0 入库/无新文章"+ 手动跑报 `sqlite3.OperationalError: database is locked` = 有别的长事务持锁——查所有并发脚本的 commit 位置
- 排查命令：`grep -n "commit\|UPDATE" <script>.py` 看 commit 是否在循环外；修复后 kill 持锁进程、重启该脚本（幂等续跑）

### GitHub Pages 验证/缓存排查（用户报"没更新"）
排查链：① 本地 data.js 是否新（ls -la site/data.js）② site/ 仓库 git log（**仓库在 site/ 子目录，不是上级目录**）③ `git ls-remote origin main` 对比远程 ④ `gh api repos/OWNER/REPO/pages/builds/latest --jq .status`（built=成功）⑤ curl 远程 data.js 检查是否含当日日期。全部通过但用户仍看到旧数据 = **浏览器/CDN 缓存**，让用户强刷（Cmd+Shift+R）。

## 架构（实测可靠）

```
cronjob create（no_agent=true, script=xxx.py, schedule="30 7 * * *", deliver=origin）
  └─ 脚本全自动：抓取 → LLM 摘要/打标 → 多维表格写入 → 飞书文档更新 → 飞书群推送
```

### 为什么 no_agent（关键）
- cron 的 agent 模式：脚本输出注入 → agent 调 LLM 思考 → 生成汇报。**LLM API 早晨时段响应挂起时 agent 空闲超时被杀（inactivity 600s），任务"跑了"但产出全丢**（8-16/8-17 连续两天实测，iteration=1 卡在第一次 LLM 调用）。
- **修复：no_agent=true 纯脚本模式**——脚本内自己调 LLM API（读 `~/.hermes/.env` 的 key）、自己调 lark-cli 更新文档/写表格/推飞书，stdout 直接投递。无 agent 超时问题，脚本总时长自己控制（<10 分钟）。
- no_agent 投递：非空 stdout 原样发出；deliver 用 `origin`（会话）+ 脚本内飞书群推送（用户手机收通知）。

### 通道选择（反爬第一原则，用户拍板"安全不被限制最要紧"）
| 通道 | 适用 | 说明 |
|---|---|---|
| **camofox 浏览器**（localhost:9377 REST API） | **所有网页源**（新闻站、B站搜索页） | 真实浏览器指纹，反检测；curl 抓 RSS 也会被检测（NEJM 实测 IP 临时封） |
| 官方 API 直连 | medRxiv / B站 view 接口 | 接口非反爬目标，低频（≥1.2s/条）安全 |
| curl | 仅 camofox 挂掉时的 fallback | 不要作为主通道 |

- **"RSS 是公开 feed 无反爬"是错误假设**：NEJM etoc RSS 用 curl 每天固定时间抓被 IP 级临时封禁。RSS 也走 camofox。
- camofox 用法详见 `references/camofox-rest-api.md`（tabs/navigate/evaluate、唤醒竞态 500 重试、XML/RSS 抓取）。

### 频率规划（降风控 + 不浪费）
- **周更源每周只抓 1 次**：NEJM 周四/五发刊 → 周六抓；Lancet 周六发刊 → 周日抓（`if now().weekday() == 5`）。
- **周末无更新的源跳过**：STAT 工作日更新（`if now().weekday() < 5`）。
- 日更源（ScienceDaily/medRxiv/Nature News/科学网）每天抓。

### 增量窗口与去重
- 窗口按**日期**判断时用 72h 而非 40h：40h 按"当天 0 点"计算会误杀"昨天"的条目（下午跑时 8-16 的条目被算成 40.6h 前）。
- 状态文件 `xxx_state.json` 存 URL/bvid 集合做去重；写入表格/入库成功才更新状态（防重复入库）。
- LLM 摘要/打标：max_tokens ≥4000（推理模型会把预算花在思考上，正文为空）；分批 ≤100 条/次；JSON 解析容错（```json 代码块/逐行）。

### 飞书投递三件套
1. **多维表格写入**（素材库主库）：详见 `references/feishu-bitable-cron-writes.md`——`+record-batch-create --json '{"create_records":[...]}'`、record_id 拿法、auto_number 删不掉、字段名核对。
2. **飞书文档「今日更新」节**：`docs +update --command str_replace --pattern "📅 今日更新...二、顶刊新闻（完整标题）" --content @节.md`（pattern 后缀必须用完整标题，否则括号残留累积）。
3. **飞书群推送**：`im +chat-create --name "xxx"`（建群，用户自己为成员）→ `im +messages-send --chat-id oc_xxx --markdown <报告> --as user`。用户手机飞书收通知（比微信通道省事，无需注册第三方）。

### 执行要点
- 每源独立 try/except，单源失败只标"缺失源"不中断整体。
- 脚本总时长目标 <8 分钟；camofox navigate 每次 5-15s，8 源 ≈ 1-2 分钟。
- 输出格式：速报 markdown（亮点 TOP3 + 分源清单 + 缺失源），stderr 打诊断（camofox fallback/耗时），stdout 只打速报。
- cron 运行记录在 `~/.hermes/cron/output/<job_id>/*.md`（no_agent 存 stdout）；排查"没跑"先看这里 + `cronjob list` 的 last_run_at。

### 溯源：用户问「这个日报是谁在发的 / 哪个任务在做」

用户每天在飞书收到推送却不知道是谁在跑时，**不要停在排除法**——查完 Hermes cron 列表回一句「不是我」等于没回答（用户会追问「到底是谁在做」）。从消息本体正向溯源，四步定案：

1. **飞书消息里直接看发送者**：`lark-cli im +messages-search --query "<日报标题里的固定词>" --as user` → 每条返回 `chat_id / chat_name / sender.name / sender.sender_type / create_time`，同一群的历史日报一次全出来（看历史格式差异、异常消息也顺手拿到）。
2. **分辨「真人」「机器人」「脚本代发」**：
   - `sender_type=app` → 某个机器人应用；`lark-cli im +chat-members-list --chat-id <oc_xxx> --member-types bot,user` 拿 app_id 对号。
   - `sender_type=user` 且 `lark-cli contact +get-user --as user`（**不带 --user-id 返回的就是「我」**）给的 open_id 与消息 sender 相同 → 是本地 lark-cli 拿用户令牌发的脚本输出，不是手打、也不是 bot。这一点必须讲给用户听：飞书里显示发送者是他自己，所以他一直以为是「有人在发」。
3. **定位执行体**：`launchctl list | grep -i <关键词>` → 逐个打印命令行 `/usr/libexec/PlistBuddy -c 'Print :ProgramArguments' ~/Library/LaunchAgents/<label>.plist`（label 名字往往和业务无关，别靠名字判断，直接看它跑哪个脚本）→ 打开入口脚本 grep 出产脚本（如 `daily_pipeline.sh` 里 `python3 bili_daily.py &`）→ 在出产脚本里 grep `CHAT_ID` / `+messages-send` 确证目标群。
4. **日志时间对账**：`grep -nE '<日期>' /tmp/<pipeline>.log | tail -20`，推送时间点必须落在流水线运行区间内（起点 + 各波结束时间都在日志里）。

汇报给完整链路，一段到位：launchd label → 入口脚本（带行号）→ 出产脚本 → 推送身份 → 日志时间。用户要的是「谁在做」，不是「谁没在做」。

排障坑：
- **别对 `~/.hermes` 整目录递归 grep**：里面有大 cache/会话库，几十秒到超时；只查 `~/.hermes/scripts/*.py`、`~/.hermes/cron/jobs.json`、`~/Library/LaunchAgents`。
- 查历史会话用 `session_search`，不要 grep 会话库文件。
- macOS 没有 `timeout` 命令（`timeout: command not found`）——限时用 `gtimeout` 或直接给工具的 timeout 参数。

## 下线流水线里的一路（用户说「某平台/某日报别跑了，浪费 token」）

日报是流水线里并行起的一个 python 阶段时，**只删启动行会留下三个反噬**。四处必须一起改（bash 3.2 无关联数组，失败收集靠 `wait $pid || FAILED=...`）：

| 位置 | 不改的后果 |
|---|---|
| 启动行 `python3 xxx.py >> $LOG 2>&1 &  PAx=$!` | 任务照跑 |
| `wait $PAx \|\| FAILED="$FAILED xxx"` | `wait` 等空变量 → 每天记一次「该路失败」+ 白睡 120 秒再重试一轮 |
| 重试 `case` 里的 `xxx)` 分支 | 残留分支指向已删脚本 |
| 零产出告警的 `plats` 元组 | 该平台永不再入库 → 每天误报「X 0 入库」，比没告警更糟 |

配套：

- 先备份（`cp daily_pipeline.sh daily_pipeline.sh.bak-<日期>`），再改；改完 `bash -n` 验语法（被守卫拦时见 `launchd-service-supervision` 坑 3 的替代做法）。
- **零产出告警名单是必改项**，最容易漏：删了抓取路却没删告警平台，第二天早上就收到一条假故障推送。
- 判断「还要不要停附属脚本」：转录/追踪这类循环在「无候选即退出」的设计下会自己空转退出，不用专门停；不耗 token 的直接留着，向用户说清即可。
- 停用后**不要顺手删出产脚本和它的状态文件**：用户要的是停止消耗，不是删代码；留着一句恢复说明比删干净有价值。

## 参考文件
- `references/camofox-rest-api.md` — camofox 浏览器 REST API 端点、坑、代码片段
- `references/feishu-bitable-cron-writes.md` — 多维表格写入/更新/隐藏列的实测要点
- `references/youtube-camofox-scraping.md` — YouTube camofox 直抓：日期提取选择器陷阱、30 天过滤、播放量同收、老视频清理
- `references/social-track.md` — 小红书/抖音互动追踪（门槛版）：进队窗口、redfox 详情接口路径、成本
