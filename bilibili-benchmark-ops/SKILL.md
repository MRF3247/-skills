---
name: bilibili-benchmark-ops
description: "管理B站对标账号体系时使用：互动数据、账号库建档、TOP10计划、watchdog守护、避雷分析。"
---

# B站 对标账号体系运维 (bilibili-benchmark-ops)

覆盖「对标账号库」的批量运维：枚举清单、互动数据爬取、账号文档生成、TOP10 分析计划、教程类统计、进程守护、避雷分析。单视频下载/转写管线见 `bilibili-video-pipeline`（user-owned）；得到大脑 API 见 `getnote-api`（user-owned）。全部脚本在 `/Users/Jin/Documents/Hermes/B站工作流/`。

## 账号库规范（用户确认的格式，2026-08）

- 保留账号按**粉丝量降序编号**：`{NN}-账号名（粉丝xx.xx万）.md`（如 `01-兔叭咯（粉丝810.58万）.md`），粉丝数统一 **xx.xx万**（去尾零），播放量同样万格式
- 每个账号文档列出**全量稿件**（不做筛选，按播放量降序），列：播放|点赞|投币|收藏|转发|评论|标题|时长|发布|链接|逐字稿|选题分析
- 被排除账号移到 `对标账号库/不分析/`（含 catalog 移到 `.catalog_excluded/`）
- 用户筛选口径迭代链（enumerate_accounts.py 固化）：recent_months → exclude_keywords（如医学SCI排除 zotero）→ max_duration=40 → 两段式（2025-01 后≥2000/更早≥1万）；用户手工删账号、名字含「科研绘图」、粉丝<1万 一律不分析
- 用户主赛道是**医学论文/科研**：纯医学科普账号（健康科普/医生日常/科普杂志）会被用户要求撤掉，只补论文/科研相关 + 用户点名的头部号（如大物是也）

## 互动数据爬取（fetch_stats_one.py / run_fetch_loop.sh）

- 数据源：`api.bilibili.com/x/web-interface/view?bvid=` 的 `data.stat`（view/like/coin/favorite/share/reply/danmaku），写回 catalog 的 `v["stats"]`
- 防反爬节奏：间隔 1.0-1.8s 随机 + 每 100 条休息 25-40s + 风控码(-412/-799/429)退避 120s + 连续 5 次失败长暂停 600s；必带 cookie + 浏览器 UA + referer
- **长进程会被系统杀**（macOS 后台进程，exit None 且无 traceback）：用 bash 循环模式——`run_fetch_loop.sh` 对每个账号调用短进程 `fetch_stats_one.py <catalog.json>`，外壳存活则单进程被杀也无妨（断点续传）
- 失效视频：接口返回 -404「啥都木有」= 视频已删除，标记 `stats={"view":0,...,"deleted":true}` 后 catalog 算 100% 完成
- 注意 Hermes 的 process 工具**误报退出**（exit code None 但进程实际活着）——报退出后先 `ps aux | grep` 确认再重启，避免双进程并发写 catalog

## 评论接口（fetch_comments.py）

- 新接口 `x/v2/reply/main` 和未签名的 `x/v2/reply` 在**未登录/未签名时只返回 3 条预览**（code=0 但数据空）——这是 B站 对未登录评论的截断，不是「评论少」
- 修复：`bili_api._sign()` wbi 签名 + 有效登录 cookie（SESSDATA）
- **cookie 过期症状**：`nav` 接口 `isLogin: False`、评论恒 3 条——让用户重新导出 cookie 覆盖 `/Users/Jin/Documents/Hermes/APIs/www.bilibili.com_cookies.txt`（SESSDATA 约 1-2 个月过期）

## TOP10 分析计划（build_top10_plan.py → getnote_top10.py / top10_local.py）

- 每个账号取播放量 TOP10 → 分类：普通-分析（逐字稿+选题分析）vs 教程-统计/教程-超长合集（不转录）
- **教程判定**（用户口径）：标题含 教程/教学/课程/训练营/公开课/网课/从入门到精通/零基础/系统课/速成班/学习路线/全套教程，或时长>3h（合集）；模糊词（实战/保姆级/手把手/全套/合集）会误伤干货视频——不算教程
- 教程类 → 账号内「教程合集统计.md」：分类+标题+播放+时长+评论区诉求（LLM 总结「关心什么/诉求/想看什么」，抓 200 条评论）
- 双通道执行：得到 API（100 次/天，额度用完自动停，429=额度耗尽的另一种表现）+ 本地 FunASR（校对用 ThreadPoolExecutor(3) 并发提速，下载间隔 8-15s）；共用 `logs/getnote_done.txt` 去重

## 选题分析批量（analyze_top10.py）

逐字稿齐了后跑：每条 = 抓评论（fetch_comments，缓存 .comments_cache/{bvid}.json，最多 200 条）→ 从逐字稿笔记提取 AI 摘要 → DeepSeek 分析（提示词要求：赛道归类/情绪钩子/评论区焦点带原话/可借鉴点/SciLink 启示）→ 归档 `选题分析/{NN}-{账号名（粉丝x.xx万）}/{NN}-{标题}（播放x）.md`。
- `ThreadPoolExecutor(3)` 并行，400 条约 1-2 小时；断点 `logs/analysis_done.txt`
- 归档目录 `ow._account_dir_name(cfg, up)`（按粉丝匹配账号名含编号）；文件名里标题要 `_safe()` 截断
- 完成后 `obsidian_writer.rebuild_index(cfg)` 重建素材索引

## 逐字稿目录编号对齐（obsidian_writer._acct_num）

用户要求逐字稿子目录与账号库编号一一对应（`逐字稿/01-兔叭咯/` ↔ `对标账号库/01-兔叭咯（粉丝810.58万）.md`）。
- `_acct_num(cfg, up)`：遍历账号库文档名，`up == name or 双向 startswith` 匹配（兼容账号库名带后缀：`医学SCI文献解读（医嘉研）` 匹配 up=`医学SCI文献解读`；`意得辑 editage` 匹配 up=`意得辑`）；非对标账号返回 '' 保持原名
- 一次性重命名脚本：正则 `^(\d{2})-(.+?)（粉丝.+?）\.md$` 提取编号，逐字稿目录 `mv` 成 `{NN}-{原名}`；已带编号的跳过
- 得到 API 归档的目录名可能不是账号库名（联合投稿显示主投者如「医健三连充电站」）——非保留账号目录不动

## 进程守护（watchdog.sh + crontab）

- crontab `*/30 * * * *` 跑 watchdog.sh：守护三项（top10_local / analyze_top10 / getnote_top10），进程挂了 `nohup ... &` 自动重启（断点续传不重复），对应批次全部完成自动收手
- 得到 API「额度用尽不重启」判断：**按日志文件 mtime 是否今天**（`stat -f "%Sm" -t "%Y-%m-%d"`）——日志里额度停止行无日期前缀，且额度每天刷新（昨天用尽今天要重启）；不能用 tail 看「额度」字样
- 完成判断：动态读 top10_plan.json 数「普通-分析且 in done.txt」的 bvid 数，达到目标即收工

## 全量价值分层 + 腰部选题库（analyze_all.py → waist_lib.py）

第三个分析维度（避雷/TOP10 之外）：把全量稿件按「播放段 × 赞播比」自动分级，筛出**腰部高赞播**（B级 1-10万 + 赞播比≥4% = 内容质量已验证只差推荐量，冷启动主战场）。
- `analyze_all.py`：秒级完成 31,704 条分级（S≥50万 / A 10-50万 / B 1-10万 / C 0.2-1万 / D<2000）+ 主题关键词分类（11 类）→ `logs/all_classified.json`（rows/topic_seg/waist）
- `waist_lib.py`：腰部全量抓评论（ThreadPoolExecutor(8) 并行，复用 .comments_cache）→ **LLM 按主题批量提炼**（每批 40 条，不是逐条分析：主题共性选题模式/评论区诉求原话/冷启动选题标题）→ `内容增长/腰部选题库.md`
- 关键设计：选题规律从「标题+互动+评论」就能提取，**不需要逐字稿**——批量分析快（1,950 条约 30 分钟）
- **静默截断坑**：样本必须全量或明说抽样——`waist[:300]`、每主题 `min(len,120)` 这类截断会让「全量」名不副实（本次 1,950 只实际分析 300 就出过这问题，用户要求全量后修复）
- **% 格式化坑**：prompt 里「赞播比≥4%」的 `%` 后跟全角字符会崩（unsupported format character）——LLM prompt 一律用 f-string，别用 % 占位
- 详细口径/算法/坑复现路径：`references/analysis-methods.md`

## 账号策略画像（account_profiles.py）

对与 SciLink 业务相似的账号（15 个：论文/AI/统计/生信/工具服务商类）做深度拆解，回答「抄谁、怎么抄」：
- 指标聚合（catalog 全量，0 秒）：粉稿比、播放中位数、爆款率（S/A/B 占比）、互动质量（平均赞播比/收藏率/评论率）、主题结构、近 12 月更新数、系列化前缀识别（`【XX】`标题聚类）、变现信号（标题含 课程/服务/报名 词占比）
- LLM 逐账号策略拆解（每账号 1 次调用，max_tokens=4000）：内容支柱（带证据）/人设定位/涨粉变现逻辑/3 条可复制点/风险短板
- 每账号补「📎 关键稿件参考」小节：选 5 条代表作（业务相关关键词优先 + 播放 TOP2 兜底），带可点击 B站 链接——脚本插入文档
- **fans 字段坑**：catalog 的 `account.fans` 常为 0（枚举时没存）→ 粉丝数权威来源是 `accounts.yaml`；且 accounts.yaml fans 有「46.49万」字符串格式，`int()` 直接失败返回 0 → 必须 `_parse_fans()`（万→×10000）；账号名带后缀（医学SCI文献解读（医嘉研））需前缀别名匹配

## 选题分析目录历史遗留与合并去重

编号体系多次演进（96 账号时代 → 44 账号重排）会产生：同账号多目录（不同编号 + 不同批次内容）+ 垃圾目录（联合投稿显示主投者、错误命名如「罗翔说刑法/NA」）。
- 合并去重脚本口径：按账号库名归一（去编号/粉丝后缀，双向 startswith 匹配）→ 每组保留「编号与账号库一致 or 文档最多的」为主目录 → 其余目录文件并入（同名按内容 md5 去重，不同则加「（旧批次）」后缀）→ 删空目录
- 用户对「剔除/排除」类操作可能反悔（本次剔除非科研选题后要求全部还原）——**删除/排除前先确认或保证可回滚**；还原 = 反向 move + 重跑数据脚本 + 恢复文档口径

## 避雷选题分析（analyze_flops.py → build_flop_report.py）

- 只需互动数据+标题+时长+发布时间，**不需要逐字稿**，可随时并行跑
- 扑街定义：播放 < 账号播放中位数 × 30%（相对基准，非绝对阈值）；扑街率维度=主题/时长段/年份 + jieba 标题词频（扑街 vs 对照）+ LLM 提炼共性（抽 50 条扑街标题）
- 反直觉发现：扑街但赞播比≥3% = 内容不差只是没推流（粉丝向内容），别当雷区
- 报告存 `医时知识库/内容增长/B站避雷选题分析.md`

## 关键坑（都踩过）

1. **deepseek-v4-pro 是推理模型**：max_tokens 需覆盖推理+输出；1200 会全被推理耗尽（返回空 content、finish_reason=length）——LLM 总结类调用给 4000+
2. **llm_client signal 超时仅主线程**：线程池内调用报「signal only works in main thread of the main interpreter」→ `_timeout_guard` 加非主线程直接调用分支（靠 HTTP 超时兜底）
3. **Hermes process 误报退出**：输出重定向到文件的进程常报 exit code None 但实际活着——先 ps 确认再决定，别急着重启造成双进程并发写同一文件
4. **B站时长格式不统一**：`MM:SS`（383:15）和 `H:MM:SS`（58:02:06）都有，解析必须兼容（按冒号段数区分）
5. **catalog 数据会被枚举进程覆盖**：--refresh 枚举跑完才动 catalog；并发写同一 catalog 会丢 stats，爬取和枚举不要同时跑

## 账号健康度图（make_health_chart.py → 单文件 HTML 交互图）

对每个对标账号生成「一眼看健康度」的交互图（输出到 `内容增长/附件/账号健康度-{账号}.html`，浏览器打开即可）：
- **主图**：月度播放中位数折线（**不是逐稿原始播放**——累计播放有积累效应，新稿积累时间短会误判"衰落"）+ 月发稿柱状（区分"衰退"与"停更"）+ 月度赞播比着色点（≥4%绿/2-4%黄/<2%红）+ 全时段中位参考线 + 爆款 TOP3 标注（粉色星）
- **健康度评级卡**（四指标）：趋势（近12月中位÷前12月中位：>1上升 / 0.5-1平稳 / <0.5衰退）、质量（平均赞播比≥4%优/2-4%良/<2%差）、活跃（近12月发稿≥12活跃/6-11低活跃/<6濒停）、综合评级（健康上升/健康平稳/亚健康/衰退停更）
- Canvas 原生绘制（无外部依赖），悬停显示月度明细
- **HTML 模板坑**：CSS 的 `%` 与 Python `%` 格式化冲突（unsupported format character）——模板用 `__KEY__` 占位符 + `str.replace` 填充，不用 % 格式化
- **catalog glob 坑**：`.catalog/*.json` 会匹配 `_summary.json`（list 结构非 dict）→ 必须 `"_summary" in f` 跳过，否则 `d["account"]` 报 TypeError
- 用户已验证形态：月度中位聚合 + 四维健康度 + 多账号批量（15 账号一次跑完）
- **15 账号总览仪表盘**（build_health_all.py → logs/health_all.json + make_health_dash.py）：单文件 HTML，账号 checkbox 筛选（全选/全不选）+ 4 指标切换（播放中位/发稿数/赞播比/只看卡片）+ 多账号折线叠加 + 健康度卡片 + 爆款 TOP3；产出 `内容增长/附件/B站对标账号健康度总览.html`。KIMI 生成模板（占位符 __DATA__）→ 脚本注入数据 → 浏览器实测；坑见 html-ppt-generation「数据注入式 HTML」章节（typeof 三元冗余、generateMockData 残留、字段名不一致、重试）
- 实现细节/验证方法：`references/account-health-chart.md`

## 相关

- 单视频/账号下载转写分析：`bilibili-video-pipeline`（user-owned）
- 得到大脑 API（B站链接→AI笔记+逐字稿）：`getnote-api`（user-owned）
- 分析框架/赛道分层：`video-content-strategy`（user-owned）

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `bilibili-benchmark-catalog` | 整理B站对标账号库时使用：枚举筛选、查UID、爬互动数据、生成Obsidian账号文档。 | `references/merged-bilibili-benchmark-catalog.md` |
