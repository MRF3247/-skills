# Canva 模板批量扒取管线（2026-08-07 实测全通）

目标：把 Canva 小红书图文模板的示意图批量下载到本地素材库，并按官方主题分类归档。
结果：150 张 299×400 JPEG 全部落地，20 个官方主题分类。

## 素材库位置（用户约定）

- 用户素材库 = `/Users/Jin/Documents/素材/`（保存字体/表情包的文件夹）
- 小红书模板素材库 = `素材/小红书模板/`：`Canva小红书图文模板/`、`排版样图/`（165 张 19 类）、`视觉风格样图/`（340 张 11 家族）
- Billfish 素材库 = `/Users/Jin/Documents/本地资源库/`（`浏览器采集/` 为最近下载；位置可从 `~/Library/Application Support/Billfish/config/recent_lib.ini` 的 `CustomSettingLibPath` 读）

## 关键发现：哪些 URL 不需要登录

- **登录墙**：`canva.cn/s/templates?query=...` 弹登录遮罩，模板不渲染（用户原始链接是这个）
- **公开可抓**：`canva.cn/rednote/templates/posts/`（小红书帖子模板，10,096 个，21 页，无需登录）——真正的官方分类页，每页 50 个
- 子分类：`/rednote/templates/red-covers/`（封面）、`/rednote/templates/videos/`（社媒视频）
- 模板详情页 `/templates/{id}/` 无需登录，og:image 带完整信息
- curl/urllib 直连 canva.cn 一律 403（Cloudflare 防护），必须走浏览器会话

## 抓取流程

1. **列表页拿模板 id + alt**：browser_navigate 打开 `https://www.canva.cn/rednote/templates/posts/?continuation=N`（N=0/50/100...），browser_console 提取：
   ```js
   const links = Array.from(document.querySelectorAll('a[href*="/templates/EA"]'));
   const seen = new Map();
   for (const a of links) {
     const m = a.getAttribute('href').match(/\/templates\/(EA[A-Za-z0-9_-]+)\//);
     const img = a.querySelector('img');
     const alt = img ? img.alt : '';
     if (m && !seen.has(m[1])) seen.set(m[1], alt);
   }
   return JSON.stringify(Array.from(seen.entries()).map(([id, alt]) => ({id, alt})));
   ```
   注意：列表页 img 懒加载（IntersectionObserver），滚动/强制滚动都不触发 headless 加载，**src 拿不全**——所以只拿 id+alt，图从详情页拿。

2. **详情页拿图（核心）**：模板详情页 og:image 是带 AWS 签名的 CDN URL。浏览器内一次性处理：
   ```js
   const resp = await fetch('https://www.canva.cn/templates/' + id + '/');
   const html = await resp.text();
   const m = html.match(/<meta property="og:image" content="([^"]+)"/);
   const ta = document.createElement('textarea'); ta.innerHTML = m[1]; const url = ta.value;  // 关键：反转义 &amp; -> &
   const imgResp = await fetch(url);
   const blob = await imgResp.blob();
   // -> FileReader 转 base64 回传
   ```
   **两个致命坑**：
   - og:image URL 里 `&` 是 HTML 实体 `&amp;`，不反转义直接 fetch 会报 `AuthorizationQueryParametersError`（XML 错误体）——用 `textarea.innerHTML` 反转义
   - 部分模板返回 `application/octet-stream`（不是 image/jpg）但数据是有效 JPEG——**类型检查要放宽**，不能只认 `blob.type.includes('image')`

3. **base64 回传超限处理**：一次 10-20 张的 base64 JSON 超过 console 返回上限（>300KB 持久化到文件），分批（每批 ≤10 张），或用 urlB64 方式：浏览器里 `btoa(unescape(encodeURIComponent(url)))` 只回传 URL 的 base64，再 curl 下载。

4. **curl 直接下载签名 URL（更稳）**：`template.canva.cn/{id}/N/0/299w-{hash}.jpg?X-Amz-...` 签名 URL 不需要 cookie，`curl -s -o out.jpg <url>` 直接成功（之前手改 URL 403 是因为签名无效，不是需要 cookie）。签名有效期数小时到 1 天。

## 官方主题分类（2026-08-07）

- URL 规律：`/templates/?category=tAEUgd5tLWo&fTheme=THEME_XXX`（用户原始链接 adj 参数解码后就是 category；fTheme 是官方主题筛选项）
- 20 个枚举：THEME_SHARE 分享 / PROMOTE 宣传 / EVENT 活动 / RECRUITMENT 招聘 / SALE 促销 / TRAIN 培训 / ENROLLMENT 招生 / BLESS 祝福 / INTRODUCE 介绍 / CELEBRATE 庆祝 / REUNION 聚会 / GOOD 公益 / OPENING 开业 / COMPETITION 比赛 / WEDDING 婚礼 / GRATEFUL 感谢 / LECTURE 讲座 / MEETING 会议 / COMMUNICATE 交流 / INVITE 邀请
- 翻页：`&continuation=50`
- **覆盖不全的坑**：从全量热门列表抓的 150 张，只有 54 张出现在各主题页前几页（官方确认），其余 96 张不在任何主题页前 500——因为主题筛选基于模板元数据标签，热门模板不一定打了主题标签。处理：已确认的标「官方确认」，其余用模板名关键词语义归入官方主题并标「语义推断」（诚实标注来源），见 `canva_classify_v2.py`。

## 生成图的评分口径（kimi 视觉审核）

- 医学/学术适配筛选 prompt：开头「【只看视觉风格，不读图里任何文字】」，列适合/不适合的视觉特征清单，只输出 JSON `{"suitable": bool, "reason": "..."}`
- 留白评分维度：留白充足度 / 可加字性 / 风格还原度 / 无文字乱码（各 /10）
- 空返回/解析失败是偶发瞬时错误，重跑即成功；批次脚本要断点续传（结果 JSON 即时落盘）

## kimi 批量筛选 → 待删除区流程（2026-08-07）

- **筛选口径**：判断图是否适合「医学/论文/学术」主题时，**只看视觉风格**（医学插画/细胞图形/学术版式/复古图谱/极简专业排版 vs 美食/旅游/美妆/卡通/促销），不读图上文字——用户明确纠正过。
- **结果应用分两步**：① `apply_canva_filter.py` 把「不适合」移入 `_待删除/`（**不直接 rm**，用户确认后才删）；② 生成 `02_筛选清单.md`（✅适合 / ❌不适合(含理由) / ⚠️解析失败三段）。用户确认删除前保留待删除区。
- **漏网对账**：批次断点续传可能漏图（试跑批次与全量批次索引衔接处）。跑完必须「清单 id ↔ 文件系统（含 _待删除）双向对账」，发现未审图补审。
- **下载截断的损坏图**：`im.load()` 报 broken data stream 的 JPEG 用浏览器重取详情页新签名 URL → curl 重下（签名会过期，旧 URL 无效）→ load() 验证。

## 损坏图诊断与重下（2026-08-07 实测）

- **PIL `verify()` 只查文件头，`load()` 才真正读像素**：`Image.open()+verify()` 报 OK 但 `im.load()` 报 `OSError: broken data stream` = JPEG 传输时被截断（curl 偶发）。诊断脚本必须 `load()`，不能只 verify。
- 修复：浏览器重新 fetch 详情页拿**新签名 URL**（旧签名可能过期）→ `curl -s -o <path> <url>` 重下 → `load()` 验证完整（正常 299×400 图 44-72KB）。
- 批次跑完后用「清单 id ↔ 文件系统」双向对账找漏网：文件名可能含 `_`（如 `EAG_-jWTJfU`），提取 id 用正则 `_(EA[A-Za-z0-9_-]+)\.jpg$`，不要用 `split('_')`。
