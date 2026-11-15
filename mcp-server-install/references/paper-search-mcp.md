# paper-search-mcp 实例（2026-08 安装）

- GitHub: adamamer20/paper-search-mcp-openai（PyPI 包名 `paper-search-mcp`）；Node 版 Dianel555/paper-search-mcp-nodejs（源更多但 WOS/Scopus/ScienceDirect 要付费 key + 需 tsc 编译，放弃）
- 位置：`~/.hermes/mcp-servers/paper-search-mcp/.venv/`
- 启动：`.venv/bin/python -m paper_search_mcp.server`（stdio；设 PORT 环境变量则转 streamable-http）
- config.yaml：`mcp_servers.paper_search: {command: <venv python 绝对路径>, args: ["-m", "paper_search_mcp.server"]}`
- 覆盖：arXiv / PubMed / bioRxiv / medRxiv / Google Scholar / CrossRef / Sci-Hub / IACR / Semantic Scholar；无需 API key

## 包特性（实测坑）

- `search()` 是**同步**方法（`await p.search(...)` 报 `TypeError: object list can't be used in 'await' expression`）
- 返回 **Paper 对象**（`.title` `.paper_id` `.url` 等属性），不是 dict——`item.get()` 报 AttributeError
- 医学检索实测：PubMed 搜 clinical prediction model / mendelian randomization+ML 正常返回 PMID+链接

## 重启后可用工具

`mcp_paper_search_*`：search、fetch、search_pubmed、search_arxiv、search_biorxiv、search_medrxiv、search_google_scholar、search_iacr、download_arxiv、download_pubmed、read_crossref_paper 等

## 使用建议（用户场景）

- 选题表方向反查 PubMed：临床预测模型 / 孟德尔随机化+ML / 国自然热点关键词
- 下载 PDF 归档到 `~/Documents/素材/参考文献/`（日期-来源-标题命名）
