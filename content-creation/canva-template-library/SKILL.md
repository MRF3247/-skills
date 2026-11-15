---
name: canva-template-library
description: Use when 抓取 Canva 模板/按官方主题分类建素材库/kimi 筛医学学术主题。
---

# Canva 模板素材库工作流

抓取 Canva 小红书模板 → 官方主题分类 → kimi 视觉筛选 → Obsidian 排版笔记。

## 触发场景
- 用户要扒 Canva 模板示意图存素材库（如 `canva.cn/s/templates` 链接）
- 用户要按官方分类整理模板图
- 用户要用 kimi 审核哪些图适合医学/论文/学术主题
- 用户要整理留白/风格海报成排版参考笔记

## 关键路径
- 素材库: `/Users/Jin/Documents/素材/小红书模板/Canva小红书图文模板/`
- 排版参考库: `/Users/Jin/Documents/医时知识库/视觉风格参考/排版参考/`
- Billfish 素材: `/Users/Jin/Documents/本地资源库/`（浏览器采集/ 放新下载图）
- 参考图源: `/Users/Jin/Documents/医时知识库/视觉风格参考/排版参考/样张/`

## 步骤 1：抓取模板列表（免登录）

用户给的 `canva.cn/s/templates?query=...` 需要登录（弹登录墙）。**用免登录 URL 替代**：

```
https://www.canva.cn/rednote/templates/posts/          # 小红书帖子模板（全量）
https://www.canva.cn/templates/?query=xiaohongshu      # 搜索式（也是模板）
```

- 每页 50 个，翻页 `?continuation=50/100/...`
- 列表页 img 懒加载（headless 滚动不触发），**不要依赖列表页 img src**
- 直接从 DOM 提取模板 id：`a[href*="/templates/EA"]` → `/templates/(EA[A-Za-z0-9_-]+)/`
- 模板详情页 `/templates/{id}/` 免登录，含 og:image（带 AWS 签名，1 天内有效）

## 步骤 2：下载图片（og:image + urlB64 传输）

```javascript
// 浏览器 console：fetch 详情页 → 提取 og:image → 反转义 → 图片转 base64
const resp = await fetch('https://www.canva.cn/templates/' + id + '/');
const html = await resp.text();
const m = html.match(/<meta property="og:image" content="([^"]+)"/);
// ⚠️ 必须反转义 HTML 实体，否则签名参数损坏（AuthorizationQueryParametersError）
const ta = document.createElement('textarea'); ta.innerHTML = m[1]; const url = ta.value;
const imgResp = await fetch(url);
const blob = await imgResp.blob();   // 某些模板返回 octet-stream，也是有效 JPEG
const b64 = await new Promise(res => { const r = new FileReader(); r.onload = () => res(r.result); r.readAsDataURL(blob); });
```

**传输坑**：
- console 返回大 base64 会持久化到文件且**截断**（Incorrect padding）→ 改为返回 `urlB64 = btoa(unescape(encodeURIComponent(url)))`（只传 URL 的 base64），本地解码后**curl 直下签名 URL**（不需要 cookie，签名在 query 里）
- 批量 fetch 详情页易限流（偶发空返回/octet-stream）→ 每批 ≤10 个、间隔 1-2.5s、失败重试 3 次
- 每次 console 执行 ≤10 个模板（20 个会超时）

## 步骤 3：官方主题分类

官方筛选「主题」20 类，URL 规律：

```
https://www.canva.cn/templates/?category=tAEUgd5tLWo&fTheme=THEME_XXX
```

fTheme 值（从页面 script 提取 `THEME_[A-Z_]+`）：
`THEME_SHARE` 分享 / `PROMOTE` 宣传 / `EVENT` 活动 / `RECRUITMENT` 招聘 / `SALE` 促销 / `TRAIN` 培训 / `ENROLLMENT` 招生 / `BLESS` 祝福 / `INTRODUCE` 介绍 / `CELEBRATE` 庆祝 / `REUNION` 聚会 / `GOOD` 公益 / `OPENING` 开业 / `COMPETITION` 比赛 / `WEDDING` 婚礼 / `GRATEFUL` 感谢 / `LECTURE` 讲座 / `MEETING` 会议 / `COMMUNICATE` 交流 / `INVITE` 邀请

**重要**：从全量列表抓的热门模板，很多**没有打主题标签**（翻 10 页都找不到）→ 官方确认的用官方页匹配，其余用模板名关键词语义推断（关键词表见 references/canva-official-themes.md），索引里标注「官方确认/语义推断」来源。

## 步骤 4：kimi 视觉筛选主题适配

用 k3-256k（kimicode）逐张审核图是否适合医学/论文/学术：
- **只看视觉风格，不读文字**（用户明确要求）：医学插画/解剖/细胞/DNA/科研图表/学术海报/实验室场景 = 适合；风景/美食/美妆/卡通/庆典 = 不适合
- 输出 JSON `{"suitable": bool, "reason": "一句话视觉理由"}`
- **max_tokens ≥ 1200**（800 会截断缺字段）
- 不适合的移到 `_待删除/`（用户确认后再彻底删，勿直接 rm）
- 筛选清单生成 `02_筛选清单.md`（适合/不适合/待补跑三组）

## 步骤 5：Obsidian 排版笔记

**图片嵌入格式（用户纠正过的硬规则）**：
- ✅ `<div style="display:flex;flex-wrap:wrap">` + `<img src="样张/xx.jpg" width="170" style="margin:3px;border-radius:6px"/>`
- ❌ 禁用 `![[样张/xx.jpg|180]]` wikilink（Obsidian 里显示异常）
- frontmatter 用 `date:` 非 `created:`；tags 用「排版参考」
- 逐张分析配单图 `width="360"`
- 笔记入 `00_索引.md` 登记（`### N. 标题` 追加到已收录区）

## 坑速查
| 坑 | 解法 |
|---|---|
| 签名 URL 403 | 反转义 `&amp;` → `&`；curl 直下（签名在 query 有效 1 天） |
| console base64 截断 | 改传 urlB64（URL 的 base64），curl 下载 |
| 批量限流 | ≤10 个/批、间隔 1-2.5s、重试 3 次 |
| 懒加载不触发 | 从详情页 og:image 拿图，不依赖列表页 img |
| kimi 输出截断 | max_tokens ≥ 1200 |
| kimi 偶发空返回 | 重跑缺失项（断点续传 JSON） |
| 模板无主题标签 | 关键词语义推断 + 索引标注来源 |
| 图片格式 | Obsidian 用 HTML `<img>` 网格，不用 wikilink |

## 参考文件
- `references/canva-official-themes.md` — 官方 20 主题 + 语义推断关键词表
- `references/kimi-visual-prompts.md` — 视觉分析/筛选 prompt 模板
