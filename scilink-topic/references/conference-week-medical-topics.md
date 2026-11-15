# 会议季选题手册（congress week）

适用：ESMO / ASCO / AACR / ASN Kidney Week / ECTRIMS / AHA 这类以 late-breaking abstract（LBA）为核心的医学大会。用户问「大会结束了没 / 现在能不能出汇总」，或要在会期批量入选题库时用。

## 1. 判收官：看时刻，不看日期

| 信号 | 在哪看 | 怎么读 |
|---|---|---|
| 起止日期 | 会议主页 | 只有日期，**不说明最后一天是半天** |
| 注册台开放时间 | Registration 页 | 末位开放时间通常就是收摊时间（如最后一天 08:30–12:30） |
| 最后一场 session | Programme / 媒体速览稿 | 真正的内容终点（如 09:00–13:00 Highlights） |
| 总统研讨会（Presidential Symposium） | Programme | 重磅 LBA 在这里放完，通常在倒数第二天或倒数第一天的下午 |

规则：
- **收官前不定稿**。最后半天的 Scientific Congress Highlights 是官方对「本周最重要数据」的复述与排序，做汇总视频时它直接给出优先级。
- 交付时给用户一张小时表：当地现在几点 / 最后一天议程时段 / 换成北京时间 / 注册台时段。
- 时区：欧洲会跨夏令时切换（10 月最后一个周日 CEST UTC+2 → CET UTC+1），**同一条官网日程可能一半 CEST 一半 CET**；北京 = CET+7、CEST+6。先 `TZ=Europe/Madrid date` 和 `TZ=Asia/Shanghai date` 对一次。

## 2. 抓 LBA：信源分级

1. 学会官方 press release / 官方会议新闻页（有口径、有主持人背景）
2. OncLive / Targeted Oncology / ecancer / MedPage meeting coverage 的**单试验**稿（有 HR、CI、样本量）
3. 药企 press release：只有 topline（
「met primary endpoint」），**没有效应量**，不能当数据源
4. 会前展望稿（preview / abstract preview）：**结果出来之前写的，不能当结果用**

一次主席研讨会通常 4 个 LBA，一篇 recap 把 4 个都写了——拿数字最快，但不能因此给多条记录共用链接（见第 4 节）。

## 3. 同步发表核查（最常被漏）

大会重磅 LBA 多数同期在 NEJM / Lancet / Lancet Oncology / Annals of Oncology 上线。

```python
import json, urllib.parse, urllib.request, time

trials = {"试验名": "药名 或 试验代号 + 瘤种"}
for j in ["New England Journal of Medicine", "The Lancet",
          "Annals of Oncology", "The Lancet Oncology"]:
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode({
        "query.bibliographic": q,          # 只写试验名会返回一堆无关论文
        "query.container-title": j,        # 关键的第二个查询维度
        "rows": 2,
        "filter": "from-pub-date:<会期首日>",
        "select": "title,DOI,container-title,published"})
    # 串行，间隔 ≥1.2s；命中后 GET /works/<DOI> 复核 title 与试验对得上
```

- **会议摘要本身也可能有 DOI**：ESMO 的 LBA 进 Annals of Oncology 摘要补编，形如 `10.1016/j.annonc.<年>.<月>.xxxx`。用 `query.container-title=Annals of Oncology` 能查到，查到就当正式 DOI 用。
- 期刊索引有小时级延迟：新闻里写「Lancet 同步发表」但 Crossref 当天查不到 → DOI 列写 `<摘要英文题>. 无DOI（会议报告 LBA<n>；Lancet 同步发表，索引尚未上线）`。**不要拿新闻报道自身的 DOI 充数，也不要猜 DOI**。
- 日期取 `published-online`（`GET /works/<DOI>` 里），不要用 `published` 的期次月份。

## 4. 一试验一链接

去重自检中「任意两条记录链接不得相等」在会议季最容易踩：一篇 recap 挂着 4 个试验。

1. 给每个试验找独立稿：OncLive / ecancer / Targeted Oncology / MedPage 的单试验文章。
2. **核独立稿的 `datePublished`**：厂家或媒体的「单试验」文章可能是几个月前的 topline 公告稿，标题几乎一样但日期、数据都不是本次会议 → 弃用。
3. 有正式论文的优先用 `https://doi.org/<DOI>`（出版社页常 403，doi.org 纯 URL 在浏览器可开）。
4. 兜底：recap 页只留给其中一个试验，其余走 DOI。

探活 + 取日期的单行命令：

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
code=$(curl -sSL -o /tmp/p.html -A "$UA" --max-time 25 -w '%{http_code}' "<url>"); echo "$code"
grep -Eio 'datePublished"?:? ?"[^"]+' /tmp/p.html | head -2
```

判读：`000` = 连不上（换源）；`202`/`403` = WAF 拦脚本，改用 `web_extract` 读正文与日期；`200` 但有多个 `datePublished` 时取最先出现的那个。

## 5. 选材偏好（会议季特有）

最高互动的往往不是「最大阳性结果」：

- **阴性 / 提前终止**：非劣效未成立、试验因 OS 不平衡封存（de-intensification 类尤其反常识）
- **双终点不一致**：OS 达显著但 PFS 未达（或反之）→ 天然是「怎么读统计」选题
- **曲线交叉 / OS 未达显著**：中位 PFS 翻倍但 OS 还没到边界，媒体标题常把这一条删掉，补上就是差异点
- **头对头试验**：新药直接对打同类老药，换药逻辑清晰
- **罕见瘤种的首个阳性 III 期**：样本小但「十年空白」，故事性强
- 中国团队 + 顶级刊同步发表：近年稳定卖点，会期 LBA 里中国研究占比可达三分之一

会后必做：肿瘤会天然全是肿瘤，主动问要不要给心血管/呼吸/重症/妇产等配额度，否则库结构失衡。

## 6. 坑

- 用会期日期推断收官时刻 → 最后一天只有半天，会提前宣布「已结束」或白等一天。
- 拿媒体稿的「风险几乎减半」当数据 → 必须回到 HR / CI / 绝对率，媒体常省略「OS 未达标」。
- 药企 press release 当唯一信源 → 只能核到「达到主要终点」。
- 会前预览稿与会后结果稿混用 → 数字和日期双错。
- 同一试验已在库（topline 阶段录过）→ 会后拿到完整数据时**更新那一条，不新建第二条**：`原文发布日期` 换正式发表日、`DOI链接` 补论文 DOI、`来源链接` 换成本次报道页、标题加「正式结果／正式发表」、话题度按效应量重打（通常上调）。**「换角度再录一次」是错的做法**——同一试验在库里并存两条，用户按话题度排序时看到两个几乎相同的题，会当成重复录入回头要你清。只有「同一试验的不同终点/不同人群各自构成独立新闻」时才能分两条（如主终点阴性但亚组阳性），那时标题必须一眼能区分，并在汇报里点明关系。
- 同批 LBA 几分钟内全上 NEJM 时，先把入选的试验名逐个拿去扫 `record-list` 的「内容标题」再决定新建还是更新——一轮 7 篇里常有一两篇是几个月前顶线稿录过的老相识。
