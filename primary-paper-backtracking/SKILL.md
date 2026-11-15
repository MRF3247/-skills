---
name: primary-paper-backtracking
description: "Use when 从新闻/媒体条目回溯到原研究论文：定权威层级、核题录、拿免费全文与官方图、排出存档 PDF。"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [evidence, primary-source, pubmed, europepmc, jats, pdf, medical-content]
    related_skills: [medical-evidence-sourcing, chinese-social-copywriting, medhot-medical-news-site, paper-figure-extraction]
---

# 从新闻回溯到原论文（并把它存成可读 PDF）

## When to Use

- 用户丢来一条新闻/热点条目（含 MedHOT 站内条目、英文媒体稿），问「最权威的论文出处是哪个」
  「找一下这个新闻的原论文」「把这论文下载到 <目录>」
- 要把一条已发布的媒体稿从「转述」升级成「引原论文」（给审核方/团队一份可回查的一手信源）
- 需要把论文全文归档到本地/Obsidian（出版社 PDF 被付费墙或反爬挡住）

他要的是**能写进稿子的一手信源 + 一份能读的全文**，不是又一篇转述。

不适用：为某句台词配证据、从已有 PDF 裁图（→ `medical-evidence-sourcing`，用户自有技能，不要在本技能重复它的检索/取图配方）；
登记口径核实（→ `clinical-trial-registry-factcheck`）；把结果写成文案（→ `chinese-social-copywriting`）。

## 1. 先定权威层级（写文案只准引前两档）

| 档 | 载体 | 用途 |
|---|---|---|
| ① 原研究论文 | 期刊正式论文（优先开放获取） | **所有疗效/安全性数字的唯一出处**；引用格式按它写 |
| ② 会议首次报告 | 大会摘要（SABCS / ASCO…） | 讲「首次公布」；**只存在于报告里的亚组中位月数标这个载体**，别当成论文数据 |
| ③ 监管一手 | FDA/EMA 批准通知、说明书 | 获批日期、适应证边界、黑框警告、推荐剂量 |
| ④ 后续会议摘要 | 次年大会的亚组/安全性深度分析 | 深度稿补细节（引用前先确认，标注待核） |
| ⑤ 媒体转述 | Medscape / OncLive / AJMC / ASCO Post | 只作线索，**不能当唯一来源** |

- 配发社论/编辑部评论（如 JCO 的 Relevance 段）常直接给出「这件事该怎么定位」，深度稿值得引；
  开放获取论文页脚会列出关联社论的 PMID。
- 论文题录一次拿全（DOI / PMID / PMCID / 卷期页 / 全部作者 / 在线发表日）：
  ```bash
  curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=<PMID>&rettype=abstract&retmode=xml"
  ```
  → 解析 `<ArticleId IdType="pmc|doi">`、`<ArticleDate>`（在线发表日）、`<PubDate>`（印期）。
  PMID 本身先做 **DOI→PMID 单独映射**：`esearch?db=pubmed&term=<DOI>[DOI]`，
  **禁止从批量返回的顺序推断归属**（会把 A 的 PMID 挂到 B 上）。
- **Crossref 一次拿题录＋摘要**（最快，付费墙也回摘要）：`message.abstract` 是 JATS 片段，
  结论、人群口径、边界词都在里面——先跑这一条，够用就不必开浏览器：
  ```bash
  curl -s "https://api.crossref.org/works/<DOI>" | jq '{title:.message.title[0], journal:.message["container-title"][0], online:.message["published-online"]["date-parts"][0], authors:[.message.author[].family], abstract:.message.abstract}'
  ```
- **必须判「综述／原创」**：Crossref 的 `message.type` 对两者都只写 `journal-article`，
  真类型看 PubMed `<PublicationType>` 或出版社页顶部的栏目名（`State-of-the-Art Review` /
  `Review Article` / `Original Research` / `Comment`）。综述与观点稿里的「核心数据」全是别人的旧数据，
  引用时必须写成「该综述称…」，**不能当新研究报**——用户是按稿件价值判断选题的，类型判错整条选题定性就错。

## 2. 第一作者陷阱（媒体几乎全错）

媒体按**大会报告人**写（「Dr. X reported」），二次传播就把报告人当第一作者；
而期刊论文的署名顺序与会议摘要又常不同（实测同一研究：论文第一/通讯作者是 A，
末位作者才是大会报告人 B，而会议摘要以 B 打头）。

**署名一律以期刊论文为准**，并在回复里主动点出这个差异——用户会拿它核团队稿件。

## 3. 拿免费全文与官方图（出版社 PDF 被反爬时）

优先级（实测）：

1. **Europe PMC 全文 XML**（首选，curl 直取无阻）：
   `https://www.ebi.ac.uk/europepmc/webservices/rest/PMC<id>/fullTextXML`
2. PMC 文章页：**curl 会撞 reCAPTCHA**（拿回 HTML 不是 PDF），**浏览器可开**；
   先把 reCAPTCHA 当「反爬」而非「拿不到」，回复里标「浏览器可开」。
3. 出版社 PDF（ascopubs / journals.lww 一类）：Cloudflare 403，**别硬抓**，走第 4 节本地排版。
4. OA 状态与 PDF 直链备查：Semantic Scholar `api.semanticscholar.org/graph/v1/paper/DOI:<doi>?fields=openAccessPdf`
   会给出 `status: HYBRID` + `license`；Unpaywall `api.unpaywall.org/v2/<doi>?email=<真实邮箱>`（占位邮箱直接 422）。

**出版社页被文本提取器挡住时用浏览器**：`web_extract` 在 Cloudflare 质询站与付费刊上常直接失败
（`doi.org` 与期刊域名都可能），但 `browser_navigate` 到 `…/article(-abstract)/doi/<DOI>/<id>/<slug>`
后 snapshot 顶部就写着**栏目名与在线日期**，正文区给完整摘要，底部写明「You do not currently
have access」与单篇价格。这三样正好回答「能不能引、是不是综述、全文要不要另找」——
**提取器失败不等于页面打不开，别据此把选题判死**。

**官方图**：浏览器打开 PMC 文章页后用页面内 JS 取真实地址——懒加载时 `img.src` 是空的，**必须读 `currentSrc`**：

```
browser_navigate  https://pmc.ncbi.nlm.nih.gov/articles/PMC<id>/
browser_console   JSON.stringify(Array.from(document.querySelectorAll('img')).map(i=>({alt:i.alt,src:i.currentSrc||i.src})))
```

图落在 `cdn.ncbi.nlm.nih.gov/pmc/blobs/...`，curl 可直接下载（实测 6 张全部 200）。
注意图注里的 **FIG A1/A2/A3 是在线附录图**（BICR 独立评审曲线、亚组森林图、CNS-PFS 常在这），做画面时往往比正文图更好用。

## 4. 本地排出干净 PDF（比直接打印网页好得多）

直接 `--print-to-pdf` 打印 PMC 文章页会得到带导航/被引列表的 57 页杂项；
把 JATS XML 本地排成 HTML 再打印，实测 13–22 页、内容完整（正文 + 全部表 + 全部图 + 参考文献）。

```bash
# 1) 取 XML   2) 从 PMC 页取图存到 figs/ 并重命名   3) 按该论文改 scripts/jats2html.py 的 FIGMAP
python3 scripts/jats2html.py fulltext.xml paper.html
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --no-sandbox --virtual-time-budget=20000 \
  --no-pdf-header-footer --print-to-pdf="$PWD/out.pdf" "file://$PWD/paper.html"
```

**验收（必做）**：`fitz` 数页数、数内嵌图数应等于图张数、抽查关键数字出现次数
（主终点、HR、亚组 HR、`References`、每个 `FIG` 标签各 1 次）。

两个 JATS 坑：

- **为了解析而删掉 `xmlns` 声明会报 `unbound prefix`**（`xlink:` 前缀失去声明）→
  正确做法是把 `xlink:href` 改名为 `href`、**保留** `xmlns` 声明。
- **在线附录的图/表不在 `body`**，挂在 `back/app-group/app` 下；只遍历 `body/sec` 会漏掉它们。

## 5. 交付与存档形态

用户指定的目录通常是他自己的**选题工作目录**（里面可能已有封面图等）——只新增论文与速览，
**不动既有文件**。落三样：

```
<选题目录>/
  <刊>-<年>-<试验名>-原文（中文说明）.pdf     # 本地排版的全文，首页带完整引用信息
  论文速览-<试验名>.md                       # 可直接当 Obsidian 笔记
  原论文图/fig1-CONSORT流程图.jpg …          # 按内容重命名，别留 g001.jpg
```

PDF 末页要写一句版权与用途说明（开放获取的多为 CC BY-NC-ND：可转发署名、不可改作、勿再分发），
并在回复里说明**这份 PDF 是怎么来的**（官方 JATS XML 本地排版，不是出版社原版式）。

`论文速览.md` 固定含：frontmatter（`date:`）→ 引用信息（含 DOI/PMID/PMCID + 在线发表日 + 作者位次说明）
→ 一句结论 → 设计表（例数/人群/入组门槛/给药/基线特征）→ 疗效表 → 安全性表 → 图表清单（文件名 ↔ 原文 FIG 编号 ↔ 内容）
→ 写文案的边界 → 链接组（全文/摘要页/监管页/注册号/同赛道）。

## 6. 交付前：核心情报覆盖自查

把论文的核心情报列成清单逐条核文案有没有传到：主终点数字 + 风险比（换成人话「风险降 X%」）→
独立评审（BICR）复核结果 → 预设亚组 HR（谁获益更大）→ 安全性里**可管理**的那一半（起病时间/可逆/靠减量处理）→
探索性总生存（死亡事件数 / 是否已到最终分析节点）→ 同期对照试验。

**媒体稿普遍只传第一条。** 用户会直接问「这版有没有传达出原论文的核心情报」——先自查再交，比被追问划算。

两条最常被漏的边界：

- **与历史试验不可直接比**：PFS 起算点不同的数字并列就是错（诱导期试验从诱导开始算，维持期试验从诱导结束算）。
- **探索性 OS 的 HR 不能当结论**：论文常写「OS 不成熟」，但正文里给了当前死亡事件数与探索性 HR——
  可以写「早期信号方向一致、未见不利趋势」，**不得换写成「死亡风险降 X%」**（事件数远未达最终分析所需，
  论文通常明写最终分析预计的事件数与时间点）。

## 坑

- 搜三套名字（通用名 / 商品名 / 试验代号）+ 中文译名：只搜一套必漏，库里中文稿可能为零。
- 别用 curl 的 403/404 判「链接失效」：政府站与药企站挡爬虫，**以浏览器打开为准**再写进交付。
- **政府/军方 PDF 被拦时改走高校合规整理页**：`web_extract` 对 `cto.mil` 一类站点会按地址判定直接
  `Blocked: private or internal network address`。同一份清单（Section 1286 等）在高校 research-security /
  compliance 页有逐条表格（机构名＋中英文名＋国别＋新增生效日），一所学校就是一份交叉验证。
  清单类事实必须配「官方 news release 或第二家媒体」核时间点，只引清单编号不算核完。
- 会议摘要与期刊论文的署名顺序不同，**同一研究别混用两种署名**。
- 亚组的中位月数常只在大会报告里给，论文正文只给 HR——引用时标清载体，不要拼成一个来源。
- 存档图的文件名要带内容（`figA3-CNS-PFS脑转移曲线.jpg`），否则下一轮做画面还要重新核图注。

## 附：`scripts/jats2html.py`

把 Europe PMC 的 JATS XML 转成可直接打印的 HTML（含表格、图、附录、参考文献）。
用法与两个坑写在脚本头部；换论文时只需改 `FIGMAP`（JATS 的 `graphic/@href` → 本地图路径）。
