---
name: video-content-strategy
description: "Plan video content directions & account growth (起号)."
version: 1.0.0
metadata:
  hermes:
    tags: [content-strategy, video, bilibili, shipinhao, douyin, xiaohongshu, audience-research, account-growth, qihao]
---

# Video Content Strategy (视频内容策略 / 起号)

Use when the user asks "what content should I make", "who would be interested in X", "content directions / 选题", or "起号/涨粉" for video platforms (B站, 视频号, 抖音, 小红书), or when researching what a demographic is interested in — even if the ask superficially looks like market research.

## Step 0 — Clarify the real goal FIRST (learned from a costly detour)

Before deep research, establish:
1. What are they building? (video accounts, a service, a knowledge base, a course)
2. Which platforms?
3. Content constraint: 垂直 (niche/vertical) or 泛 (broad)? A user asking "who needs to write medical papers" may actually be building a BROAD-content account that merely targets that demographic — the research needed is completely different (audience interests, not market size/competitors).
4. Current stage: 起号 (build followers first) vs 变现 (monetize now)?

Pitfall: when the ask looks like market research ("who has need X"), do NOT default to vertical market analysis (competitors, pricing, TAM). This session, that detour was interrupted by the user revealing their true goal: broad video content to attract a demographic, account-first, monetize later. Asking the motivation question up front is cheap; a full wasted research round is not.

## Core framework (泛内容起号)

Identity-as-leverage: the creator's professional identity (医生, 程序员, 教师...) is a differentiator, NOT a content cage. Best play: 泛流量选题 (broad traffic topics) × 职业身份人设 (identity persona). Broad topics = big traffic pool; identity = trust + uniqueness. Verified cases: nurse 任志达 (医院职场短剧 → 头部主播), 儿科唐医生→老唐育儿 (科普+带货, 百万粉).

### 1. Audience profile
For the target group, sketch: age/education, working hours & stress level, income dispersion (usually WIDE — e.g. trainees poor, seniors rich → audience is sensitive to 搞钱 topics), employment type (体制内 vs market), health/wellness sensitivity, recurring anxieties (exams, promotion, employment), content taste (highly educated → rejects low-quality 鸡汤).

### 2. Platform fit
| Platform | Format | Audience | Growth logic |
|---|---|---|---|
| B站 | 中长视频 5-15min | ~70% 90后/00后, high stickiness | 知识区/职场区/生活区 growing; slow start, strong fan quality, 弹幕互动 |
| 视频号 | 短视频 1-3min | 30+ 职场人群 (higher spenders) | 微信生态社交裂变 (forward to 朋友圈/群); strongest 私域 conversion |
| 抖音 | 短视频 | broadest | algorithm-first, fastest scale |
| 小红书 | 图文+短视频 | 高学历年轻用户偏多 | 封面图 critical; high 知识付费 conversion |

Cross-platform play: deep persona content on B站, short cuts + 引流 on 视频号, funnel to 私域 (WeChat).

### 3. Content direction tiers (broadest traffic → niche)
1. 职场类 (largest base): 打工人吐槽, 体制内生存, 晋升潜规则, 职场咨询 (validated monetization: 简历修改/咨询 ¥199+ via 私域)
2. 搞钱/副业类: 工资条揭秘, 下班副业, 理财存款, 防割韭菜
3. 成长/学习类: 学习方法, 考试/考证记录 vlog, 效率工具
4. 健康/生活类 (light, non-technical): 熬夜/体检/职业病, real-life vlog
5. 情绪共鸣类 (fastest growth): 职业故事, 行业梗 ("只有XX才懂"), 职场短剧
6. 身份反差类 (account-starter): 职业+反差 persona, e.g. "三甲医生讲打工人生存"
7. 泛生活/科技类: 城市生存, AI工具 (2025+ biggest increment topic)

### 4. 起号 growth tactics
- Persona first: 身份标签 + 反差属性, one sentence ("三甲医院主治医师，讲打工人生存")
- Mix: first ~50 videos ≈ 60% broad traffic topics + 40% identity content; iterate on data
- 对标拆解: benchmark 1万-10万粉 mid-tier accounts (NOT head accounts), ~5/week, record 选题锚点 / 停留设计 / 评论区引导 — cheaper than own A/B testing

### 4a. 交付对标账号清单的铁律（用户明确纠正过）
- **禁止"等N个"式省略**：交付账号清单必须把每个账号完整列出（账号名 + UID），一个都不能漏，不许写"等8个""其余类似"这类含糊收尾。用户原话："你不要说'等8个'这种没用的东西，你要直接把所有账号的id给我列出来"。
- **UID 必须可直达**：能查到 B站 UID 就给 UID（bilibili.com/space/<mid>），查不到的明确标注原因（榜单作者名/品牌名而非独立账号），不硬凑。
- 粉丝/播放等数据标注快照时间（如"2026-08-04 实时查询"），数值会漂移但账号形态/打法不变。
- **引用外部稿件/视频/数据必须附链接**（用户 2026-08-11 明确纠正）：任何提到来源的内容（B站视频、新闻、报告、数据点）都带上可直达链接；播放量级等未逐一点开核实的数据，标注"未核实"而非默认可信。
- **引 B站视频必须附播放量，且用 API 实查**（用户 2026-08-11 二次纠正：\"还要把它们的播放量附上\"）：`curl https://api.bilibili.com/x/web-interface/view?bvid=<BV>` 返回 stat.view/like/favorite/danmaku/reply，一次批量查多条。**不要信搜索摘要/搜索页里的播放字样**——曾据搜索片段误判\"播放量常见万级\"，实查 9 条里 6 条 <1000、仅 1 条破万，当场被打脸。播放低≠没需求：营销号低质量供给会压低播放，此时看收藏率（工具书型内容实测 6%+，超过 5% 健康线）。
- 视频号: forward EVERY video to 朋友圈/行业群 with a personal line ("这是我的新尝试…") — social fission is the core start mechanism
- Metrics order: 完播率 > 点赞率 > 评论率; first ~20 videos = run the pipeline, not 一炮而红

### 4.5 低产能出镜博主 (solo on-camera, low capacity): 干货 vs 泛流量 is a FALSE binary

When the creator appears on camera and capacity is limited (1-2 videos/week), do NOT ask "干货 or 泛流量" — both pure modes die:
- 纯干货: precise fans but very slow growth (new creators quit first), topic burnout, highest production cost (research + writing + editing)
- 纯泛流量: fast growth but mixed fans (pivoting later = 掉粉), identity wasted, and the topic pool is unbounded — exactly what low capacity cannot feed
- Correct lane: 泛话题 × 身份视角 NARROW lane — broad topic (职场/搞钱/成长) told through the professional identity. Pick ONE lane; run 20-30 videos before widening.

Capacity model (solo on-camera, rough hours per video):
- 口播+贴片 (talking head + on-screen material): ~4-6h → capacity king; the default for low capacity
- 口播 + PPT/数据/截图: +~1h editing
- 半剧情 (acted scenes): ~2x cost — skip at start
- 实拍vlog (daily-life footage): slow to accumulate 素材 — skip at start
- Cadence: 1-2 B站长视频 (5-10min)/week, each cut into 1-3min clips for 视频号 (one hook per clip)

选题纪律 under low capacity:
- Series columns (固定栏目): one column name, each episode answers ONE concrete question — topic cost becomes drawing from a question bank
- Question-driven titles: every title is a question ("医生为什么都劝人别学医？") — carries click-through
- 蹭热点但不泛: react to same-day hot topics (policy, events) for broad reach; series content otherwise
- 一鱼两吃: B站 long (depth + persona) → cut into 3 short 视频号 clips → 引流私域

Early metrics (first ~20 videos):
- Judge by topic-TYPE trends, not single-video data
- 完播率: B站中视频 >30% = topic/pace on track
- 粉丝画像 (后台兴趣标签): medical/职场/education share high = identity strategy working
- 评论区质量: questions + personal stories beat likes
- Decision gates after ~20: broad topics pop but fans mixed → add identity content; identity precise but slow → accept slow (monetization needs precision)

### 5. Compliance red lines (check per industry)
- 医疗机构人员直播带货: 九部委严查 (2022 policy, still enforced) — "doctor sells products" persona is risky; successful medical creators pivot to 短剧/职场 content
- 医疗/科普 content: platforms require qualification certification; treatment advice = compliance risk
- For medical personas prefer 职场/成长/搞钱 monetization over health products
- Generic: 代写/买卖论文/代发 is illegal and gets accounts banned (relevant when a medical audience is later monetized)

## 数据驱动选题决策（腰部优先，2026-08-07 落地）

对标/调研结论要落地成"做什么"时，用互动数据量化（无需逐字稿）：
- **数据分层**：播放≥50万=S爆款 / 10-50万=A / 1-10万=B腰部 / 0.2-1万=C / <2000=D扑街（对账号全量稿件）
- **赞播比（点赞/播放）≥4% 的 B 级腰部 = "内容质量已验证、只差推流"** → 冷启动确定性选题。策略：打腰部不打爆款（爆款=人设+运气，腰部=可复制规律；可复制骨架 = 高信息密度 + 情绪冲击入口 + 收藏价值）
- 腰部评论级分析：腰部条目抓评论（并行带缓存）→ LLM 按主题批量提炼（每批 40 条，不做逐条分析）→ 产出各主题「共性选题模式 / 评论区诉求原话 / 可直接用的选题标题」，几百条全量 5-10 分钟跑完
- **变现信号（用户认可的方法论，2026-08-10）**：标题含课程/报名/付费/服务/训练营/资料/模板/润色/咨询等词占比 = 标题显性变现意图的代理指标。局限：只看标题看不到真实收入结构（大师兄标题克制但靠私域课程变现）、海量稿件账号占比被稀释——只能看相对差异。用户认可的方向：**做稿件逐字稿分析时，用此思路看视频内广告植入/恰饭模式**（逐字稿能看到真实植入，比标题信号准得多）
- **选题需求验证铁律：必须找「同形态」参考内容**（2026-08-11 被用户当场戳穿）：验证\"这个选题有没有人看\"，参考必须是**同形态**内容——立项名单分析选题曾拿\"研究方向/开题报告\"类 B站视频当证据，用户一句话打回：\"这些参考跟国自然立项名单又没关系\"（相邻话题≠同类竞品，是逻辑跳跃）。同形态参考还要查**平台/受众错位**：公众号生态验证过的形态（智归/解螺旋的国自然中标热点、LetPub 中标名单汇总）搬到 B站不一定成立，B站国自然类内容实测播放普遍几十到两千。
- **调研口径教训（用户 2026-08-07 先要求剔除、随即要求全部还原）**：用户曾要求「评论区无目标受众的选题一律剔除」（例：兔叭咯护肤类，评论区无科研受众），执行完成后用户又要求**全部还原**——最终口径：调研数据**全量保留不剔除**，参考时按目标受众自行筛选。教训：涉及批量删除/移动调研成果的操作，先输出待删清单给用户确认再动手，且**操作必须可逆**（移动到独立文件夹而非物理删除，保留移动映射便于一键还原）；对「剔除 vs 保留」这类口径摇摆，倾向保留全量 + 标注口径，别替用户做不可逆的减法。
- **受众圈层模型**（泛内容起号的落地结构）：核心层（精准转化，35%）/ 扩展层（涨粉信任，35%）/ 引流层（破圈拉新，25%）/ 产品层（5%）——扩展层如"医学生态"内容扑街率最低（4.3%），是又稳又广的方向

## SciLink 官方号内容策略定稿（2026-08-10 逐章过稿）

- **受众锚定**：核心 = 有论文发表需求的医学生 + 需靠论文/代表作评职称的医生（写论文/做数据分析那批）；外围 = 即将入行医学科研的人（研0/规培/大三大四医学生）；排除 = 科普泛流量 / AI 泛受众（AI 泛内容扑街率 19.5% 全赛道最高）
- **内容四方向（各带内容目标）**：① 学术圈动态（资讯，吸引圈层粉丝；含顶会/新方法/撤稿与学术不端事件）第一优先 ② 科研AI提效（实操，结合产品能力，植入产品推广打品牌心智）③ 论文（实操，创新点/综述/投稿/文献导读，植入产品推广打品牌心智）④ 医学行业观点输出（观点，规培/考研/读博/晋升，吸引圈层粉丝）
- **铁律：对标参考必须医学领域**——用户连续 3 次纠正（资讯速递/实操录屏/AI 提效/论文复现示例全部要求换医学向）。材料/电化学等"泛科研"账号（如科研论"论文复现"系列，超级电容器）即使赞播比最高也不算医学参考；选参考先确认 UP 主赛道，医学向论文 UP = 科研大喵/FrankG/读论文silan/意得辑/Toedit 等
- **痛点清单区分实锤/推断**：评论区原话 = 实证；行业常识 = 标注「推断（待验证）」。医生/护士科研痛点（临床太忙/职称论文/统计弱）在 B站 评论区几乎无暴露（科研内容观众以研究生为主）→ 需从解螺旋等"医生聚集"账号评论区定向挖掘
- **路线结论**：质优量少（对标大师兄粉稿比 5601、科研大喵收藏率 14.6%），AI+论文选题为主，收藏率作第一健康指标（科研人群爱收藏，"工具书型"内容 5%+）
- 腰部数据洞察：1,950 条腰部中 ~1,730 条（89%）来自 6 个大众科普号（评论区非科研受众）——参考时按目标受众筛选，**不剔除数据**

## 产品演示向选题（系列A，2026-08-12 立项交付）

官方号介绍产品的第一波内容：系列A = 产品演示向（直接介绍产品、建立品牌心智），与「信息差」系列（引流吸粉）分工。实测落地 7 个选题 A1-A7（30秒出选题 / 选题报告逐块拆解 / 不会代码怎么分析数据 / 逆向选题推理 / 12模型一键训练 / 图表对比6.2分SCI / 数据预处理），已按「总览文档+7子文档」交付**腾讯文档**（文件夹「SciLink B站选题-系列A」，2026-08-12 由飞书迁移；飞书端保留不删，用户要删再删）。A1 完整逐字稿（可直接拍摄版）已作为独立章节追加进腾讯文档 A1 文档末尾。可复用的**脚本大纲模板**（10 章节结构 + 分镜表写法 + 官方号产品宣传合规红线）见 `templates/bilibili-script-outline.md`；腾讯文档 MCP 的创建/追加/迁移操作见 skill `tencent-docs-mcp`。

- 系列A 选题弹药来源：产品培训纪要（选题助手/一键预分析/一键智能训练/自定义科研 四大功能 + 效率/成本账 + 三版本定价分层），做产品演示前先读产品资料会议纪要提炼卖点
- 产品现状边界必须诚实：目前只覆盖「选题+统计分析」，论文写作需借外部AI——宣传区分实锤与规划，不吹全流程（用户已多次强调）
- 素材纪律：演示用录屏/图表对比素材，发布前与产品团队核对功能版本与数据授权（如 6.2分SCI 对比图的来源授权）
- 起号期注意（会议2调研结论）：B站医学赛道纯教程/纯AI内容流量已差（解螺旋AI短视频流量很差、纯引流干货教程号效果不好）→ 演示类每条都要带钩子开场，别做成干巴巴教程

## 品牌官方号内容安全光谱（2026-08-11 用户拍板）

做政策/监管/敏感类选题（国自然、卫健委通报、医保、职称政策等）前，先按三档分类，官方号只做前两档：

| 类型 | 例子 | 风险 | 本质 |
|---|---|---|---|
| 客观信息型 | 放榜时间、查询方式、资助率数据、榜单、立项名单统计 | 🟢 安全 | 信息搬运 |
| 政策解读型 | "政策对医生意味着什么"、"没中怎么办"、流程解读 | 🟡 低风险 | 帮用户理解规则 |
| 政策评论型 | "扩容治标不治本"、"马太效应是制度问题" | 🔴 品牌官方号不做 | 价值判断/立场 |

- 官方号=「规则说明书」（服务者人设）：政策来了，帮用户读懂、应对、省时间——正好接产品心智；个人矩阵号=「情绪出口」，观点/吐槽类内容挪个人号
- 为什么官方号禁评论型：① 商业账号涉政策内容审核严、易限流 ② 骂政策=骂用户的生存环境（用户自己在这套体系里晋升），不增信任反损信任 ③ 观点带来情绪+泛粉，信息服务带来信任+收藏（官方号收藏率第一路线，观点向性价比最低）
- 谨慎档铁律：**报数不表态**——只做数据对比（去年 vs 今年），不下"好/坏"结论，让观众自己判断
- 国自然年度素材库（官方源/第三方/故事/数据/安全版预案/放榜后执行清单）见 references/nsfc-fangbang-selection-kit.md

## 新闻热点选题扫描与筛选流程（2026-08-11 落地）

医学学术圈"本周热点"类选题的标准流程：
1. **多源并行扫描**（一次多搜）：英文顶刊（NEJM/Lancet/Nature/Nature Medicine/Science/NEJM AI）+ 中文医学媒体 + 监管/疫情（FDA 批准清单、WHO/ECDC 疫情报告、卫健委通报）+ 刚闭幕大会（AIDS 2026 等会后发酵）+ 科研圈动态（国自然/基金委/博新计划）
2. **按传播力×受众契合度分层**：A 级（强传播力×强受众相关）→ B 级（受众精准命中）→ C 级（话题流量型）→ ❌ 排除项
3. **排除项判断**：科普泛流量生活方式研究（饮酒/冥想/果汁等）传播力强但评论区无目标受众，与受众锚定冲突；除非做"医生视角解读"引流层
4. **每个选题交付物**：一句话事实 + 来源/日期 + 传播力理由 + 切入角度 + 风险提示（数据快照时间、实锤/推断区分、发布前复核）
5. 观点向选题先过「内容安全光谱」，官方号禁评论型（见上节）

## 「医学领域信息差」系列框架（2026-08-11 立项）

定位：把圈内人默认知道、圈外人一脸懵的医学情报讲给医学生/青年医生。官方号系列化内容主框架，一集一个信息差，永不缺选题。栏目名可直接用「医学领域信息差」，单集编号 001、002…，固定结尾「这条信息差，值得收藏慢慢看」+ 评论区钩子。

四条选题线：
1. 数据型信息差（独家武器——别人没数据我们有）：国自然立项分布、期刊 IF 变化、方向涨跌趋势（需爬虫/官方接口，见 references/nsfc-data-sources.md）
2. 规则型信息差（圈内潜规则）：投稿选刊隐形规则、审稿人视角、基金评审"函评生死线"、代表作制度用法
3. 动态型信息差（学术圈资讯，对应第一优先方向）：顶刊新发现、政策变动、学术不端通报
4. 机会型信息差（晋升/避坑）：水会名单判断法、论文工厂避雷、人才计划申报日历

用户 2026-08-11 明确聚焦两条主线：**论文生态**（期刊规则/撤稿/预警期刊/IF 算法/学术不端）+ **世界研究动态**（全球医学前沿进展）。

单集模板：反直觉钩子 15s → 信息差一句话 → 证据展开（数据/截图/案例）→ 对医学生/青年医生各一层"对你意味着什么" → 收藏引导+评论区钩子。

规避：信息差易被联想为割韭菜话术（卖课号常用）——每期给足出处、标快照时间、不卖焦虑；政策类只解读不评论（过内容安全光谱）。

素材收集纪律（2026-08-11 被用户批评"资讯时效有问题"后确立）：**严格限定用户给的时间窗口**（如"2026-08-01 至今"），多引擎并行搜（顶刊/FDA/WHO/中文医学媒体各一路，site: 限定 + 中英文分别搜）；过时素材（窗口外的 JCR、预警名单等）单独标注为「背景资料区」，绝不混入窗口素材；引用一律附链接，数据标日期。

## 方案类文档协作规则（用户明确要求）

- **续写用户已改文档前必先 read_file 读当前版本**——用户会在 Obsidian 直接改笔记，以用户改过的内容为准再追加新章节，绝不覆盖用户修改（用户原话："以被我修改过的稿件为准，再去续写新的部分"）
- 长方案先过大纲 → 一章章写 → 每章用户确认后再写下一章；用户可能随时改标题/删节/简化，追加前重读当前文件
- 用户改稿风格：倾向简化（删细节指标、删冗余章节如排期表），保留结论与关键数据；不要预设"用户会要什么结构"
- 涉及批量删除/移动调研成果：先出清单确认、操作可逆（移动而非删除、留映射）
- read_file 对部分 UTF-8 文件误判 binary → 用 terminal cat 读
- **报告/待办产物以附录形式追加主文档**（用户明确："直接更新到这个内容运营方案下面，以附录的形式呈现"）——不单独建文件；附录编号 A/B/C…，正文章节与附录分区清晰
- **Markdown 表格生成 pitfall**：用三引号字符串拼接表格时，字符串尾部多余换行会在表头/分隔行与数据行之间插入空行 → Markdown 表格中断。生成后必须验证「表头行 → 分隔行 → 数据行」连续无空行
- **表格格式偏好**：每条参考稿件单独一行（不合并单元格）+ 备注播放量/赞播比；粉丝/播放数字用「万」单位（46.49万 而非 464900）；参考链接必须与被参考主题同领域（医学策略文档里的参考一律医学领域）

## 逐字稿创作工作流（素材库文风学习，2026-08-12 落地）

用户要为已定稿选题写逐字稿时（"挑几篇文风适配的逐字稿，学习它们的文风给我创作一版"），流程：

1. **定视频类型**：实操录屏+口播 / 口播观点 / 资讯速递——类型决定挑什么文风样本（产品演示型 → 实操演示 UP 主，不是科普/资讯 UP）
2. **从素材库挑 2-4 篇同类型稿件**：B站逐字稿库在 `医时知识库/选题参考/B站素材库/逐字稿/`（40+ 账号按粉丝降序编号 01-44）；实操演示型首选 做科研的大师兄 / 科研人FrankG / 医学生彼得
3. **提炼文风特征表**：每篇记一条「可学之处」——大师兄=痛点开场+设问推进+"不吹不夸只讲干货"；FrankG=一句话比喻（DOI=论文身份证号）+不寒暄直接切入；彼得=聊天式开场+弹幕互动+真实吐槽感
4. **融合创作**：逻辑骨架 × 比喻化表达 × 互动感，按既有大纲（钩子/主体结构/CTA）填口播；3-4min ≈ 900-1100 字
5. **逐字稿格式**：【画面/字幕提示】与口播正文分行标注、口播可直接照着念；文末附「创作说明」交代每个设计点的文风来源与合规落点
6. **素材库转写质量参差**：部分 FunASR 转写稿是纯噪音（如科研大喵个别文件全是"嗯嗯嗯"），选稿先看文件大小/首屏有效性，坏稿直接换下一篇

逐字稿合规是硬约束：效果承诺（包发/保证/100%）禁用、产品边界（实锤 vs 规划）如实、红线服务（代写代发）不出现；诚实兜底话术（"数据还得你自己收，文章还得你自己写"）要设计进去——既合规又增信任。

文风样本细节与 A1 逐字稿复盘见 references/bilibili-script-writing.md。

## References
- references/bilibili-script-writing.md — B站逐字稿创作：素材库文风样本表（大师兄/FrankG/彼得）+ A1 产品演示型逐字稿复盘 + 交付结构偏好（2026-08-12）
- references/scilink-content-knowledge-roadmap.md — SciLink 专业内核知识补足路线图（受众→论文→统计→竞品四阶段）+ **AI 生成科研方案的四步验证流程（利血平案例）** + 现成「小白讲法」卡片（基线数据/主次结局/CTA/高血压科室，2026-08-13 扩充）
- references/nsfc-data-sources.md — 国自然数据源与**技术抓取**（2026-08 逆向验证）：kd.nsfc.cn 官方平台接口（DES-ECB 加密 key=IFROMC86、免登录统计/热词接口、成果检索≠项目检索）、LetPub nsfcfund_search.php 参数、医院喜报粒度规律、2025 榜单样例、**逐条数据滞后到 2023 的现状**、合规红线、放榜后时间线。选题素材与安全版预案见 nsfc-fangbang-selection-kit.md（两者分工：kit=内容素材，本文件=数据管道）。
- references/nsfc-fangbang-selection-kit.md — 国自然放榜年度选题素材包（2026-08 建）：放榜机制/官方源链接/第三方分析/Nature 报道/故事素材/数据点/安全版选题预案/放榜后执行清单（抓名单→词频→风向报告→视频）。
- references/medical-professional-audience.md — session research: 医生/护士/医学生 audience profile, 2025-2026 content trends with sources, verified cases, beyond-papers interest map.
- references/bilibili-account-uid-lookup.md — B站 账号名→UID 查询与批量数据采集（relation/stat 免登录验证、移动端搜索页免签名首选、wbi 接口+签名与风控行为、同名账号交叉验证铁律、execute_code 50 次调用上限、输出规范）。
- references/xiaohongshu-topic-strategy.md — 小红书选题方法论（2026-08 验证）：平台医疗治理红线与账号定位推论、选题四判断（人群次序/内容形态/三层结构/8:2 杠铃）、产品痛点→选题映射法、dbs-chatroom 五框架选题讨论法。用户完整选题库在 Obsidian 内容增长/小红书选题方向.md。
- scripts/bili_resolve_uids.py — 账号名→UID 批量解析脚本（移动端搜索 exact 匹配 + relation/stat 粉丝校验，`--expect-fans` 拦截同名号），直接可跑。
