---
name: scilink-medical-topic-scout
description: Use when 要为 SciLink 账号挖医学选题（医生/医学生/临床科研者受众）：多源直抓→选题判定→链接/日期/DOI 三核→入飞书物料库。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [medical-content, topic-scouting, europepmc, rss, feishu, scilink]
    related_skills: [feishu-content-material-library, dbs-content, dbs-xhs-title]
---

# SciLink 医学选题侦察（多源直抓 → 选题 → 核验 → 入库）

## When to Use

- 给 SciLink 官号 / 个人号矩阵找医学资讯选题，受众＝**医生 / 医学生 / 临床科研者**
- 需要**不依赖 MedHOT、每日医讯**这类中间层，自己把当天/近一周的医学新消息抓全
- 批量补飞书「内容物料库」的 6 个基础字段（标题/话题度/分类/日期/链接/DOI）
- 需要按科室（心内/呼吸/重症/麻醉/影像/肿瘤…）定向找料

不适用：患者科普、纯美国医保/诉讼/人事、无数据转述。

## 一、抓：三条路，优先级从高到低

| 路径 | 用什么 | 适用 |
|---|---|---|
| **A 期刊直抓（主力）** | `scripts/fetch_all_sources.py`（EuropePMC 按 ISSN，54 本刊） | 论文、指南、RCT、队列——质量最高、DOI 天然可核 |
| **B RSS 直抓** | 同脚本（24 个源：Nature/NEJM/Lancet/JAMA/Cell/Science/WHO/CDC/预印本/行业媒体） | 新闻、快报、机构公告 |
| **C 浏览器兜底** | camofox（`POST /tabs` → `/navigate` → `/evaluate`） | Medscape（403）、FDA 新闻稿（RSS 404）、文章页取页面日期 |

```bash
# 日常全量（近 3 天）
python3 scripts/fetch_all_sources.py --days 3 --out /tmp/cand.json

# 按科室定向（cardio/resp/icu/anes/radio/onc）
python3 scripts/fetch_all_sources.py --days 10 --dept icu --out /tmp/icu.json

# 只走期刊，最快
python3 scripts/fetch_all_sources.py --days 7 --only jr
```

输出统一 JSON：`{source, kind, title, doi, url, published, pub_basis, issue_date, abstract}`。
源清单、可达性三档、覆盖验证见 `references/medical-news-source-map.md`。
**加刊只需在脚本 `JOURNALS` 字典加一行 `显示名: ISSN`。**

## 二、筛：什么值得做

受众三条线，一条只挂一个主视角：
① 要发论文的医学生/规培生　② 靠论文评职称、不太懂统计的临床医生　③ 懂科研的临床科研工作者

优先级：
1. **能改变临床决策**的（新药获批、指南更新、诊断阈值被挑战）
2. **有硬数据的**队列/RCT（样本量＋HR/OR/AUC/灵敏度）
3. **科研方法与工具**（真实世界数据、生信、AI 辅助科研）→ ①②最爱
4. **反常识/阴性结果**（试验未达终点、机制意外）→ 互动最高，**别只收阳性**
5. **科室分布要均衡**：肿瘤类天然过剩（期刊与会议都偏肿瘤），必须主动给心血管/呼吸/急诊重症/麻醉/影像/肾/妇产配额度

排除：地方性政策（市/县级申报通知）、代写代投广告、只讲 AI 多强不讲边界的软文。

**话题度**＝目标受众痛点相关度(0-40) + 时效性(0-30) + 可讨论度(0-30)，整数。打分理由只写汇报，不进表。

**内容分类**只能用固定选项（新药获批/临床试验数据/指南共识更新/观察性真实世界/预印本早期研究/AI与数字医疗/公共卫生与疫情/科学奖项与基础研究/科研方法与行业分析/观点与评论），高风险留给涉及具体药物疗效与用药推荐的。

## 三、核：三件事，一件都不能猜

### 1. 链接要对得上标题
每条都打开比对**标题**，不能只看域名。聚合站/数据库里的 url 有相当比例 404 或指向别的文章。404 就换能打开的二手报道并写明。

### 2. 日期只能取页面自带的
写入格式 `YYYY-MM-DD HH:MM`（Asia/Shanghai），**用页面印刷的日历日 + 09:00**，不要拿美东时间换算（上午的稿会跳日）。
取不到就留空，**禁止**用抓取日/建议日/推断值补。

⚠️ **三个已踩的坑**：
- **EuropePMC 的日期可能是未来期次**：Lancet 系、部分 Elsevier 刊会把"期次日期"当发布日期返回（实测出现过 2027-09）。脚本已把超今天的值清空并落到 `issue_date`。
- **web_extract 摘要行里的 `Published:` 不可信**：它会把期次月份当日期（实测 Lancet Resp Med 给 2026-10-01，真实 2026-10-21）。
- **出版社页面只需看 meta**：`citation_online_date` / `datePublished` 才是真的；Elsevier/Lancet 站被 Cloudflare 挡时用 camofox 读这两个字段。

### 3. DOI 必须 Crossref 验
```
https://api.crossref.org/works/<DOI>   # 返回 title 与新闻主题对得上才算过；串行、间隔 ≥1.2s（会 429）
```
- **从 URL 推导优于从正文抓**：`nature.com/articles/<code>` → `10.1038/<code>`；NEJM/doi.org 的 URL 直接含 DOI；medRxiv/bioRxiv 去尾部 `v1`。正文里常引一堆历史文献，抓第一个 DOI 一定抓错。
- 填表格式＝可直接粘贴的引文：`<Crossref 返回的英文原题>. DOI: <10.xxxx/xxxxx>`
- 确实没有论文的（会议摘要、监管文件、政策、教程、吐槽）→ `<内容标题>. 无（原因）`，**不拿新闻报道自身的 DOI 充数**。

## 四、写：6 列 + 分批 + 读回

飞书「内容物料库」只写 6 列（`内容标题/话题度/内容分类/原文发布日期/来源链接/DOI`），其余列留给后续步骤：

```bash
# 差集（幂等优先，已入库绝不重复录）
lark-cli base +record-list --base-token <t> --table-id <t> --limit 500 --format ndjson --output /tmp/existing.ndjson --overwrite --as user
# 分批创建（create 是数组）
lark-cli base +record-batch-create --base-token <t> --table-id <t> --json @/tmp/payload.json --as user
# 读回验收（别用 head 截断）
lark-cli base +record-list --base-token <t> --table-id <t> --limit 500 --format ndjson --output /tmp/check.ndjson --overwrite --as user
```

- **每 5-6 条一组走完全流程并立即写表**，不要攒到最后——会话有迭代上限，已入库的才算交付。
- payload 形状：create 是 `{"create_records":[{fldId:value}]}`（数组），update 是 `{"update_records":{"recX":{fldId:value}}}`（map），两者不通用。
- `--json @file` 只允许当前目录、`/tmp`、`~/files`。
- **datetime 列拒收文字**：塞"原文未标注日期"会整批 `800010403`，日期原因只能写汇报或 DOI 列。
- 写完立刻读回，逐条核 6 列是否落位、分类是否在合法选项内。

## 五、判空与降级规则

- **抓 0 条 ≠ 空源**：先查该刊最新一篇日期（不限窗口），远早于窗口才换刊，只是刚落到窗口外就放大 `--days`。急诊/麻醉/肾脏类期刊发文慢，建议 10-14 天。
- 权威源打不开：改用手上能打开的行业媒体/转载，汇报写清"原文 404/不可访问"＋实际用的链接。
- 代表链接 404 且各媒体数字互相矛盾的选题：**直接剔除**，不要硬凑。
- 作者/会议摘要/监管文件没有 DOI 属正常，写"无（原因）"即可。

## 六、交付汇报（用户要求逐条列全）

每条给：`内容标题 | 原文日期 | 分类 | 话题度（含三分项理由）| 主视角 | DOI 验证结果 | 链接是否对得上 | 留空项及原因`。
另附：本轮新增条数、表内总条数、科室分布变化、剔除项与理由。

## 七、常见坑（都实际踩过）

1. Nature/NEJM/JAMA/Lancet 用 curl 直接用浏览器 UA 可过；Medscape/MedPage/gastrojournal 会 403/Cloudflare → web_extract 或 camofox。
2. camofox 复用同一 tab 连续 navigate 会突然 400/500——每条 URL 新建 tab；Lancet 首次 nav 常 500，重试一次即成功。
3. `record-list --output` 同名文件会 `failed_precondition`，每次换名或加 `--overwrite`，否则会把旧 manifest 当新结果。
4. 同一新闻中英文两次收录（STAT/Medscape/Nature 各一版）→ 按主题只留信息最全的一条。
5. 中文 SEO 站（选刊指南站、软件测评软文、知乎/CSDN）日期缺、正文空，优先官方机构页与期刊正式文章。
6. 摘要里的数字不可信，正文口径以原文为准；"相关≠因果"这类限定词必须保留。

## 相关

- 卡片文案与 P2/P3 截图：`feishu-content-material-library`
- 选题标题公式：`dbs-xhs-title`；开头钩子：`dbs-hook`
- 反爬浏览器：`camofox-browser-api`
