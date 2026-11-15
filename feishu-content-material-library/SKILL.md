---
name: feishu-content-material-library
description: Use when 给飞书内容物料库日更选题卡片（选材→DOI→截图→写表）。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [feishu-bitable, medical-content, content-material, dbs]
    related_skills: [medintel-feishu-table, lark-base, dbs-content, dbs-xhs-title]
---

# 内容物料库（情报总表 → 医学内容卡片）

## When to Use

- 用户给「每日医学情报总表」+「内容物料库」两个飞书链接，要求「找一些医生/医学科研者/医学生关注的选题，写进去」
- 要给 SciLink 官号/矩阵产出资讯类图文卡片（封面文案＋标题＋正文）
- 要核对已有卡片格式、批量补题、排期
- 用户丢来一条 `/record/<token>` 记录链接问「帮我看看这个新闻到底是怎么回事」→ 走「选题卡新闻核验」一节（只核不发稿，结尾给判断）

## 对象坐标

> 同一个 Base 下的**选题库（痛点库）**——`产品内容选题库`（`tblW0VnKXJaPlids`）——的建库、拆云文档与表结构重构不在本技能，走 `feishu-topic-library`。本技能只管内容物料库 `tblfAf9h81t9oVq9` 的日更写卡片。

| 角色 | 表格 | wiki 节点 | base_token | 表 |
|---|---|---|---|---|
| 源（选题池） | 每日医学情报总表 | `SeOzwYIv3ihYcWkV8CncZof6nLh` | `LxE4bRFqHaWoyxsPBEFc8BcInOe` | 按月分表，如 `2026-10` = `tbljRVqpA4FBnwrc`（约 543 行/月）|
| 目标（交付） | 内容物料库 | `DTcUwQwEBi1bTWkSdN9c09Kbnnf` | `PCm9b6saQaJ8gmsqAxTcqWHtnVj` | `tblfAf9h81t9oVq9` |
| 排期 | 选题排期表 | `YvbMwgi0piEsWbk9hrncVZqAnbg` | `Ub3bbJcwsacKULs03Ysc3UmBnCe` | `tbltQrk5R0TtQmWi`（`选题`=text `fldL1PU5nb`、`物料`=url `fldGdlQ9vk`，物料写 `[内容标题](wiki url)`）|

源表字段：`标题/摘要/医讯AI摘要/链接/原文链接/医讯来源/MedHOT分类/MedHOT评分/MedHOT精选/医讯主分类/发布日/播放量/博主主页`。
行分两类：**医讯类**（有 MedHOT 评分／来源＝海外站、medRxiv、bioRxiv、ScienceDaily…）与 **B站博主稿件类**（有 播放量＋博主主页）。做卡片只用医讯类；博主稿只作对标参考。

## 目标表字段（15 列，以 `+field-list` 实测为准）

| 字段 | field_id | 类型 | 口径 |
|---|---|---|---|
| 内容标题 | fldhbzJpN2 | text | 原文标题忠实直译，专有名词/缩写留英文，药名「中文通用名（英文原名）」|
| 话题度 | fldA6S6euY | number | 0-100 整数＝痛点相关(0-40)+时效(0-30)+可讨论(0-30)，打分理由只写汇报不进表 |
| 内容分类 | fldMEfxgp5 | select 单选 | 只能用已有 10 个选项，禁止新增 |
| 原文发布日期 | fldxUgwRLN | datetime | 取页面自带日期；写入用**页面印刷的日历日期 + `09:00`**（Asia/Shanghai），别把美东发布时间原样换算成 +08:00——上午发的稿会跳到次日。datetime 只吃 `YYYY-MM-DD HH:MM`，塞说明文字会 800010403 |
| 来源链接 | fldPmLFm7v | text | 纯 URL，无 markdown |
| DOI | fldU3IEPbd | text | **一条可直接粘贴到评论区的引文**：`<原文英文标题>. DOI: <10.xxxx/xxxxx>`（标题取 Crossref 回传的英文原题）。确实无 DOI 的写 `<内容标题>. 无（原因）`，标题照留、原因自证——用户已不再把出处放在正文里，这一列就是唯一出处 |
| P2截图 | fldt075IAZ | attachment | DOI 指向的文献页（无 DOI 才退回新闻页）|
| P3截图 | fldEMsdmhF | attachment | 同页关键结果段，黄条高亮数字 |
| 封面建议文案 | fldXY4cwQ2 | text | ≤20 字钩子 |
| 图文建议标题 | fld6INSLTV | text | ≤20 字，最多 1 个 emoji |
| DS建议正文 | fldqTWRrDy | text | 初稿，常规 ≤1000 字含 3-6 个 #标签；从云文档并入的长稿原样保留、不截断 |
| 润色正文（文档里常被叫「Kimi润色正文」，**表内实名是「润色正文」**） | fldHZF29L7 | text | **写稿交付模式下这一列存云文档纯 URL**（正文只留在文档里）；只有轻量补数据 / 长文并入 / 没有建文档时才存正文文字。`--filter-json` 按字段名过滤时要写实名 |
| 物料文档 | fldy8z10Xu | text | 该记录对应的云文档 wiki 链接（纯 URL），写稿必填，方便从表跳文档 |
| 专题 | fldcVHamCO | select 单选 | 会议／事件整批选题的合集标记，如 `ESMO2026专题`（与「系列」并存，见下节）|
| 封面图 | fld03IouOZ | attachment | **留空不动**（属出图环节）|
| 封面图（带文案）| fldRpLHRbd | attachment | **留空不动** |
| 系列 | fldnwSTWwF | select 单选 | 2026-10 新增，用于把散条归拢成可排期的系列（见下节）|

只写这 14 列；不新增字段、不改列顺序、不改视图、不删已有记录。

### P2／P3 截图规格（用户口径）

**来源页真实截图，不是自绘信息卡。** P2 对象是 **DOI 指向的文献页面**（标题＋摘要开头＋主图），新闻页只是无 DOI 时的退路；P3 是同页最关键的结果段（主要终点／效应量／CI／样本量），关键数字加半透明黄条 `rgba(255,235,59,0.55)` 高亮，只涂词和数字，不整段涂。规格统一 1080×1440（3:4）。

生产用 `scripts/shot_web_card.py`（camofox 真浏览器渲染 → 注入高亮 → 全页截图 → 裁 3:4），决策表与坑见 `references/p2-p3-web-card-screenshot.md`：

> ⚠️ **P2／P3 的更新版以 `scilink-pic/scripts/shot_p2p3.py` 为唯一真源**：它多了三类处理——cookie/Sponsor 空广告位按文本特征删除、`naturalWidth===0` 的懒加载大图连图注一起隐藏、黄条只改文本节点（避免把 `href` 里的数字一起替换成裸代码），并且按正文栏宽度裁 3:4（不会留 1/3 白边）。本目录的 `shot_web_card.py` 保留作历史兼容，不要在两边各改一份。

```bash
python3 <skill_dir>/scripts/shot_web_card.py \
  --url "https://pmc.ncbi.nlm.nih.gov/articles/PMCxxxxx/" \
  --slug icraki --kw "63.1%,53.5%,1.30" [--selector p] [--skip-p2|--skip-p3]
# 输出 /tmp/shots/<slug>-p2.png / -p3.png（1080×1440）＋ JSON（http/marks/y2/y3）
```

要点：
- 有 PMC／出版社 OA／预印本就用它们截（版面干净、可全页渲染）；付费墙打不开才退回新闻页并在汇报里写明实际版本。
- 每张都用 `vision_analyze` 自检：标题/日期可读、无大片空白、无登录墙/广告/评论区、高亮落在数字上。
- 批量出图后再拼一张 contact sheet（缩略图网格）扫一眼整体，比逐张看省一半时间；低墨量（ink<4%）或两张图像素差≈0 的格子重点回看。
- 上传：`+record-upload-attachment --record-id <id> --field-id fldt075IAZ --file <P2>`（P3 用 `fldEMsdmhF`），文件名带选题关键词 `{内容标题}-p2.png`，再 `+record-list` 读回确认。
- 老办法（curl 存本地副本 + Chrome `--headless=old` 截图）仅适用于**静态页**；遇到 403 或正文在内部滚动容器里时它会截出一张白图，别在这里反复调。

## 封面生成（两条封面列，第三步）

- 文案直接取 `封面建议文案`；中文逗号是分行标记，不上图。
- 插画：image_gen 走**英文** prompt（中文医疗 prompt 易被审核拒），扁平蓝白矢量、主体居中、底部 y≥950 留给文字层；主体必须对应主题（结肠癌→结肠+免疫细胞、HPV→宫颈+病毒+AI 大脑），禁药瓶摆拍/听诊器凑数。
- 合成用 PIL 手动重建 overlay（psd-tools 的 composite() 不处理图层蒙版）：顶部白渐变 `exp(-y/180)`、235→0；底部蓝渐变 (20,60,130)、1050→1440；logo 宽 540 贴 (270,26)。文字 MiSans-Heavy 纯白＋`GaussianBlur(6)` 灰阴影，y≈950 起，最长行 ≈990px 自适应字号。
- 上传：无文案→`fld03IouOZ`、带文案→`fldRpLHRbd`，`+record-upload-attachment` 一次只传一个字段；成品另存 `~/Documents/Obsidian Vault/医时工作/刀客轻研SciLink/`。
- 完整提示词、素材路径、可跑脚本见飞书《@刀客轻研SciLink 内容生产SOP》「3.封面生成」（doc `ORrCd9ksRoXeJHxsj1VcMsy5nVI`）。

## 受众与主视角（每条只挂一个，不混着写）

① 要发论文的医学生/规培生　② 靠论文评职称但不太懂统计的临床医生　③ 懂科研的临床科研工作者

方法学/工具 → ②；科研捷径/选刊 → ①；吐槽/政策 → ①③；重大临床研究/新药 → ②③。

写作硬要求：**每个术语首次出现紧跟一句大白话＋一个生活化比喻**（例：dMMR＝肿瘤细胞“校对 DNA 错字”的功能坏了，像复印机坏了；CRRT＝一台机器守着一个病人慢慢做 24 小时）。缩写先写中文全称再给缩写。

## 两列文案（不是二选一）

> **先分清落库位置**：写稿交付时 `DS建议正文` 存初稿文字、`润色正文` 存云文档纯 URL（成稿只在文档里，见下节硬规则）；轻量补数据时两列都留空。下面讲的是稿子本身怎么产出，不是往哪存。

- `DS建议正文`＝初稿，按上面房式写，常规 ≤1000 字含 3-6 个 #标签（长文档并入的稿子例外，保留全文）。
- `Kimi润色正文`＝用 **Kimi K3（`k3-256k`）**重写：句子更短、去「首先/其次/综上所述/在这个时代」这类腔调、能中文就中文、事实与数字不增不减、术语保留原文。
- Kimi 通道：key 在 `~/Documents/Hermes/APIs/kimicode API.rtf`，端点写死 **`https://api.kimi.com/coding/v1/chat/completions`**——同一把 key 打 `api.moonshot.cn` 回 401、打 `api.kimi.com/v1/...` 回 404；**temperature 只能等于 1**（传 0.6 直接 400 invalid temperature）；它是推理模型，`max_tokens` 给足 4000，给小了 `content` 是空串、只剩 `reasoning_content`。现成脚本：`scripts/polish_kimi.py`（3 线程、3 次重试、原地写回）。
- **润色稿必须逐句对差再入表**：模型习惯自己加一句开头 hook，且会把「有风险」升级成「已被正式摆上台面」这类 DS 稿没有的断言——凡初稿里找不到依据的句子整句删掉，不保留、不软化。
- **结尾不写免责声明**：用户已明确删掉「⚠️仅为医学科研资讯分享，不构成任何…建议」这一族，DS 与 Kimi 两列都不要写。真有信息量的口径提示可以留，单独成句写成「⚠️{口径}」（例：⚠️具体执行以官方标准原文为准），别和免责话术拼在同一句里。
- **压缩长文时把源 DOI 当白名单喂进去**：凡是让模型把长稿（多篇论文串讲、云文档迁移的稿子）压到 ≤1000 字，提示词里原样列出源文 DOI 并声明「只准出现这些」，输出后用正则抽 DOI 与源列表比对，出现任何非源列表 DOI 就重跑。
- Kimi 完全不可用时才退到 GLM（`https://open.bigmodel.cn/api/coding/paas/v4/chat/completions`，key=`~/.hermes/.env` 的 `GLM_API_KEY`，非 coding 端点常回 429 余额不足），并在汇报里标注实际模型。

## 「系列」字段：把散条归拢成可排期的合集

字段 `fldnwSTWwF`（select 单选），10 个固定选项，**全表每条都要有值**，新增记录入库时同步打标（别留空，空值等于无法按系列筛）：

`合规必读` `科研方法` `数据库与工具` `统计与解读` `写作与投稿` `学术诚信` `期刊与评价` `职业与基金` `行业观察` `临床资讯`

判定优先序（从上到下命中即停，避免“统计”“方法”这类泛词抢走归类）：

1. 学术诚信：诚信/撤稿/论文工厂/造假/伪造/礼物作者/虚假引用
2. 合规必读：伦理审查/遗传资源/研究者发起的临床研究/真实世界证据指导原则
3. 行业观察：倦怠/跑路/卷科研（再往后是行业/舆情/医保/制度/报告）
4. 科研方法：批判性评价/目标试验模拟/PICO/临床问题清单/模型选择；
   另：`HitSV`、`结构变异检测` 这类**方法学论文里的工具**归 `数据库与工具`
5. 期刊与评价：核心期刊/预警/分区/影响因子/审稿时长/职称（“评价”单独出现不要用，会把“批判性评价”抢走）
6. 写作与投稿：投稿/审稿人/回复信/cover letter/预印本/图表/返修
7. 统计与解读：统计/P值/多重比较/风险比/样本量/判别力
8. 数据库与工具：MIMIC/NHANES/SEER/数据库/R语言/SPSS/Scopus 等库与工具名
9. 科研方法：方法/设计/队列/模型
10. 职业与基金：基金/国自然/职称晋升/转行/MSL/规培/会议征文
11. 其余 → `临床资讯`（新药/临床试验/指南/观察性研究/预印本/公卫/基础研究默认落这里）

批量打标用一次 `+record-batch-update`（map 形状），**每批 ≤40 条**，157 行约 4 批；改完必须 `+record-list` 读回统计各选项条数，确认无空值。

**合规必读是常青件**（伦理审查办法 2023、遗传资源细则 2023、IIT 管理办法 2024、RWE 指导原则 2020）：日期老旧，混在日更流里会被当旧闻跳过，排期时单独走合集/置顶，不按资讯追时效。

**系列/分类这类需求，交付物是表内字段＋全表打标，不是一份外部清单文件。** 只写一份 md 清单交过去，用户的第一反应是「不是直接合并到我多维表格里的吗」——分类信息只有进表才能筛选、排期、发给他同事看。做法：`+field-create` 建 select 字段 → 按下面的优先序给**全表每一条**打标（不能只标刚写的那几条，稀疏散落的字段等于没用）→ `+record-list` 读回统计各选项条数确认无空值。外部清单最多留作附件（讲法建议、排期顺序），开头写明「表是唯一真源」。

原任务写着「不新增字段」指的是补数据阶段不许乱加列；**用户明确要分类/系列/标签时，建字段就是他要求的动作**，先建再打标，不要为了守旧约束改成交外部文件。

## 选题标准（用户口径）

受众＝**医生 / 医学科研者 / 医学生**，不是患者科普。优先级：

1. 临床可改变决策的：新药获批、指南/共识更新、诊断阈值或筛查标准被挑战
2. 有硬数据的队列/随机试验（样本量＋HR/OR/AUC/灵敏度）
3. 科研方法与工具类（真实世界数据建模、生信工具、系统综述检索、AI 辅助科研）——科研者与医学生最爱
4. 反常识/机制意外（如 BCG 降糖、C 肽不恢复）

C 路「补搜什么」不要每次从零想：**10 类稳定主题、优先级、内容分类映射与信源质量分级见 `references/topic-taxonomy-for-medical-audience.md`**（选题/数据库挖掘/读论文检索/写作投稿/统计反例/诚信撤稿/基金/会议/职业路径/AI 与出版伦理）。

排除：纯患者科普、纯美国医保/诉讼/人事八卦、无数据转述。**地方性政策一律不收**——市/县级卫健委、人社局、考试中心发的申报通知、数据填报、评审细则（如「天津市卫生高级职称临床评价指标数据填报」这类流程通知）没有传播价值，账号受众是全国范围的医护，只收国家部委级（国家卫健委、人社部、国家医保局、NMPA）或全国性行业标准/指南；省级政策仅在能代表全国趋势（如北京「破四唯」被其他省跟进）时才考虑，且要写全国视角、不写某地流程。与目标表已有 `内容标题`/`来源链接` 去重后再写。同一**持续事件**的后续数据可以再出一条（例：同一波疫情先报某州破千例，后报全国总量翻倍），但必须换角度——量级／全国 vs 单州／接种数据 vs 住院死亡，并用 `docs +fetch` 调出旧稿逐段比对，避免把旧稿的数字再抄一遍；角度换不动就合并进旧稿，不新增一条。

## 两阶段交付：文字先行，生图后置（2026-10 用户定，强制）

**文字免费，生图烧算力**：一批选题进来，先把文字全线做完并定稿，再统一出图。不许"边写边生图"，也不许替用户"顺手先出一张看看"。

| 阶段 | 做什么 | 交付物 | 什么时候停 |
|---|---|---|---|
| **A 文字** | 选题 → 核链接/DOI → 标题（dbs 工具箱）→ 封面文案 → DS 初稿 → 润色稿 → 写入表格四列 | `封面建议文案`（≤20 字）/`图文建议标题`（≤20 字）/`DS建议正文`/`润色正文` 四列齐 + 读回验收 | **停在这里等用户点选哪几条要出片**。文字未定稿不生成任何图 |
| **B 出图** | 只对用户点名的条目：封面（无文案→带文案）→ P2／P3 来源页截图 | `封面图`/`封面图（带文案）`/`P2截图`/`P3截图` | 文案改动优先「重压文案」（`add_cover_text.py`），不重跑模型 |

判断标准：**用户没说"出图/出封面/要图"，就不进 B 阶段。**

### 专题（系列之外的合集标记）

字段 `专题`（`fldcVHamCO`，select 单选，2026-10 新建）。会议／事件类整批选题（ESMO、ASN、ECTRIMS、AACR 等）入库时**一次性全打上专题名**（如 `ESMO2026专题`），方便整组排期与统一封面；`系列` 字段照旧管内容类型（临床资讯／统计与解读…），两者并存不互替。

**专题在封面上的呈现（用户 2026-10 口径）**：专题名做成**顶部居中的深蓝胶囊标签**（logo 下方 y≈112），**不占 y≈950 的正文文案位**；原位置照旧放这条自己的 `封面建议文案`。命令：

```bash
python3 <poster skill>/scripts/add_cover_text.py 封面成品.png 输出.png "<封面建议文案>" --badge "ESMO2026专题"
```

## 卡片房式（严格遵守，与已有行一致）

```
{一句钩子式结论或直接上事实，不加 📌}

{背景：谁/何时/发在哪/什么设计}

核心数据：
▫️ 数据点（同一主题）
▫️ 数据点（同一主题）

为什么值得关注？
{2-3 句：临床或科研上改变了什么}

⚠️ {边界：研究类型限制、未获批、不可外推}

#标签 #标签 #标签
```

**开头不加 `📌`**（用户 2026-10 口径：「没必要每条文案都加这个，去掉」，存量稿不再补）。

**`▫️` 数据块只放同一主题的几个数**：实测被批「前两条是疫情进展、第三条跟疫情进展有什么关系」——疫苗保护力、政策口径这类不同维度的数字，从数据块拿出来写进段落，别混在一堆。

- **正文里不写出处**：`📄 …` 行、段落里的「来源：X」「DOI: …」「XX期刊，2026年X月X日在线」一律不写进 DS／Kimi 两列——出处统一进 DOI 列，正文到 `#标签` 就结束，用户可以整段复制去发。存量记录要按行正则 `^\s*📄` 清理，并顺手去掉句中的「…在线，DOI: 10.xxx」从句。
- **DOI 列＝可直接粘贴的引文**：格式 `<原文英文标题>. DOI: <10.xxxx/xxxxx>`；标题取 Crossref 返回的英文原题（`api.crossref.org/works/<DOI>` 的 `title[0]`），不要用中文译名。没 DOI 的写 `<内容标题>. 无（原因）`，标题也保留。

### 事实与措辞核验（比链接更容易翻车，详见 `references/source-and-doi-verification.md` 第 5 节）

- **绝对化断言必须回到原文措辞**：原文写「没有标志物能可靠预测**结局**」，就不能写成「没有标志物」或「无法预测」——后者把已在指南里的分流检测（细胞学／HPV 分型／p16-Ki67 双染／甲基化）一起否掉了，医生读者第一反应就是反驳。凡是「0 个」「无法」「从来没有」这类断言，先找到原文那句限定语，把限定词（结局／单指标／常规临床）原样写进标题和正文。宁可写「难以预测」，不要写「无法预测」。
- **术语用指南里的规范搭配，不自造组合词**：`分流检测 / 分流方法`（triage）是筛查指南里的写法，「分流工具」不算规范；首次出现跟一句大白话（HPV 阳性后决定谁转诊阴道镜、谁继续观察）。
- **观点文章与研究结论分开写**：Trends／Lancet Comment 这类稿件只有主张没有新数据，正文写「作者主张……」，⚠️ 里注明「未验证、不能进常规临床」。
- **期刊名和作者写全**：首次提到期刊用书名号＋英文全名（《Trends in Molecular Medicine》，不用缩写或中译顶替），紧跟作者与单位——用户会追问「杂志全名到底叫什么」「作者是谁」。
- **用户自己给的标题／封面优先照用**：他偏好朴实口语（一问句式，如「HPV癌变为何难预测？」「未来研究方向在哪？」），不要拿公式腔去改写；交给你的版本只做两件事——事实核验、字数核对（≤20），改写建议放汇报里让他挑。

- `封面建议文案` ≤20 字（含标点），结论前置带数字，用空格断句（如「查肿瘤基因 别只按年龄」）；写完数一遍字数，不超 20
- **封面与标题要落在病人/门诊那一句话上，不要研究者视角**：用户否过「预测HPV癌变 不能再找单一指标」这类从作者立场出发的封面，改成「HPV阳性 没人能说准会不会癌变」这种病人心里话＋反差。写法：先想「患者/医生看到这句话会不会停一下」，再压缩到 ≤20 字。
- **封面文案 ≠ 图文标题，两者分工呼应**：封面（图上大字）给结论/反差/数字，标题（发布页）给人群/悬念/立场；不得同义重写，也不能只换一两个字。写前先定一句「这条想让人停在哪」，封面负责“楞一下”，标题负责“对号入座”。
- **标题必须先定、且必须调 dbs 工具箱**：`dbs-xhs-title`（从 75 公式选并标注编号）→ `dbs-hook`（前 3 秒）→ `dbs-content`（正文结构）。视角只能锁在三类人（要发论文的医学生/规培生、靠论文评职称的临床医生、懂科研的临床科研工作者），不写患者科普、不写研究者自述。顺序：定标题→定封面→写正文，用户确认标题后才动正文。
- `图文建议标题` ≤20 字（含标点，硬规定），最多 1 个 emoji，用 dbs-xhs-title 的公式编号可追溯；英文缩写＋数字最容易超字，先数再定
- **医学科普／辟谣类选题，标题与事实边界同轮交付**：dbs 公式偏好极端化断言（「95%的过敏都不成立」这类），标题可以冲，但同一轮必须给一句正文红线（如「高危患儿仍须完整评估，不能直接激发」），否则用户拿去发就是标题党＋医疗误导。同时标一句这条更适合医护还是更适合破圈到患者家属——两群人的痛点词不同（医护吃「多输液／二线抗生素」，家属吃「能不能吃青霉素」）。
- 本表**没有**「建议发布日期」列；日期列是 `原文发布日期`（页面自带的发布日），排期另议

## 选题卡新闻核验（用户丢 record 链接问「这新闻到底怎么回事」）

这不是写卡片，是**替他把这条新闻核到底**再给判断。坐标解析照「反向流程」开头那两条：`/record/<token>` 里的 token 是 share token，必须先 `+url-resolve` 换 `base_token/table_id/record_id`；`+record-get` 的 `- 字段: 值` 清单直接读，`hint.fields` 那种整块字段定义不要回显给用户。

流程：

1. 取卡上五个值：`内容标题／来源链接／DOI／原文发布日期／内容分类`（外加话题度）。
2. 抓原文（`web_extract`），**再补第二家独立媒体**——只有一个信源的事件稿不交。
3. 有 DOI 就进题录层（配方在 `primary-paper-backtracking`）：Crossref 拿题名/期刊/日期/**摘要**，PubMed 拿 `PublicationType`，OpenAlex 拿 `oa_status`。**先判综述 vs 原创研究**：State-of-the-Art Review / Comment / Perspective 的「数据」都是二手，正文必须写「该综述称…」。
   - 出版社页 `web_extract` 常被直接拦（AAP／Springer 回 `Failed to fetch url`），但 `browser_navigate` 通常还能渲染出摘要页：页面顶部那行 `State-of-the-Art Review | November 04 2026` 是判文章类型最快的一眼，同页还带出全部作者单位与单篇价格（如 `$36`）——「获取状态」按它写，不要猜。
   - **Crossref 的 JATS 摘要足以支撑一篇诚实稿子**：摘要写到的结论可以写；摘要没写的剂量、流程、亚组一律不写，或改写「公开临床路径给出的做法是…」并注明出处不是该文。
4. 一手原件（政府 PDF、清单、监管文件）被拦时换官方整理页/高校合规页交叉，不拿媒体转述顶一手。
5. 交付形状（用户认这个）：**结论先行一句** → 文献级元数据表（期刊/日期/文章类型/DOI/作者与单位/获取状态与单篇价格）→ 摘要要点逐条 → 背景操作细节（**注明来自公开指南，不是该文正文**）→ 给他的判断。

判断那一节必须拆成三件事写：

- **受众相关性**：学科层面无关就直接说无关（受众是医生/医学生，量子物理论文再热也是 0）；真有关系的通常是「署名单位、合规、经费」这类机制层，不是学科层。注意别把机制层说成「这条也能用」——它的正确用途是当替换选题的钩子。
- **分类有没有标错**：综述被标成「观点与评论」、方法学文章被标成「前沿研究」时，主动说该改哪一列。
- **能不能做**：不相关就建议「不优先」，并给一个能落回受众的替代角度；不要为了保住这条硬扯相关性。

纪律：正文里每个数字都要能在原文找到原话；推断（例「附属医院是否落在清单覆盖内」）**自己标成推断**并写明缺哪份官方条文。用户说了「你先不用管」之后，不再回头追问那张表要不要改，只答当前问题。

## 每日更新执行流程（日更任务按这个顺序）

1. **先做差集，再选题**：`+record-list --limit 500 --format ndjson --output /tmp/existing.ndjson`，解析每行的 `record_id/内容标题/来源链接/DOI`。已入库的绝不重复录（幂等优先）；DOI 列为空的老行只能靠标题＋链接去重。
2. `lark-cli base +url-resolve --url '<wiki链接>' --as user` 拿 base_token；`+field-list` 取字段 ID（以实跑为准，别信过期文档的列数）。
3. 三路素材：A `MedHOT` **全量**（`/api/site/hot` 只是 Top 10 精选，拿它当日更会严重漏条目）：查本地 Postgres `medhot` 库的 `stories`＋`story_signals`＋`articles`＋`analyses.selected`，配方见 `references/medhot-full-inventory.md`；B 每日医讯库 `~/Documents/Hermes/数据/医学素材库.db`（`平台 in ('国外源','中文源')`，按 `发布时间` 圈窗口）；C 联网搜主题，每类≥2 条：固定 10 类清单与优先级见 `references/topic-taxonomy-for-medical-audience.md`；中文 SEO 站（选刊指南站、软件测评软文、知乎/CSDN）日期缺、正文空，优先官方机构页与期刊正式文章。
   - **不依赖这两个中间层的备选**：跑 `scripts/fetch_all_sources.py --days N [--dept radio|icu|anes|cardio|resp|onc]`，直接抓它们的同源数据（欧洲PMC 按 ISSN + RSS）。源清单、可达性三档、覆盖验证与日期陷阱见 `references/medical-news-source-map.md`。自建的真实收益是**可定制**：补某科室只需往 `JOURNALS` 加一行 ISSN。
   - ⚠️ **抓取/信源已独立成 `scilink-topic` 技能**（同名脚本与 reference 各一份）。**以那份为唯一真源**：加刊、改判空规则、改科室关键词都改那边；本目录的拷贝只为历史兼容，不要在两边各改一份——真源分叉后两次日更会给出不一致的源表。
4. 定选题与唯一主视角（①医学生规培生 ②临床医生 ③临床科研者），一条只挂一个。
5. **逐条核链接与日期**：打开原页比对标题（不能只看域名），取页面自带 `datePublished`／正文日期行；方法见 `references/source-and-doi-verification.md`。
6. 定 DOI 并验证（Crossref／EuropePMC，同上 reference）；无 DOI 的（会议摘要、监管文件、政策、博客、教程）留空并写原因。
7. 出 P2／P3 截图（`scripts/shot_web_card.py`），再动笔写文案——图先出，slug 与文件路径先固定。**例外（用户拍板过的降级）**：当源站集体反爬（Nature/NEJM/MedPage 同时 403/500）导致出图不可行时，先把 14 列里的文字列全部写完入库、P2／P3 留空，再单独安排补图；不要为了等图把整批文字压着不交。
8. 写 DS 初稿（房式见下，术语首次出现跟一句大白话）。
9. 写润色版到 `Kimi润色正文`：用当前可用的中文强模型重写（Kimi 通道不可用时用别的模型并在汇报里标注）；两列都存。
10. 上传附件＋写记录（分三步，顺序不能颠倒）：
    a. `+record-batch-create --json @/tmp/payload.json`，payload ＝ `{"create_records":[{<field_id>: <value>}]}`；返回的 `record_id_list` **按提交顺序**对应每条，立刻存成 内容→record_id 映射。
    b. 逐条 `+record-upload-attachment --record-id <id> --field-id fldt075IAZ --file <P2>`（P3 用 `fldEMsdmhF`），每次只传一个字段；34 个文件约 2 分钟。
    c. 无 DOI / 取不到日期的原因用 `+record-batch-update --json '{"update_records":{"<recId>":{"fldU3IEPbd":"无（…原因）"}}}'` 补写；**datetime 列写不了字**，日期原因只能放汇报。
11. 读回验收：`+record-list --format ndjson`，逐行核对 14 列是否落位（尤其 DOI／日期／两个附件）。

### 轻量模式：只写 6 列（补数据，不截图不写文案）

用户在日更里会单独要求「只填内容标题/话题度/内容分类/原文发布日期/来源链接/DOI，其余列留空」。这时跳过截图与两列文案，节奏改成：

1. 差集与 `+field-list` 照旧；`+record-list --limit 500 --format ndjson --output /tmp/existing_<新名>.ndjson --overwrite`（同名文件会 `failed_precondition`）。
2. **先跑脚本批量核验，再人工处理例外**：一个 Python 脚本串行跑「curl 取 http code + `<title>`/`datePublished`」＋「Crossref `works/<DOI>`」，全部落 JSON；只对被 403 的站逐条走 `web_extract`。这一步决定整批能不能按时落库。
3. 来源链接的选择：有论文就用论文页（`nature.com/articles/<code>`、出版社 URL 或 `https://doi.org/<DOI>` 规范链接——出版社 403 时 doi.org 形式的纯 URL 比抓不到的页面链接更稳），无论文的新闻/政策才用报道页。
4. 5-6 条一组 create + 立刻读回（**28 条约 5 批**跑得完，别攒到最后）。缺日期的那条**payload 里直接不写 `fldxUgwRLN` 键**，批量照样成功，不要塞「未标注日期」这类文字。text 列直接传**纯字符串**（`{fldhbzJpN2: "标题", fldPmLFm7v: "https://…"}`）即可，不必构造成 `[{text:…, link:…}]` 段数组（两种都收，纯字符串更好拼）；同一会议多个 LBA 不要共用同一篇 recap 链接，四条一起报的汇总页会被去重自检第④项判重——每条另找单试验报道页或改走 DOI。
5. **读回校验写成脚本跑，不靠肉眼扫表**：`+record-list --overwrite` 落 ndjson 后，用新 `record_id` 集合做四项断言——①总行数＝老行数＋新增数且新增 id 一条不缺；②`内容分类` 取值 ∈ 合法 10 项集合（`+field-list` 拿的 options）；③`来源链接` 是纯 URL（无空格、无 `](` 这类 markdown 残留）；④任意两条之间链接不得相等，标题 token 交并比 >0.75 要人工看一眼。四项全绿再交付。
6. 汇报里每条给：标题｜日期｜分类｜话题度（含三段打分）｜主视角｜DOI 的 Crossref 题名核验结果｜链接标题是否对上｜留空项与原因。剔除的条目也要写「为什么剔」（例如找不到支撑论文、地方性政策、同一事件多版本只留一版）。

**日期空白不是终局**：先按 `references/source-and-doi-verification.md` 1.3 再试一次 camofox 取 `citation_online_date`，能补的在同一次会话里用 `+record-batch-update` 写回（用户会注意到「上次空着的日期补上了」，这算加分而不是返工）。

批量技巧（很重要）：**按 5-6 条一组走完全流程并立即写表**，不要"先全部研究→再全部截图→再全部写文案→最后统一写表"。日更没有 deadline，但会话有迭代上限：一次性堆 17 条会让研究做完、图也截完、文案也写完，却没来得及落库。每组组内流程仍是素材→核链/DOI→截图→双列文案→上传写入→读回核对；交不了的条数写进汇报，已入库的永远是交付。

## 存量维护：云文档正文并入 / 免责声明清除

老记录的 `DS建议正文` 可能存的是飞书云文档链接（`[标题](https://my.feishu.cn/wiki/<token>)`）。用户要求把正文搬进表、文档删掉时按这个顺序做（**先落库再删文档**，删文档不可逆）：

1. 扫出链接：`+record-list --format ndjson` 后正则匹配 `my.feishu.cn/wiki/`，连 `record_id` 一起记下来。
2. 取正文：`lark-cli docs +fetch --doc "<wiki URL>" --doc-format markdown --as user` → `data.document.content`（顺带有 `document_id`）。
3. 清洗（云文档是编辑稿，不剥会混进整套脚手架）：去 `<title>…</title>`、去与记录标题重复的首行 H1；若含 `正文（…）` 行，只取该行之后的内容；去 `**`/`*` 标记、压缩空行。
4. 写回：`+record-batch-update`，形状是 map——`{"update_records":{"recX":{"fldqTWRrDy":"<正文>"}}}`。DS 列可以超过 1000 字（长文原样保留），只有 Kimi 列卡 ≤1000。
5. 补 `Kimi润色正文`：先全表查空，把所有空列一起补掉，别只补点名的那批。
6. 删文档：`lark-cli wiki +node-delete --node-token "<wiki URL>" --include-children=false --as user --yes`（high-risk，用户点名要删才执行）。删完逐个 `+node-get` 复查，确认查不到再汇报「已删除」。
7. 免责声明清理：按行匹配 `^⚠️\s*仅为医学科研资讯分享`；纯免责句整行删；后面带实质口径的（「具体执行以官方标准原文为准」「数据以原报告为准」）保留 `⚠️` + 后半句，别把有用提示一起删掉。

## 物料文档：每条记录一篇（四图并排 + 文案）

用户说「把生成过封面图的条目整理成一个个云文档、挂到多维表格下面当子文档、再把标题和链接回填排期表」时走这个流程。**图必须并排，不要纵向堆叠**——四张 3:4 竖图顺序堆下来太占地方，用户明确要求分栏。

1. **筛记录**：`+record-list --filter-json '{"logic":"and","conditions":[["封面图（带文案）","non_empty"]]}' --format ndjson --output /tmp/cover_with_text.ndjson --overwrite`（filter 支持字段名）。再用全量 ndjson 独立数一遍「附件字段非空」的条数对齐，别把快筛结果当全量。
2. **下四张图到同一目录**（`封面图` `fld03IouOZ` / `封面图（带文案）` `fldRpLHRbd` / `P2` `fldt075IAZ` / `P3` `fldEMsdmhF`）：`base +record-download-attachment --record-id <id> --file-token <token> --output /tmp/feishu_docs/plainNN.png --overwrite`；命名固定 `plainNN / coverNN / p2NN / p3NN`，NN＝记录序号，后面 XML 直接引用。
3. **建子文档**：`wiki +node-create --parent-node-token <bitable 的 wiki node_token> --obj-type docx --title '<内容标题>' --as user`。
4. **一次性写内容**：`docs +update --doc <obj_token> --command overwrite --doc-format xml --content @/tmp/feishu_docs/xmlNN.xml --as user`，CWD 必须是图片目录（`path="@./x.png"` 只认当前工作目录）。生成 XML 用 `scripts/build_material_doc_xml.py`，不要手抄模板。
5. **读回验收**：每篇 `docs +fetch --doc-format markdown`，判定条件是 `feishu.cn/file/` 出现 **4** 次、`<column` 出现 4 次、四条 caption 齐全；三者缺一就是有图没落位。
6. **回填排期表**：`+record-batch-create` 新增记录，`选题`＝内容标题、`物料`＝`[内容标题](<wiki url>)`。表里原有的空占位行不要拿来填，也不删——用户自己留着用的。

固定文档结构（顺序不能换）：

```xml
<title>内容标题</title>
<h1>封面与截图</h1>
<grid>
<column width-ratio="0.25"><img path="@./plain01.png" caption="封面（无文案）"/></column>
<column width-ratio="0.25"><img path="@./cover01.png" caption="封面（带文案）"/></column>
<column width-ratio="0.25"><img path="@./p201.png" caption="P2 来源页截图"/></column>
<column width-ratio="0.25"><img path="@./p301.png" caption="P3 关键结果截图"/></column>
</grid>
<p>封面文案：…</p>
<h1>图文标题</h1><p>…</p>
<h1>正文</h1><p>润色正文按行拆的段落…</p>
<h1>出处</h1><p>DOI：…</p><p>来源链接：…</p><p>内容分类：…</p><p>原文日期：…</p>
<h1>附：DS 初稿</h1><p>…</p>
```

- 各列 `width-ratio` 之和必须等于 1；三图时取 `0.333333`，四图取 `0.25`。
- `<column>` 里可以放 `<img>`（实测可渲染），所以分栏图不用 `+media-insert`（那条只能追加到文末，图会全挤在文档最后）。
- 正文字段是多行文本：按行拆成多个 `<p>`，并转义 `& < >`，否则空行和特殊字符会被吞。
- 交付时提醒一句：3:4 竖图占 1/4 栏会偏小、要点开看；嫌小就改 2×2（两张封面一排、P2/P3 一排）或封面单独一行。

## 写稿即建文档：成稿的交付位置是子文档，不是表格列（硬规则）

用户说「写稿」「把这几篇写一下」「优化正文」时，**默认交付物＝每篇一个 docx，挂在内容物料库节点（`DTcUwQwEBi1bTWkSdN9c09Kbnnf`）下**；表格只放指针与初稿：`润色正文`＝云文档纯 URL、`物料文档`＝同一 URL、`DS建议正文`＝初稿文字。**把成稿正文直接塞进 `润色正文` 文字列会被打回**——表格列里看不到结构、排版、出处，用户会问「你写到哪去了」。

会议／事件专题的文档名带前缀：`<专题名>｜<内容标题>`（全角竖线 `｜`，不是 `|`），新建时一次写对：

```bash
lark-cli wiki +node-create --space-id <space> --parent-node-token DTcUwQwEBi1bTWkSdN9c09Kbnnf \
  --obj-type docx --title 'ESMO2026｜<内容标题>' --as user
lark-cli drive +update-title --url <wiki URL> --title 'ESMO2026｜<内容标题>' --as user   # 已建好的改名
```

文档内部固定六节：`图文标题` → `正文`（发布用成稿）→ `出处` → `附：DS 初稿`，顶部一条 `<blockquote>` 放元信息（专题、封面文案及字数、出图状态）。正文按手机阅读拆行（段间空行、段内每句 `<br/>`，函数见 `scilink-writing`「文档排版」）。

**建节点后不要把输出管道接 `head -c`**：截断的 JSON 解析会抛异常，但节点其实已经建成了——此时**绝不能重建**（会得到两篇同名文档）。恢复办法：

```bash
lark-cli drive +search --query "<标题里独一无二的片段>" --as user
# result_meta 里取 url（wiki 链接）、token（node_token）、icon_info.token（obj_token）
```

`wiki +node-list --parent-node-token <bitable>` 对 bitable 父节点恒返 0 条，别拿它判断「建没建成」。

### 新闻体文稿（用户指定「体裁为新闻体、平实易读」）

四段式，通篇不加 emoji、不加 `#标签`、不写钩子句、不用「重磅／震惊／颠覆」：标题（直陈新闻事实，不做标题党）→ 导语（何时、哪本刊、什么类型文章、讲了什么）→ 主体 4-6 段（核心数字／代价／政策或背景／关键人群／怎么做／边界）→ 出处节（原文题录＋DOI＋作者单位＋**获取状态**）。

- **获取状态必须写清**：全文付费就写「全文付费，本文依据期刊摘要及公开的临床路径写作」。剂量、观察时长、抢救药物这类操作细节单独归给来源路径——把路径里的数字写成该文正文的结论，用户会拿原文对。
- 句子短、少形容词；术语仍按上文硬要求，首次出现跟一句白话＋一个生活化比喻。
- 结尾给判断、不给免责声明，并落一句金句（例：「去标签的价值不在于多做一次检查，而在于少一次不必要的用药妥协」）。
- 字数用脚本核，不靠肉眼：`len(re.findall(r'[\u4e00-\u9fff]', body)) + len(re.findall(r'[A-Za-z0-9]+', body))`（汉字＋西文词），交付时同时报「正文字数／含出处总字数」。
- 标题与 `wiki +node-create --title` 逐字一致（见踩坑 36）；与父节点下邻居的命名风格保持一致（直陈事实，不加「｜小红书文案」这类后缀）。

## 反向流程：文案确认后再建云文档（用户点名单条时）

两种触发：①「把内容放到新建的在线文档、文档链接填进润色正文」；②用户给一条 record 链接＋一篇参考文档，要「照这个结构写一篇，放到 XX 选题库下面」。

动手前三件事：

- **record 链接先解析，别当 record_id 用**：`/record/<token>` 里的 token 是 **record share token**，直接 `+record-get --record-id <token>` 会报 `800010701 Record id must start with "rec"`。改用 `lark-cli base +url-resolve --url '<record 链接>' --as user`——一次给出 `base_token` / `table_id` / `record_id` / `record_share_token`，且 `hint.record_data` 已带整行字段值，不必再查一次表。
- **先读参考文档定节序**：`docs +fetch --doc "<wiki 链接>" --doc-format markdown`，照抄它的节名与层级。同一库里有两种形态，别串用：物料文档＝`# 封面与截图`（四图并排 grid）→ `封面文案：…` → `# 图文标题` → `# 正文` → `# 出处`（DOI／来源链接／内容分类／原文日期）→ `# 附：DS 初稿`；长稿文档＝一～七节（封面文案／图文标题／正文／备选标题／备选开头／事实要点／原文全文）；新闻体文稿＝标题／导语／主体段／出处（见下节）。用户点名的那篇是哪一种就写哪一种——用户说「体裁为新闻体」时，不要套物料文档的「封面与截图／图文标题／附：DS 初稿」那套脚手架。
- **记录附件为空也不要删「封面与截图」节**：保留节标题＋`封面文案：…`＋一句「封面图（无文案／带文案）与 P2／P3 截图待出图，出图后按同结构四图并排贴入本节」。节结构与邻居一致，缺图也一眼看得见，比整节省略更好交接。

具体步骤（父节点通常就是目标表所在的 wiki 节点）：

1. 建子文档：`lark-cli wiki +node-create --parent-node-token <wiki node_token> --obj-type docx --title '<内容标题>' --as user` → 返回 `node_token` ＋ `obj_token`（docx）＋ `url`。标题照 `内容标题` 原样；参考文档没带后缀就别自己加「｜小红书文案」，wiki 目录里要与邻居保持一致。
2. 写内容：`lark-cli docs +update --doc <obj_token> --command overwrite --doc-format markdown --content @/tmp/doc_content.md --as user`；`--content` 用 `@file`（长文塞命令行会被截断）。写完 `docs +fetch --doc-format markdown` 读回字符数确认。
3. 回填链接：`+record-batch-update` 写 `fldHZF29L7`（润色正文）＝**纯 URL**。
   - 同一篇还要把文案落进表里的三列：`封面建议文案`（fldXY4cwQ2）／`图文建议标题`（fld6INSLTV）／`DS建议正文`（fldqTWRrDy），并顺手补 `系列`（fldnwSTWwF）——一次 `+record-batch-update`（map 形状）写完，再用 `+record-get --record-id <id> --field-id 封面建议文案 --field-id 图文建议标题 --field-id DS建议正文 --field-id 系列` 投影读回验收。表里这三列空着＝文案还没落库，用户会当成没做完。
4. **补原文全文＋论文附件（用户固定要求：文档末尾必须附原文全文）**：
   a. 追一节「原文全文」：`docs +update --doc <obj_token> --command append --doc-format markdown --content @/tmp/doc_append.md`。分两小节——研究原文（标题/作者/DOI/期刊）全文，与新闻原文全文；**新闻有付费墙的只放公开可见部分并在该节开头注明截断原因**，不拿别的段落凑。
   b. 论文全文从官方 PDF 提取（`pypdf`：`PdfReader(path).pages` → `extract_text()`），先洗掉页眉页脚重复行（`Deng et al. … PNAS`、`https://doi.org/…`）与多余空行，再包进代码块防 markdown 吃格式。
   c. 上传 PDF：`docs +media-insert --doc <obj_token> --type file --file "<本地.pdf>"` → 返回 `file_token`；文件名用 `作者-年份-关键词.pdf`，中文名可用。附件会落在文档最末尾（`<figure view-type="Card"><source name=… mime="application/pdf" …/>`）。
   d. 读回验收：`docs +fetch --doc-format markdown` 应同时命中「七、原文全文」「期刊名/DOI」与 `<figure … mime="application/pdf">`；只看到文字没看到 figure 就是附件没插进去。
   e. PDF 怎么拿到：先查 OA（OpenAlex `open_access.is_oa`／Semantic Scholar `isOpenAccess`）；CC BY 的才能下载转发，非 OA 就在汇报里写「付费墙，未附 PDF」，不硬拉。PNAS 这类 Cloudflare 站的取字节配方见 `camofox-browser-api` 技能「二进制文件下载」。

坑：
- **text 字段塞 markdown 链接会读回 None**：`[标题](https://my.feishu.cn/wiki/<token>)` 写进 `润色正文` 后读回为空（接口仍回 `ok:true`），改纯 URL 立刻落位；markdown 链接只适合本来就是长文的列。
- **父节点是多维表格时，文档不在表格页可见**：目标 wiki 节点的 `resource_type` 是 bitable，docx 挂在它下面只能从左侧 wiki 目录点进去，交付时说明一句，别让用户以为没建成。
- **`wiki +node-list` 对 bitable 父节点恒返 `children: 0`**（不是没建成）：验证子文档是否挂对，用 `wiki +node-get --node-token <新节点>` 看 `parent_node_token` 是否等于目标 bitable 节点。`+node-list` 还必须带 `--space-id`，不然只报 `required flag(s) "space-id" not set`。
- **表里要能从记录跳到文档**：建一个 `物料文档`（text，包 URL 纯文本）列并把 wiki 链接回填（`fldy8z10Xu`，2026-10 新建）。写完马上 `+record-list` 读回；**读回时注意写后立刻列出可能拿到空值**——batch-update 返回 `ok:true` 后紧跟 list 偶发旧快照，重列一次再判。
- **文档放「可复制去发的成品」**：封面文案（含备选）→ 最终标题 → 正文成稿 → 备选标题（带公式编号）→ 备选开头 → 发布前事实自查（源研究 DOI、原文专家口径）。正文里仍不写出处，出处只进文末自查节。

## dbs 工具箱配合方式

- **用户点名单条「帮我补封标文案和正文」时的交付清单**：①6 条标题候选（每条标公式编号）＋Top3＋终选建议 ②封面 3 选（数字锚/纯数字/对仗各一，≤20 字）③正文成稿（本表房式，术语一句白话＋一个比喻）④3 条备选开头 ⑤五维自检表。用户点头后再落三列（`封面建议文案`／`图文建议标题`／`DS建议正文`），并主动问「润色正文」列要不要跑。
- **用户问「这篇论文有什么值得挖掘的观点/选题方向」时的交付形状**：①直接可用的观点，每条带硬数字与原文边界（作者自述的 limitation 一并写）②按受众分档的选题表（角度｜≤20 字标题示例｜形态｜证据锚点｜为什么有流量）③**选题链**——论文的参考文献就是现成的选题库，一稿可拆多期，并给出系列名与串联顺序④必须避开的误读（相关≠因果、指标本身有争议、经费数据是美国口径）⑤结尾落到 SciLink 的顺滑切口（先做认知、再落工具），但不靠「AI 做不到」立论。不要把论文摘要复述一遍当答案。
- 主 `dbs-content`：形式匹配（资讯数据类 →「图文大字报＋短视频」组合）＋五维自检（文字洁癖/封面标题/表达效率/认知落差）- 辅 `dbs-xhs-title`：从 75 公式里挑一条生成 ≤20 字标题，并记住公式编号便于复盘
- 注意：dbs-content 原则是「不代笔」；用户要求直接产出卡片时，把它的框架当自检清单用，正文仍按上表房式写

## 踩过的坑

1. **`--json @file` 路径有白名单**：只允许当前工作目录、`/tmp`、`~/files`。写到 `~/.hermes/cache/scratch/` 会报 `outside the built-in allowlist` → 先 cp 到 `/tmp` 再传。同一白名单也管 `docs +update --content @file`（报 `--content: invalid file path … outside the built-in allowlist`）；稿子在库外目录时不必搬文件，直接 `cat 稿.md | lark-cli docs +update … --content -` 走 stdin。
2. `--format ndjson --output` 时 stdout 是 manifest 不是 `{ok,data}` 信封；读数据直接读 ndjson 文件。
3. `--field-id` 必须传字段 ID；`+field-list` 里 select 字段是多值（list），本地处理前先归一化。返回结构是 `data.fields[]`，键名 `id`/`name`，单选选项在 `[].options[].name`——按 `field_id`/`field_name` 解析会整列打印 None，白跑一轮。
4. 验收：用「总行数 ＝ 老行数 ＋ 新增数」＋逐条比对 `内容标题/建议发布日期/来源链接/正文长度`。
5. 附件只留**文字占位禁止**：P2／P3 必须自己截图上填（配方见上节）；`封面图`、`封面图（带文案）`仍属出图环节，不在本流程产出，交付时说明。
6. 源表 MedHOT 摘要有压缩失真（例：BCG 那条摘要写「糖尿病患者」，原文是长病程 1 型糖尿病）→ 一律以原文为准，正文里把人群写准。
7. 源表同一条新闻可能被中文/英文两次收录（如 pritelivir 有两条：Medscape 版与「旭化成旗下」版）→ 按主题去重，只留信息最全的一条。
8. **隐藏广告的 CSS 别用宽泛选择器**：`[class*=paywall]`、`[class*=sticky]`、`[class*=article-]` 会把正文容器本身一起删掉，截图只剩标题；`header` / `footer` 元素选择器也危险——论文页的标题＋作者就在 `<header class="c-article-header">` 里，连它一起隐藏后 P2 只剩 Abstract，用户会以为截错了。只黑名单明确的广告/弹窗/导航 class，删完必须看一次截图。
9. **正文在内部滚动容器里的站（MedPage 一类）**：`document.body.scrollHeight ≈ 视口高`，`scrollIntoView` 没用、全页截图也只有一屏。先把所有 `scrollHeight > clientHeight + 100` 且 overflow 为 hidden/auto/scroll 的容器改成 `overflow:visible; height:auto; max-height:none`，页面才会展开。
10. **高亮定位用 DOM 不用像素**：正文里本来就有淡黄提示框（Key Points 类），按“黄色像素行”找位置会命中它，P3 裁出来和 P2 一模一样。改成取 `mark.hlmark` 的 `getBoundingClientRect().top + scrollY`，像素检测只当兜底。
11. **camofox 截图是 GET**：`/tabs/{id}/screenshot?userId=<uid>`（POST 会 404），加 `&fullPage=true` 才是全页；视口用 `POST /tabs/{id}/viewport {width,height}`，高度上限约 2400（6000 直接 400）。
12. **DOI 验证走 Crossref API 而不是 doi.org**：`https://api.crossref.org/works/<DOI>` 直接返回标题/期刊/日期，可机器比对；`doi.org` 与出版社页常回 403。Crossref 会 429，串行调用间隔 ≥1.2s，别并发打。
13. **权威源打不开时不要放弃这条，也不要编**：改用手上能打开的二手报道（行业媒体/转载），正文和汇报里写清「原文链接不可访问或已 404」＋二手来源；代表链接 404、或各媒体报道数字互相矛盾的选题直接剔除并入汇报。
14. **会议摘要/监管新闻常常没有 DOI，但会议季必须先查再下结论**：重磅 LBA 多数同期上 NEJM/Lancet/Lancet Oncology，会议摘要本身也常进 Annals of Oncology 补编带 DOI（`10.1016/j.annonc.<年>.<月>.xxxx`）。查法是 Crossref 加 `query.container-title=<刊名>` 逐刊搜试验名（只写试验名会返回一堆无关论文），配方见技能 `scilink-topic` 的「会议季专线」一节。查不到才留空并写清「会议报告/监管文件」；不拿新闻报道本身的 DOI 充数。
15. **datetime 单元格拒收解释文字**：往 `原文发布日期` 写「原文页未标注发布日期」会整批 `800010403 invalid_request`（batch 全失败）。日期只能 `YYYY-MM-DD HH:MM`；取不到的那条就**在 payload 里直接不写 `fldxUgwRLN` 这个键**（同批其他条照常写，不会失败），原因写进 DOI 单元格与汇报。
16. **`+record-batch-update` 的 JSON 形状是 map 不是数组**：`{"update_records":{"recXXX":{fldId:value}}}`；而 create 是 `{"create_records":[{...}]}`。两者不通用，写错就整批失败。
17. **一次堆 17 条会撞迭代上限**：研究/截图/文案都做完却来不及落库——按上文「5-6 条一组走完全流程并立即写表」，已入库的才算交付。
18. **模型压缩长文时会自己编 DOI**：实测把 8 篇论文的长稿压到 1000 字，模型把源文的 `10.1126/science.1072068` 写成 `science.1073768`。光写「不得改写 DOI」挡不住——必须把源 DOI 列表原样塞进提示词，落库前用正则抽输出 DOI 与源列表比对，不匹配就重跑。
19. **用户说「补齐 Kimi 润色」时要全表查空**：先数一遍 `Kimi润色正文` 为空的记录一并补掉；只补被点名的那批，表里会长期挂着空列，下次还得返工。
20. **云文档正文并入前必须剥脚手架**：`docs +fetch` 给的是编辑稿，含 `<title>` 标签、重复 H1、「小红书标题（…）/Top 3 推荐/备选标题」整套选标题段落；只保留 `正文（…）` 之后的部分，否则 DS 列里会混进一堆标题候选。
21. **DS 列能超 1000 字，Kimi 列不能**：合并长文档时 DS 保留全文；润色稿要压到 ≤1000 字，靠「按时间轴列 6-8 个节点＋限定 DOI 数量」的结构要求才压得下来，只说「压缩到 1000 字」模型会反复超到 1200-2600 字。
22. **生成完立即程序化数字数**：批产 38 条时实测 11 条 DS、4 条 Kimi 超标（最长 1227/1123）。流水线里加一道 `len()` 校验，超限的按「只删冗余词句、事实数字 DOI 结构全保留」再压一轮，压完复检到 0 条超限才入库。
23. **DOI 优先从 `来源链接` 推导，别从正文抓第一个 DOI**：`nature.com/articles/<code>` → `10.1038/<code>`；NEJM/Lancet/doi.org 的 URL 里直接含 DOI；medRxiv 去掉尾部 `v1`。正文里常引用一堆历史文献，取第一个 DOI 会抓错（诺奖那条会抓到 1991 年那篇）。
24. **批量改一列后必须读回，且别用 `| head` 截断响应**：`+record-batch-update` 返回 `ok:true` 才生效；用 `| head -5` 看响应会吞掉错误分支，出现「以为写了、读回没变」的假象。改完立刻 `+record-list` 读回比对目标字段。
25. **批量写表前先查一遍死链与猜测链接**：从数据库/聚合站拿到的 `url` 里有相当比例已 404 或从未存在（FDA 新闻稿、会议页）。逐条 `curl -sIL -o /dev/null -w '%{http_code}'`，404 的重新搜官方原文；实在找不到就用聚合站的 story 页兜底，并在 DOI 单元格写清「原文 404／反爬，暂用 X 页」。
26. **`+record-list --output` 遇到同名文件直接失败**：报 `failed_precondition: output file already exists`，但 stdout 仍打印旧 manifest，很容易把昨天的 `records_count` 当成今天的结果。每次换新文件名或加 `--overwrite`，并核对 manifest 的 `rev`/`records_count` 与「老行数＋新增数」是否对得上。
27. **camofox 复用同一个 tab 连续 navigate 会突然回 400**：不是 URL 的问题，是 tab 失效；每条 URL 新建 tab（或导航失败立刻重建）即可恢复。`activeTabs` 涨到两位数后服务开始报 400/500，`launchctl kickstart -k gui/$(id -u)/com.mednews.camofox` 或 pkill 后重新起 `~/.local/bin/camofox-browser` 能清干净。
28. **JAMA 与 Science 的 Cloudflare 要 30-60 秒轮询**：直接取会拿到 `Just a moment...`，每 5 秒重试、最多 60-70 秒才放行。JAMA 页面放行后 `meta[name=citation_publication_date]`（`2026/10/20`）和 `meta[name=citation_doi]` 同时给出发布日期与 DOI，比抓正文日期行可靠；且**页面 h1 常与 RSS 标题不同**（RSS「ACOG强化…推荐」vs 页面「Remove the Fallopian Tubes If the Opportunity Arises…」），标题一律取页面 h1。Science.org 即使放行也没有日期 meta（cookie 墙），取不到日期就别硬编，换同题可核验的源。
29. **`docs +update --command overwrite` 常回 `partial_success` + `degrade_code=1011`（"Instruction produced no document changes"），但正文和图片其实全写进去了**：不要据此重跑覆盖（会白等一轮），统一用 `docs +fetch --doc-format markdown` 读回，检查 `# 各节标题` 齐不齐、`feishu.cn/file/` 有没有出现（图片是否落地）来判定成败。
30. **图要并排就必须走 XML 的 `<grid><column>`，markdown 做不出分栏**：markdown 只能把图纵向堆叠（`![封面](@./x.png)` 那条只适合单图文档）。做法是 `--doc-format xml` ＋ `<grid><column width-ratio="0.25"><img path="@./x.png" caption="…"/></column>…</grid>`，`width-ratio` 之和＝1，CWD 必须是图片所在目录；结构模板见「物料文档：每条记录一篇」。
31. **找支撑文献用 Crossref `query.bibliographic` 而不是猜 DOI**：`api.crossref.org/works?query.bibliographic=<标题>&filter=from-pub-date:...` 一次就能拿到「原文题＋DOI＋月份」，JAMA/JMIR/medRxiv 都覆盖；medRxiv 新前缀是 `10.64898`（不是 `10.1101`），`/works/<DOI>` 能直接回日期。原文确实没有论文的（学会指南、监管公告、厂商口径、教程页）就写 `无（原因）`，别拿新闻自身 DOI 充数。
32. **B 路「每日医讯」库的表名是 `content`，不是 `news`**：`~/Documents/Hermes/数据/医学素材库.db` 只有 `content`＋`summary_daily` 两张表；列是 `标题/链接/发布时间/来源/平台/主分类/摘要`，`发布时间` 是 `YYYY-MM-DD` 文本（可直接字符串比较圈窗口，但库里有未来日期的预告稿，取完先看一眼 `max(发布时间)`）。`平台 in ('国外源','中文源')` 里有大量 Lancet Correspondence/Obituary/Department of Error、NPR 生活方式稿、财经门户稿，**取下限是「全量取出」，不是「全量入库」**——按受众（医生/科研者/医学生）筛。
33. **核验脚本先行，人工只处理例外**：几十条候选逐条开浏览器核时绝对跑不完。先用一个脚本串行跑 curl 状态码+页面 title/datePublished 与 Crossref 题名，落 JSON；再把 403/无日期/DOI 可疑的挑出来单独处理。被挡的站优先 `web_extract`（见 `references/source-and-doi-verification.md` 1.1），最后才 camofox；对 camofox 也 500 的站（Lancet、gastrojournal）先换新 tab 重试一次（放行后能读 `citation_online_date`／`citation_date`，判据见 reference 1.3），仍不行才接受「日期留空＋题名靠 Crossref 核」，不要为一条记录重试十几轮。
34. **DOI 列里的英文题名一字不改**：Crossref `title[0]` 是什么写什么，副标题、地名、试验代号全带上。中文译名可以概括，引文里的英文题名不能自己补「及相关岗位」「等研究」这类概括词——用户会拿它去搜原文，多一个字就搜不到。
35. **存量老记录要顺手清洗标题与链接**：翻旧记录时会发现标题是早期写的缩写版、`来源链接` 里还残留 `[url](url)` 的 markdown 包装（text 列塞 markdown 读回可能变 None，也是排期表回填时的老坑）。批量维护时一并处理：标题取页面 `h1` 全文（去掉 `<title>` 尾部的「-站名」，不缩写、不改写、不加情绪词），链接只留纯 URL；改完 `+record-list` 读回抽查几条。用户口径始终是「标题用原稿」——缩写标题看着省事，但对不上原文就搜不到。
36. **建 wiki 节点时的 `--title` 与 markdown 里的 `# 标题` 会分叉**：先 `wiki +node-create --title A` 再 `docs +update` 写入含 `# B` 的 markdown，结果是节点标题 A、文档标题 B，用户一眼看出不一致。收口用 `lark-cli drive +update-title --url <wiki URL> --type wiki --title '<最终标题>'`——它把节点与文档标题一起改；更省事的做法是建节点前就把 markdown 的 H1 定成与 `--title` 逐字相同。
