# 医学资讯信源地图（脱离 MedHOT / 每日医讯的独立抓取方案）

> 2026-10 实测。本文回答一件事：**不依赖 MedHOT 和每日医讯这两个中间层，能不能把它们的消息自己抓回来？** 结论：能，而且是同源——它们本身就是聚合器，源清单可直接提取。

## 1. 断源策略：抄它们的源，不抄它们的中间层

| 管道 | 本质 | 我们的替代 |
|---|---|---|
| MedHOT（本地 Postgres `medhot`） | 59 个源（28 个 EuropePMC ISSN 查询 + 31 个 RSS），合并同一事件的多个报道成 story，AI 打分/选精 | 直接打 EuropePMC + RSS（同源），自己去重合并 |
| 每日医讯（本地 `医学素材库.db`） | RSS/新闻站 + 社媒（B站、丁香园）+ LLM 打标 | RSS 直抓 + 中文源页面抓取 |

**关键情报在 `sources` 表**（`config->>'feedUrl'` 存 RSS 地址，EPMC 源存带 ISSN 的完整查询 URL）。这个表就是现成配方，已固化进 `scripts/fetch_all_sources.py`。

## 2. 源清单（按可用性分三档）

> 2026-10 更新：已补入 6 个中文官方源（见下「中文源」），至此**英文线 + 中文线都不再依赖 MedHOT / 每日医讯**。

### A 档 · 直连即得（实测 HTTP 200，21/24）

**期刊正文（EuropePMC，按 ISSN，可扩）**：NEJM / JAMA 系列（4）/ Lancet 系列（5）/ Nature 系列（4）/ Cell / Science / BMJ / Annals / Circulation / JACC / EHJ / Diabetes Care / Blood / JCO / Brain / Gut / Gastroenterology / J Hepatol / CID / ICM / Critical Care / Anesthesiology / Radiology / Eur Urol / Pediatrics / PLOS Med / STTT / Chin Med J

查询模板（照抄可用）：
```
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ISSN:<issn>+AND+SRC:MED+AND+HAS_ABSTRACT:Y&format=json&pageSize=50&sort=FIRST_PDATE_D+desc&resultType=core
```
`HAS_ABSTRACT:Y` 很重要——不写会混进大量读者来信、更正、讣告。

**RSS（16 个）**：Nature / Nature Medicine / Nature Biotech / Nature Rev Cancer / NEJM / NEJM Evidence / Lancet / Lancet Oncology / Lancet ID / JAMA / Cell / Science / WHO / CDC / bioRxiv / medRxiv

> ⚠️ 2026-10-26 起 **bioRxiv / medRxiv 默认不抓**（用户决定：预印本无同行评议、太前沿，不适合医生向公开内容）。源配置移到 `PREPRINT_FEEDS`，只有 `--with-preprint` 才启用。

### B 档 · 能抓但偶发失败（重试即可）
- `medRxiv` RSS：偶发 408 超时，重试 1-2 次
- `Science`：RSS 给的是新闻，论文走 EuropePMC
- `ScienceDaily`：一次给 60 条，噪音多，适合筛"反常识/机制"选题

### C 档 · 必须浏览器兜底（3 个）
| 源 | 症状 | 兜底 |
|---|---|---|
| Medscape | RSS 403 Cloudflare | camofox 打开文章页取 title/date；RSS 走 `https://www.medscape.com/cx/rssfeeds/2700.xml` 在浏览器里也常能读 |
| FDA 新闻稿 | 原 RSS 路径 404 | 改抓 `https://www.fda.gov/news-events/fda-newsroom`（camofox），或 openFDA API |
| Guardian Health | 国内直连超时 000 | 需要时走代理；价值低，可直接不抓 |

### 中文源（已接入脚本，`--only cn`）

2026-10 实测可用并已固化的 6 个中文官方源：

| 源 | URL | 接入方式 | 发帖节奏 |
|---|---|---|---|
| NMPA 药品公告 | `nmpa.gov.cn/yaopin/ypggtg/index.html` | camofox（curl 412） | 几天一条，含说明书修订、非处方药转换、口岸公告 |
| NMPA 药品动态 | `nmpa.gov.cn/yaopin/ypjgdt/index.html` | camofox（curl 412） | **1-3 天一条，含新药批准上市（最高价值）** |
| 卫健委政策法规 | `nhc.gov.cn/wjw/zcfg/list.shtml` | camofox | 周级，政策原文+解读混排 |
| 卫健委工作通知 | `nhc.gov.cn/wjw/gztz/list.shtml` | camofox | 半月级，规培/绩效监测/专项活动 |
| 卫健委征求意见 | `nhc.gov.cn/wjw/zqyj/list.shtml` | camofox | 月级，含生物医学新技术转化审批规范类 |
| 国自然通知公告 | `nsfc.gov.cn/p1/2828/2831/tzgg11.html` | **curl 直连 200** | 季度级，集中在中报期 |

已排除的候选：`nhc.gov.cn/wjw/zcjd/list.shtml`（政策解读）与政策法规列表内容 100% 重叠，删；卫健委首页（新华社时政通稿占满，无选题价值），删；`nsfc.gov.cn/publish/portal0/tab442/` 旧路径已 404。

其他中文媒体（科学网、梅斯、丁香园、B站）仍是**页面抓取**，未接入脚本——价值低于官方源，需要时单次抓。

> 模板提示：两类列表结构都要兼容——①`<li><a title>¥</a><span>日期</span></li>`（NMPA/卫健委）；②`<a href><li>…<div class="date">日期</div></li></a>`（国自然）。脚本 `parse_cn()` 按「日期位置往前找最近的 `<a>`」统一处理，不用写两套。

## 3. 覆盖验证（实测 2026-10-25，MedHOT 近 3 天 15 个 story 抽 11 条）

| MedHOT 的 story | 直连能否抓回 |
|---|---|
| NeoCOAST-2（Nature）、Moderna mRNA（Nature 新闻）、Shamonda（Nature 新闻） | ✅ Nature RSS |
| relatlimab 5 年、mKRAS 疫苗、CAR-T 队列、visugromab | ✅ Nature Medicine RSS |
| Anbenitamab（NEJM） | ✅ NEJM RSS |
| COMPANION-002（JCO）、PBC 指南（Gastroenterology） | ✅ EuropePMC 按 ISSN 补回 |
| Bundibugyo 预印本（bioRxiv） | ⚠️ 可抓，但 2026-10-26 起主动不收预印本；如必须做前沿题材再加 `--with-preprint` |
| APRIL/BAFF（Medscape）、登革热（MedPage） | ⚠️ 新闻类只走 camofox；同一事件基本都有期刊原文可用 EuropePMC 抓到 |

**结论：期刊类 100% 可复现；新闻类靠 RSS 约 8 成，剩余靠 camofox。**

## 4. 日期陷阱（最容易翻车的一处）

EuropePMC 的 `firstPublicationDate` / `electronicPublicationDate` 对 **Lancet 系、部分 Elsevier 刊** 返回的是**未来期次日**（实测出现过 2027-09、2027-12）。

处理：`pub > 今天` 一律不当发布日期 —— 脚本清空 `published`、原值落 `issue_date` 字段待人工核。**入库前日期一律以页面自带为准**（见 SKILL.md 日期口径）。已踩过的具体案例：PBC 指南页面只给 `citation_date=2026/11/01`（期次），Mitapivat 要 camofox 读 Lancet 页 `citation_date=2026/10/24`。

RSS 的时间戳通常可靠（`pubDate`），但 bioRxiv/medRxiv 给的是**采集日**，原文日期要进页面看。

## 5. 与 MedHOT 相比丢掉了什么

| 能力 | MedHOT 有 | 我们自建 |
|---|---|---|
| 同一事件多源合并成 story | ✅ `story_signals` 关联 | ❌ 需自己做标题相似度聚类（阈值 0.28 可用，见 medhot-full-inventory.md） |
| AI 打分 / 精选 | ✅ `analyses.score/selected` | ❌ 我们自己按话题度三分法打分 |
| 摘要写成中文 | ✅ `stories.digest` | ❌ 需自己写（其实写文案时本来就要重写） |
| 可定制（加刊、按科室、按系列） | ❌ 改不了 | ✅ 改一个 ISSN 字典就多一本刊 |

所以自建的真实收益是**可定制**：想补影像就加 Radiology，想补重症就加 Critical Care/ICM，不用等 MedHOT 的源表更新。

## 6. 标准操作顺序

```bash
# 1) 拉一周候选（含期刊 + RSS），按科室过滤
python3 <skill>/scripts/fetch_all_sources.py --days 7 --dept radio --out /tmp/cand.json

# 2) 人工/模型筛选题（痛点相关 + 是否临床可改变决策）

# 3) 逐条核：链接标题比对 → 页面日期 → DOI Crossref 验证
#    （C 档三个源用 camofox；日期用 meta 的 citation_date/datePublished）

# 4) 写表：6 列 + 系列字段，分批 5-6 条，每批读回
```

## 7. 科室覆盖现状与缺口（2026-10-25 统计）

| 科室 | 表内条数 | 建议补源 |
|---|---|---|
| 肿瘤 | 27（偏多） | —— 应主动限流 |
| 消化 | 12 | Gut / Gastroenterology / J Hepatol（已接） |
| 心血管 | 7 | EHJ / JACC / Circulation（已接）；可加 Eur Heart J Cardiovasc Imaging |
| 呼吸 | 3 | 已接 Lancet Resp Med？**未接，建议加 ISSN 2213-2600** |
| 精神/神经 | 6 | Lancet Neurology 已接；可加 JAMA Psychiatry 2168-622X |
| 影像 | 6 | Radiology 已接；可加 Eur Radiol、Radiology: AI |
| 肾/泌尿 | 5 | Eur Urol 已接；可加 JASN 1046-6673 |
| 儿科/妇产 | 5 | Pediatrics 已接；可加 BJOG 1470-0328 |
| 急诊/重症 | 2 | Critical Care / ICM 已接；可加 Ann Emerg Med 0196-0644 |
| 麻醉/疼痛 | 3 | Anesthesiology 已接；可加 BJA 0007-0912 |

**加刊只要在 `JOURNALS` 字典加一行 `显示名: ISSN`**，不用改其他代码。

## 8. 临床学习/参考站点 vs 资讯源（两类，不能混）

用户问「哪些网站对临床/医学生有价值、你收了没」时，先分类再回答，**不要把所有网站都算成“该抓”**：

| 类型 | 例子 | 是否入抓取 |
|---|---|---|
| **资讯型**（每天/每周出新内容，能产选题） | NMPA、卫健委、国自然、NEJM/Lancet RSS、MedPage、STAT、Retraction Watch、医脉通·指南、中华医学期刊网 | **该抓**（未收的要补） |
| **工具型**（随时查，不产出“新消息”） | UpToDate、BMJ Best Practice、DynaMed、MDCalc、AMBIS、Osmosis、Radiopaedia、LITFL、Pathology Outlines、PubMed/PMC 检索页、ClinicalTrials.gov | **不抓**，但学习/查证时优先 |

已核过、**该收但尚未收录**的 6 个（按价值排序）：医脉通·指南（`guide.medlive.cn`，评级医生的刚需、页面抓取）、中华医学期刊网（`yiigle.com`，可能有付费墙）、CDE 药审中心（`cde.org.cn`，返回 202 需 JS，能提前 3-12 个月看到“这药要来了”）、FDA 药品审批（`fda.gov`，camofox 可绕）、EMA（`ema.europa.eu`，RSS 可用、常早于 FDA）、中华医学会会议/征文。

完整 46 条清单（含每个站一句话用途、✅已收录/🟡抓不到/⬜未收录）已存入选题库 Base 内的 docx 块「**常用信源（用于人工筛选）**」(`docx_token` `Tqeid2vHlo4jmXxhKb2cmpXZntk`)；再要更新它时用 `base +base-block-list` 拿 token，再 `docs +update --command overwrite --doc-format markdown`。

链接交付前必须批量探活（并发 10 路、单条 20s）：`404` 换路径、`000` 换站——实测 `calgaryguide.ucalgary.ca` 已迁到 `calgaryguide.ca`，`ECG Wave-Maven` 域名彻底无响应要换 `ECGpedia`。`401/403` 是 WAF 拦脚本，浏览器正常，照发并注明。

## 9. 「抓 0 条」不等于空源（踩过的错判）

2026-10-25 实测：`Annals of Emergency Medicine`（ISSN 0196-0644）在 `--days 10` 窗口下拉回 **0 条**，我一度判定它是空源，要求下一轮换刊。复查发现**它收了 7211 篇、最新一条是 2026-10-14**——只是发文節奏慢，刚好卡在 10-15 的窗口边界外。

判空流程（每次多 10 秒，能省掉一次错判）：
```bash
# 不限窗口，看这本刊最新一篇是哪天
curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ISSN:0196-0644+AND+SRC:MED+AND+HAS_ABSTRACT:Y&format=json&pageSize=3&sort=FIRST_PDATE_D+desc&resultType=lite"
```
- 最新条目 >> 窗口 → 真空源/停刊，才换刊；
- 最新条目刚在窗口外 → 把 `--days` 调大（急诊、麻醉、肾脏类期刊發文慢，建议 10-14 天）。

急诊/重症线实测（2026-10-25 最新条目）：Ann Emerg Med 10-14；Resuscitation 10-23；Crit Care Med 10-23；Acad Emerg Med 10-01；Emerg Med J 09-23；Ann Intensive Care 10-09。
