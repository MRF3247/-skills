# 来源链接、原文日期与 DOI 核验

三条铁律：链接必须真指向这篇内容（标题比对，不看域名）、日期必须来自页面本身、DOI 必须能解析且标题对得上。任一项拿不到就留空并在汇报里写原因，禁止推测。

## 1. 抓页面元信息

camofox 取 `document.title / h1 / og:title / meta datePublished / meta citation_* / body.innerText` 一次拿全（body 前 3-4k 字够写卡片，也够抽日期）。

- 日期优先级：`datePublished` / `article:published_time` / `citation_publication_date` / `citation_online_date` → 正文日期行（`October 15, 2026`、`2026-07-30 06:50`）。
- 很多站（Medscape/MedPage/搜狐）**不写 meta 日期**，只有正文里的日期行；正则同时匹配英文月日年与 `YYYY-MM-DD`。
- 写入格式 ISO 带时区，表格时区 Asia/Shanghai。
- 收录库里的 `发布时间` 只能当参考，不能当原文日期填。

### 1.1 被 Cloudflare 挡住的站：先用 `web_extract`，再谈 camofox

curl（带 UA）对出版社/新闻站普遍 403：NEJM、Medscape、MedPage Today、theLancet、gastrojournal.org、bioRxiv 都可能回 `Just a moment...` 或 429。核验阶段的顺序是：

1. **`web_extract([url])` 先试**——它对 NEJM、Medscape、MedPage Today、JAMA Network 这几家实测能拿到正文，返回内容里自带 `Published: YYYY-MM-DD` 行与页面 `h1`，一举拿到「日期＋标题比对」两件事（MedPage 的日期行形如 `October 22, 2026 • 3 min read`，Medscape 是页内 `date` meta）。
2. Nature 系列 curl 直连常能过，取 `"datePublished":"…"` 或 `citation_online_date`；打回空串时再用 `web_extract`。
3. 只有前两步都拿不到才动 camofox（Cloudflare 挑战要轮询 30-70 秒）；`navigate` 回 500 不等于打不开——那是浏览器唤醒竞态，**换新 tab 重试一次**往往就放行（Lancet、gastrojournal.org 实测如此），放行后 `citation_*` meta 可读。重试一次仍 500 才按第 3 节核 DOI 题名、日期留空，并在汇报里写「页面 Cloudflare 拒绝，取不到页面日期」。

### 1.3 Elsevier 的 `citation_date` 是期次日，不是上线日

Lancet / Gastroenterology / J Clin Epidemiol / JTCVS Open 放行后都只有 `citation_date` 与（有时）`citation_online_date` 两个 meta：

- **优先 `citation_online_date`**（如 `2026/02/27`）——这是线上首发日，可以填。
- **只有 `citation_date` 时要先判性质**：它经常是**期次日**（`2026/11/01` 这种月初齐整、甚至落在未来日期的，就是期号日），不能填；`citation_date` 恰好等于真实上线日（如 Lancet 某篇 `2026/10/24`）才可用。判据：与 `created.date-time`（Crossref 登记时刻）比，登记日≈上网日；citation_date 明显晚于登记日 → 期次日。
- 拿不到可填日期就留空，绝不拿期次日或抓取日凑——用户在评审季会拿这个日期对「发布时间」。

### 1.4 政策文件页（*.gov.cn）的日期行

nhc.gov.cn 的政策文件页 curl 只回 3-4KB 空壳（无 title、无正文），`web_extract` 也给不出日期；用 camofox 打开后 `document.body.innerText` 前 300 字就含固定格式 `发布时间：YYYY-MM-DD 来源: 司局名`，紧跟文号（`国卫科教发〔2023〕4号`）与落款日。**日期填「发布时间」，不填落款日**（两者常差几天）。most.gov.cn / nmpa.gov.cn 的同类页 curl 直连正常，可先 curl 再 camofox。

### 1.2 日期粒度：Crossref 只给到月就不能填

`api.crossref.org/works/<DOI>` 的 `published.date-parts` 常只有 `[[2026,6]]`（月刊/期号），这时**没有可填的日期**，留空；同理 `published` 给的是**期号月份**而非线上首发日（11 月期号的指南常常 10 月下旬就上线）。
`created.date-time` 是登记时间（≈线上首发时刻），用来在汇报里给一句「实际线上日很可能就是这天」，但它不是页面日期，不能拿来填 `原文发布日期`。

## 2. 链接验证

1. 打开链接，记 `httpStatus` 与 `final_url`（重定向后的真实地址）。
2. 标题比对：页面 `h1`/`title` 必须与选题标题同义，不能只是同域名。
3. 404 / 标题不符 → 回去搜正确链接；仍找不到就换选题，别拿错误链接凑数。
4. 聚合站代表链接会烂掉（热点 API 里的 URL 也可能 404），以打开成功的原文为准。

## 3. DOI 核验

```
https://api.crossref.org/works/<DOI>   # 返回 title / container-title / issued / type
https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:"<DOI>"&format=json&resultType=core
```

- Crossref 返回的标题与新闻主题一致 = 通过；`doi.org` 与出版社页常回 403，别拿它当验证入口。
- Crossref 会 429：串行、间隔 ≥1.2s，禁止并发。
- 新闻没 DOI 时按「支撑这条新闻的论文」找：先用标题关键词打 EuropePMC（能同时给 DOI + PMCID，OA 的还能直接拿去截图），再用 Crossref 补。
- EuropePMC 查不到 = 太新未收录；此时留空，不要凭记忆补一个「看起来对」的 DOI。
- 新闻稿本身的 DOI（Nature news、Lancet comment）不能当作研究论文 DOI 填进去。
- **同一篇文章在 Crossref 里常有一组近同名 DOI**：JAMA 会同时挂着原文（subtitle 是 `The XXX Randomized Clinical Trial`）、`Research Summary`（subtitle 就是这三个字）和同期述评（作者不同、subtitle 是设问句）。`query.bibliographic` 只按标题排序，三者都能命中，**光看标题会选错**。判据：目标页（`jamanetwork.com/journals/<刊>/fullarticle/<id>`）正文的引文行 `… JAMA. Published online <日期>. doi:10.1001/…` 里那个 DOI 才是原文；拿到后用 `type`+`subtitle`+`page/article-number` 复核，别用第一个命中结果。

## 4. 没有 DOI 的合法情况

会议摘要（AAO/ACG/EASD 等年会）、监管文件（FDA 新闻稿、CHMP 意见）、行业报告、政策通知、博客与开源教程 —— 留空并在汇报的「留空项及原因」里逐条写明。这类条目的 P2/P3 就截发布页本身。

## 5. 断言核验（标题/封面里的每个判断）

链接对、DOI 对，也不等于这句文案对。医学声明的翻车点几乎都在**限定词被吃掉**。

1. **回到原文找那句限定语**：新闻稿/论文摘要里的原句通常是「没有任何标志物能可靠预测**哪些感染会消退、哪些会进展**」——限定语是「预测结局」，不是「没有标志物」。写文案时把限定语一起带上，否则等于否掉整个筛查体系。
2. **区分三类问题**，不要混为一句：
   - 现在有没有病变（细胞学、阴道镜、病理）
   - 现在风险高不高（HPV 16/18 分型、p16/Ki-67 双染、E6/E7 mRNA、DNA 甲基化 —— 这些是**分流检测**，指南里有明确搭配，别写成「分流工具」）
   - 将来会不会进展（文章说的空白正是指这个）
3. **绝对化词降级**：`无法 / 零 / 从来没有 / 彻底` → `难以 / 至今没有 / 仍缺少`，并在同句给出范围（结局／单指标／常规临床）。用户会拿标题去问同行，同行一句「那 p16/Ki-67 算什么」就能把整条内容否掉。
4. **区分文章类型**：观点/评论（Trends、Lancet Comment、JAMA 观点）只有主张；预印本未同行评议；会议摘要未全文发表。三类都要在 ⚠️ 写清，不能写成「研究发现」。
5. **给出可点的证据链**：论文 DOI＋一手新闻稿/机构稿＋至少一条指南或共识（证明「已有分流手段」这类反向事实）。汇报里列成表格，用户会自己点开核。


## 6. 权威站打不开时

政府/机构站（`*.gov.cn` 等）可能整段不可达。此时：

- 改用能打开的二手报道（行业媒体、门户转载），并把「原文链接不可访问」写进正文的 ⚠️ 与汇报；
- 标题若为原文中文标题，原样保留；二手报道的标题不冒充官方标题；
- 若代表链接 404 且不同媒体给出的关键数字互相矛盾（疫情计数、样本量一类），直接剔除该选题并说明原因，不要挑一个数字写。
