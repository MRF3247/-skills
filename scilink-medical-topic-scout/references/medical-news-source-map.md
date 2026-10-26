# 医学资讯信源地图（脱离 MedHOT / 每日医讯的独立抓取方案）

> 2026-10 实测。本文回答一件事：**不依赖 MedHOT 和每日医讯这两个中间层，能不能把它们的消息自己抓回来？** 结论：能，而且是同源——它们本身就是聚合器，源清单可直接提取。

## 1. 断源策略：抄它们的源，不抄它们的中间层

| 管道 | 本质 | 我们的替代 |
|---|---|---|
| MedHOT（本地 Postgres `medhot`） | 59 个源（28 个 EuropePMC ISSN 查询 + 31 个 RSS），合并同一事件的多个报道成 story，AI 打分/选精 | 直接打 EuropePMC + RSS（同源），自己去重合并 |
| 每日医讯（本地 `医学素材库.db`） | RSS/新闻站 + 社媒（B站、丁香园）+ LLM 打标 | RSS 直抓 + 中文源页面抓取 |

**关键情报在 `sources` 表**（`config->>'feedUrl'` 存 RSS 地址，EPMC 源存带 ISSN 的完整查询 URL）。这个表就是现成配方，已固化进 `scripts/fetch_all_sources.py`。

## 2. 源清单（按可用性分三档）

### A 档 · 直连即得（实测 HTTP 200，21/24）

**期刊正文（EuropePMC，按 ISSN，可扩）**：NEJM / JAMA 系列（4）/ Lancet 系列（5）/ Nature 系列（4）/ Cell / Science / BMJ / Annals / Circulation / JACC / EHJ / Diabetes Care / Blood / JCO / Brain / Gut / Gastroenterology / J Hepatol / CID / ICM / Critical Care / Anesthesiology / Radiology / Eur Urol / Pediatrics / PLOS Med / STTT / Chin Med J

查询模板（照抄可用）：
```
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ISSN:<issn>+AND+SRC:MED+AND+HAS_ABSTRACT:Y&format=json&pageSize=50&sort=FIRST_PDATE_D+desc&resultType=core
```
`HAS_ABSTRACT:Y` 很重要——不写会混进大量读者来信、更正、讣告。

**RSS（16 个）**：Nature / Nature Medicine / Nature Biotech / Nature Rev Cancer / NEJM / NEJM Evidence / Lancet / Lancet Oncology / Lancet ID / JAMA / Cell / Science / WHO / CDC / bioRxiv / medRxiv

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

### 中文源（每日医讯那条管道的补充）
科学网（news.sciencenet.cn）、梅斯医学（medsci.cn）、丁香园、B站博主——都是**页面抓取**，没有可用 RSS。medsci 文章页 `curl` 可直读标题+日期（实测 521KB 完整 HTML）。

## 3. 覆盖验证（实测 2026-10-25，MedHOT 近 3 天 15 个 story 抽 11 条）

| MedHOT 的 story | 直连能否抓回 |
|---|---|
| NeoCOAST-2（Nature）、Moderna mRNA（Nature 新闻）、Shamonda（Nature 新闻） | ✅ Nature RSS |
| relatlimab 5 年、mKRAS 疫苗、CAR-T 队列、visugromab | ✅ Nature Medicine RSS |
| Anbenitamab（NEJM） | ✅ NEJM RSS |
| COMPANION-002（JCO）、PBC 指南（Gastroenterology） | ✅ EuropePMC 按 ISSN 补回 |
| Bundibugyo 预印本（bioRxiv） | ✅ EuropePMC 标题搜 / bioRxiv RSS |
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

## 8. 「抓 0 条」不等于空源（踩过的错判）

2026-10-25 实测：`Annals of Emergency Medicine`（ISSN 0196-0644）在 `--days 10` 窗口下拉回 **0 条**，我一度判定它是空源，要求下一轮换刊。复查发现**它收了 7211 篇、最新一条是 2026-10-14**——只是发文節奏慢，刚好卡在 10-15 的窗口边界外。

判空流程（每次多 10 秒，能省掉一次错判）：
```bash
# 不限窗口，看这本刊最新一篇是哪天
curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=ISSN:0196-0644+AND+SRC:MED+AND+HAS_ABSTRACT:Y&format=json&pageSize=3&sort=FIRST_PDATE_D+desc&resultType=lite"
```
- 最新条目 >> 窗口 → 真空源/停刊，才换刊；
- 最新条目刚在窗口外 → 把 `--days` 调大（急诊、麻醉、肾脏类期刊發文慢，建议 10-14 天）。

急诊/重症线实测（2026-10-25 最新条目）：Ann Emerg Med 10-14；Resuscitation 10-23；Crit Care Med 10-23；Acad Emerg Med 10-01；Emerg Med J 09-23；Ann Intensive Care 10-09。
