# 找「能下载」的论文：检索 + 核验配方

用户要求「引具体论文 / 高 IF / 要能下载」时走这套。核心原则：**先用 OA 元数据判定可下载性，再用可下载的文献去撑结论**，不要先按 IF 选好再发现拿不到全文。

## 0. 运行环境

用 `/Users/Jin/.local/bin/python3.11` 跑脚本。系统 `python3` 是 3.9，`int | None` 这类 3.10+ 写法会直接 TypeError。

## 1. Europe PMC：按主题/结论找候选（免 key）

```python
import json, urllib.parse, urllib.request
def epmc(query, n=50):
    p = {"query": query, "format": "json", "pageSize": str(n), "resultType": "core"}
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(p)
    return json.loads(urllib.request.urlopen(url, timeout=60).read())
```

要取的字段：`title` / `pubYear` / `journalInfo.journal.title` / `doi` / `pmid` / `pmcid` / `isOpenAccess` / `inPMC` / `fullTextUrlList`。

可复用查询式：

| 目的 | 查询 |
|---|---|
| 某年该主题全部新文献 | `TITLE:"measles" AND PUB_YEAR:2026` |
| 某国/某州暴发相关 | `(measles AND outbreak) AND ("United States" OR "Texas") AND PUB_YEAR:[2025 TO 2026] AND SRC:MED` |
| 消除状态/政策类 | `("measles elimination status" OR "elimination of measles") AND PUB_YEAR:[2025 TO 2026] AND SRC:MED` |
| 单篇元数据（有 PMCID） | `PMCID:PMC13218421` |
| 单篇元数据（有 DOI） | `DOI:"10.1073/pnas.2605971123"` |
| 疫苗有效性/覆盖率 | `TITLE:"measles" AND (TITLE:"vaccine effectiveness" OR TITLE:"vaccination coverage")` |

坑：`PMCID:"..."` 加引号会 0 命中，不加引号才对；`DOI:"..."` 反而必须加引号。空结果先怀疑查询语法，再怀疑真没有。

## 2. OpenAlex：判定能否免费下载（免 key，最可靠）

```bash
curl -s "https://api.openalex.org/works/doi:10.1073/pnas.2605971123"
```

看三处：

- `open_access.oa_status`：`gold` / `hybrid` / `green` / `diamond` = 可免费拿到；`closed` = 出版商版付费（但仍查 `locations`，可能有 green 作者稿）。
- `best_oa_location.pdf_url`：最直接的下载入口。
- `locations[]`：**逐条看 `version=acceptedVersion` 的条目**——出版商版付费的论文，免费 PDF 常是 medRxiv 预印本落在这里。

## 3. 直链形态速查

| 源 | 可下载直链 | 备注 |
|---|---|---|
| PMC 作者稿 / 官方稿 | `https://pmc.ncbi.nlm.nih.gov/articles/PMCxxxx/pdf/<file>.pdf` | `<file>` 必须从文章页 HTML 取（见下），不要猜 |
| PMC 文章页 | `https://pmc.ncbi.nlm.nih.gov/articles/PMCxxxx/` | curl 得到 ~1.8 KB 的 reCAPTCHA 页，不是付费墙 |
| medRxiv 预印本 | `https://www.medrxiv.org/content/medrxiv/early/YYYY/MM/DD/<doi>.full.pdf` | 200 application/pdf；`/content/<doi>v1.full.pdf` 会 403 或跳 `/node/` |
| EID（CDC，diamond OA） | `https://wwwnc.cdc.gov/eid/article/<vol>/<iss>/<id>_article` | 全文免费；主文 PDF 无稳定直链（猜路径必 404），给 HTML 页 |
| 出版商 OA（PNAS hybrid 等） | DOI 链接 | curl 403 属反爬；PMC 常另有同篇镜像 |

抓 PMC 的 PDF 文件名：

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
curl -s -L -A "$UA" "https://pmc.ncbi.nlm.nih.gov/articles/PMC8590458/" -o p.html
grep -oE 'href="[^"]*\.pdf[^"]*"' p.html | head -1
```

## 4. 核验命令与判据

```bash
curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download}B\n" -L -A "$UA" "<url>"
grep -oiE 'register to read|sign in to |subscriber-only|create a free account' page.html
```

| 结果 | 含义 | 动作 |
|---|---|---|
| `200 application/pdf` | 可下载（已验证） | 直接给直链 |
| `200 text/html` 且含 “Checking your browser” | PMC reCAPTCHA 反爬 | 用浏览器复核，别判付费 |
| `403` | Cloudflare 反爬 | 用 OpenAlex `oa_status` 定性 |
| `404` | 路径猜错（文件名/卷期号不对） | 回文章页找真链，别下“死链”结论 |

## 5. 浏览器复核（唯一可靠判据）

`browser_navigate` 打开 PDF → `browser_vision` 问「标题/作者是谁、有没有付费或登录提示」。
不要用 `browser_console` 跑 async `fetch` 验证——该评估路径可能直接 500，得出的是假失败。

## 6. 交付模板

按**结论**分组（不是按期刊排序），每条一行：

```
| 结论/用途 | 论文题名 | 期刊(IF≈档位) | 免费下载 |
```

- 下载不到的单列一栏，写明原因 + 免费替代（预印本 / PMC 作者稿 / 免费行业报道），不要静默换低档源。
- IF 写「≈」并注明「以最新 JCR 为准」。
- 正文清单存 md 到用户的选题文件夹，聊天里只给精简版（推荐篇目 + 遮挡不了的坑）。
