---
name: camofox-browser-api
description: "用 camofox 反检测浏览器 REST API 抓网页/RSS 时使用，规避风控封 IP。"
version: 1.0.0
metadata:
  hermes:
    tags: [camofox, browser, scraping, anti-detection, rss, cloudflare]
---

# Camofox 浏览器抓取通道（localhost:9377 REST API）

Use when 网页站被 curl 风控/封 IP（如 NEJM Cloudflare 封禁）、或需要真实浏览器指纹抓取网页/RSS/搜索页（B站搜索、医学资讯源）。Camofox 是反检测浏览器（C++ 级指纹伪装），比 curl 安全得多。

## 核心流程（实测 2026-08）

1. **健康检查**：`GET http://localhost:9377/health`（`browserRunning` 可能为 false——浏览器惰性启动，首次 navigate 会自动拉起）
2. **创建 tab**：`POST /tabs {"userId": "<用户标识>", "sessionKey": "<会话组>"}` → 返回 `tabId`
3. **导航**：`POST /tabs/{tabId}/navigate {"userId": ..., "url": ...}`（SPA 页 sleep 5-6s 等渲染）
4. **拿内容**：`POST /tabs/{tabId}/evaluate {"userId": ..., "expression": "document.documentElement.outerHTML"}` → `result` 字段 = 原始 HTML/XML
5. **结构化提取**：evaluate 传 IIFE JS 返回 JSON 字符串（如 B站搜索页 `document.querySelectorAll('.bili-video-card')` 提取标题/UP主/播放），`json.loads(result)`

## 表单交互：`/type` 与 `/click`（登录页、搜索框、筛选器）

```
POST /tabs/{id}/type  {userId, selector, text, mode:"fill"|"keyboard", delay, submit, pressEnter}
POST /tabs/{id}/click {userId, selector 或 ref}
```

文案输入/点按钮**一律走这两个端点，不要用 JS 赋值 + `dispatchEvent('input')`**：Vue/Element UI 的 v-model 常吃不到合成事件，表面填进去了、提交时值被清空且不报错，排查成本极高。

- ⚠️ **selector 必须唯一，否则回 422**：`/click` 走 Playwright locator，命中多个元素就是 `strict mode violation: ... resolved to N elements`。多 tab 表单（账号登录/验证码登录两套面板共存）常同时有 2-3 个同名「登录」按钮——先 evaluate 列出候选的 `className`/`disabled`，再用 `button.login-btn:not([disabled]):not(.disabledBtn)` 这类收窄写法。
- ⚠️ **协议/提示弹窗会静默吞掉点击**：国产站常把「同意《用户服务协议》」做成点提交后弹出的「同意并继续」，不点它请求根本不发（页面无报错、URL 不变）。点提交前后各补一次「同意」兜底。
- 调试分三截定位：① evaluate 读 `input.value` 看值进没进；② 看按钮 `disabled`/点击返回值；③ 读页面提示文案（`.el-message` 等）看服务端怎么说。
- **想拿登录后的 token/cookie？端点里没有**：`/tabs` 系列只有 navigate/evaluate/type/click/press/scroll/select/upload/snapshot/extract/images/links/wait/screenshot/stats/back/forward/refresh/downloads/open，没 `/cookies` `/storage` `/network`。只能从 `document.cookie` / `localStorage` 读，或 hook `fetch`/`XMLHttpRequest` 抓请求头（结果写 DOM 节点，别存 window 变量）。完整「代填表登录 → 抓 Bearer Token」流程（含用假凭证验链路）见 `token-gated-video-download` 技能的 `references/auto-login.md`。


## 截图（页面 → PNG，实测可用）

```
POST /tabs/{id}/viewport {userId,width,height}   # 高度上限≈2400；6000 直接 400
GET  /tabs/{id}/screenshot?userId=<uid>          # 必须 GET（POST 会 404）
GET  /tabs/{id}/screenshot?userId=<uid>&fullPage=true   # 全页
```

- 返回值是 `image/png` 二进制，直接写文件；不加 `fullPage` 只截视口一屏。
- ⚠️ **超长文档全页截图可能回 500**（页面高度过大，如带完整 References 的 PMC 全文）：先用 JS 删掉文末参考文献/评论区/推荐位再截，或改截同一内容的新闻页/摘要页；重复重试无效，不要在这死循环。
- ⚠️ **正文在内部滚动容器里时全页截图也只有一屏**（MedPage 类：`document.body.scrollHeight ≈ 视口高`，但正文段落 y 坐标却在视口外）。截图前先 unwrap：遍历 `div,section,main,article`，对 `scrollHeight > clientHeight+100` 且 overflow 为 hidden/auto/scroll 的元素设 `overflow:visible;height:auto;max-height:none`，页面才会真正展开。
- ⚠️ **隐藏广告的 CSS 不要命中 `paywall`/`sticky`/`article-` 这类 class**：出版社正文容器就叫这些名字，写了就只剩标题。只黑名单明确的广告/弹窗/导航。
- ⚠️ **高亮定位用 DOM 不用像素**：页面上常自带淡黄提示框，按“黄色像素行”找位置会命中它；取目标元素 `getBoundingClientRect().top + window.scrollY` 才准。
- 现成实现：`feishu-content-material-library` 技能的 `scripts/shot_web_card.py`（渲染→高亮→全页截→裁 3:4）。

### 把本地 HTML 渲成 2 倍图（做配图/卡片，不依赖截图源）

写好的 HTML/CSS 图要导成 PNG 时，**camofox 不接受 `file://`**（navigate 回 400 `Blocked URL scheme: file: (only http/https allowed)`）。走本地 http：

```bash
cd <figs 目录> && python3 -m http.server 8877   # 后台跑；避开 8899（Flask 面板占着）
# navigate http://localhost:8877/fig1.html
```

**2 倍导出**（viewport 是 CSS 像素，截出来只有 1x）：先 evaluate 设 `document.body.style.zoom='2'`，再把 viewport 宽高同时翻倍，截图就是 2x。高度先用 `document.body.scrollHeight`/`scrollWidth` 量，翻倍后 +4 防边缘裁切。

```js
document.body.style.zoom='2';
// 随后 POST /tabs/{id}/viewport {width: w*2, height: h*2+4}
// GET  /tabs/{id}/screenshot → 1960px 宽的 PNG
```

- 每渲完一张要 `zoom='1'` 复位，否则下一张跟着放大。
- **渲完必须用 vision 复核，别信“代码写对了”**：实测常见三类问题——树状图缺横向连接线（`::before` 只画了竖线没画横线，两个子节点悬空）、卡片底部留白不齐（内容行数不同，需 `display:flex;flex-direction:column` + `margin-top:auto`）、多卡里只有一张被高亮导致视觉重心跑偏（除非确有强调意图，否则统一配色）。

## 二进制文件下载（PDF／附件，实测可用）

Cloudflare 站（PNAS／NEJM／Science）的 PDF 用 curl 直接取回 403。可用路径只有一条：**在已放行的页面上下文里 fetch 成二进制字符串，分片 btoa 回传本地拼接**。`GET /tabs/{id}/downloads` 与 anchor `download` 属性都不可用（回 410 `browser_restarted`，即使刚建 tab）。

1. 先把**文章 HTML 页**导航到放行（`document.title` 不含 `Just a moment`）——PDF 预览页本身 evaluate 受限，别在 PDF 页里跑脚本。
2. 每片一条 evaluate（**片内重新 fetch + 切段**，因为 evaluate 之间 window 状态不保留）：

```js
(async()=>{const r=await fetch('/doi/pdf/<DOI>',{credentials:'include'});
const blob=await r.blob();
const text=await new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result);fr.onerror=()=>res('ERR');fr.readAsBinaryString(blob);});
const part=text.slice(OFF,OFF+59994);            // 59994 是 3 的倍数
return JSON.stringify({total:text.length,b64:btoa(part)});})()
```

3. 本地 `"".join(parts)+padding` 后 `base64.b64decode` 写文件；首页应为 `%PDF-1.x`、尾部 `%%EOF`，再用 pypdf 验页数（`PdfReader(p).pages`）。

坑（都实际踩过）：
- **别碰 typed array**：`s[i]`／`String.fromCharCode.apply(null, subarray)` 会在 camofox 的隔离世界里报 `Permission denied to access property "constructor"` 或 `Accessing TypedArray data over Xrays is slow, and forbidden`——只能走 `blob()` + `FileReader.readAsBinaryString()`。
- **一次返回整个文件必 500**：单次 evaluate 的返回值有上限，2MB PDF 直接 btoa 会 500；按 60KB／片切（≈80KB base64），2MB 约 35 片，每片重新 fetch（总传输翻倍但稳）。
- **分片必须按 3 字节对齐**再 btoa，否则拼接后 base64 错位；每片 `rstrip('=')`，最后统一补 padding。
- **窗口变量不跨 evaluate**：`window.__u8 = ...` 下一次 evaluate 就是 undefined，别写「先存后切片」的两段式。
- **`Range: bytes=0-59993` 不一定被尊重**，且读 `content-range` 头会连带 500；要小流量就靠切段而不是 Range。
- 下载前先判 OA，别把付费墙页面存成「PDF」：查 `api.openalex.org/works/doi:<DOI>` 的 `open_access`／`api.semanticscholar.org/graph/v1/paper/DOI:<DOI>?fields=isOpenAccess,openAccessPdf`；OA 才取，非 OA 在汇报里写明付费墙、不硬拉。


## 关键坑（全部实测踩过）

- **首次 navigate 偶发 500**（浏览器唤醒竞态）：失败后 sleep 3s **重试一次**即成功；脚本里 `fetch()` 统一做 2 次尝试再 fallback curl
- ⚠️ **navigate 连续 500 的完整重试模式（2026-08-25 ytview 卡死教训）**：唤醒竞态可能连续 500 多次（首次唤醒后马上跑批量最易触发），且默认 timeout 90s/条会让整批静默卡 30 分钟（log 无输出、进度为 0）。**批量脚本标准写法**：① navigate timeout 收到 45s；② `for attempt in range(3)` 循环——失败 `time.sleep(3)` + `tab=None` + 重建 tab 再试；③ 每进程限批（20 条内）+ bash 循环外层调用（`fix_yt_views.py 20` + ytview_loop.sh）——单进程跑 200 条一旦卡住无产出还占着 camofox；④ 首轮完成后 tail log 验证有进度（"补齐 N/20"），>2 分钟无 log 即怀疑卡死，手动单条 probe 定位
- **tab 可能失效**：navigate 抛异常时 `self.tab = None` 强制重建 tab 再试
- **evaluate 返回结构**：结果在 `result` 字段（不是 `value`/`data.result`）
- **RSS/XML 兼容**：浏览器渲染 XML 文档后 evaluate outerHTML 返回原始 XML 文本（ScienceDaily RSS 60 item 实测 OK）——parse 直接用 `ET.fromstring`
- **RDF/RSS 1.0 命名空间坑**（NEJM etoc 是 RDF 格式）：`root.iter("item")` 不匹配命名空间标签 → 用 `el.tag.split("}")[-1]` 取 local name 再匹配 item/title/link/pubDate
- **礼貌节奏**：脚本内请求间隔 ≥3s（浏览器也要低频）
- ⚠️ **复用同一 tab 连续 navigate 会突然全回 400**：不是 URL 有问题，是 tab 失效——**每条 URL 新建 tab**（或导航失败立刻重建）比「同 userId 复用 1 个 tab」稳。`/health` 的 `activeTabs` 涨到两位数后 navigate 也开始回 400/500；`DELETE /tabs/{id}?userId=<uid>` 要求 userId 对得上、清不干净时直接 `launchctl kickstart -k gui/$(id -u)/com.mednews.camofox` 重启（恢复 `activeTabs:0`），别在 400 上反复重试
- ⚠️ **Cloudflare 挑战要轮询 30-70 秒，别拿第一次 evaluate 判失败**：JAMA／Science／Nature 类站点首屏是 `Just a moment...`，navigate 返回 `httpStatus:403`、`navigationOk:false` 但页面会自己放行。做法：navigate 后每 5 秒 evaluate `document.title`，含 `Just a moment` 就继续等（最多 12-14 轮，约 60-70 秒）；放行后再读 `meta[name=citation_publication_date]`／`meta[name=citation_doi]`／JSON-LD `datePublished`。放行后仍只剩站名或 cookie 墙（如 science.org）＝这条取不到，换同题可核验源，不推测字段
- **输出里可能有进度行**（如 `Fetching...`）——JSON 解析用 `out[out.find("{"):out.rfind("}")+1]` 截断
- ⚠️ **headless 也会出声（2026-08-25 用户投诉）**：camofox 是 headless Firefox（`-headless` 启动），但打开 YouTube 视频页**照样外放声音**（headless 不自动静音）。**导航后立即 evaluate 静音**：`document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})`（navigate 返回后立刻执行，抢在视频自动播放前）。没有 API 级 mute 配置（/config 等端点全 404），只能 JS 层静音
- ⚠️ **用完关 tab**：`DELETE /tabs`（集合）确实 404，但 **`DELETE /tabs/{tabId}?userId=<同 userId>` 有效**，单条脚本结束时对每个 `tabId` 调一次，`/health` 的 `activeTabs` 就不会堆积（批量循环里每轮都关）。只有服务真的卡死（全端点 500/404）才需要重启：launchd 托管时 `launchctl kickstart -k gui/$(id -u)/com.mednews.camofox`；手工场景 `pkill -f camofox-browser` + `pkill -f "Camoufox.app/Contents/MacOS/camoufox"` → `~/.local/bin/camofox-browser` 后台（**别再用 `npm start` / `node server.js`**——官方包没有那个目录/入口，见下方"验证过的修复"）→ curl /health 验证 `activeTabs:0`。日常防卡死可配每小时看护脚本（/health 的 `browserRunning` 为 false 或 `activeTabs>=5` 就 kickstart）

- ⚠️ **服务重启 + 开机自启**：服务本体 = 官方 npm 包 `@askjo/camofox-browser`（可执行 `~/.local/bin/camofox-browser`，默认监听 9377）；plist 的 ProgramArguments 直接指向该绝对路径，**不要再写 `node <目录>/server.js` + WorkingDirectory**（换机后目录不存在 → exit 78）。已配 launchd 自启：`~/Library/LaunchAgents/com.mednews.camofox.plist`（RunAtLoad + `KeepAlive SuccessfulExit=false` 非正常退出自动拉起；日志 /tmp/camofox.log）。**流水线依赖 camofox 时先确认 /health**（`browserRunning:true`）——launchd 拉起需要几秒，批量任务前健康检查是标准动作；重启命令见上文（pkill camofox-browser 后重新启动 `~/.local/bin/camofox-browser`，或 `launchctl kickstart -k`）
- ✅ **验证过的修复（2026-09-21 实机跑通）——装官方 npm 包，别翻旧机 tar、别 clone 同名仓库**：
  ```bash
  export PATH="$HOME/.hermes/node/bin:$PATH"
  npm install -g --allow-scripts=@askjo/camofox-browser,better-sqlite3 @askjo/camofox-browser
  ~/.local/bin/camofox-browser   # 默认监听 9377，无参数
  ```
  - **必须带 `--allow-scripts=...`**：npm 默认拦截 postinstall（下载 Camoufox 浏览器）与 better-sqlite3 的 node-gyp 编译——不带就是"装完了但起不来"
  - npm 全局前缀是 `~/.local`（`npm prefix -g`）：包在 `~/.local/lib/node_modules/@askjo/camofox-browser`，**命令在 `~/.local/bin/camofox-browser`**（不在 `~/.hermes/node/lib/...`）；浏览器二进制落在 `~/Library/Caches/camoufox/`
  - **别用 `--help` 探测**——它不是 CLI，会直接起服务并挂住；要验证就 curl `/health`
  - 认 npm scope 包 `@askjo/camofox-browser`。GitHub 上同名第三方仓库是 TS 工程（需 tsc 构建 + better-sqlite3 原生编译易失败），端点契约也不一致，白折腾
  - 装前若 launchd 里已有旧服务，`launchctl bootout`/unload 再 `load` 新 plist
- ⚠️ **抖音互动数据未登录拿不到（2026-08-25 实测）**：未登录打开 `douyin.com/video/<id>`，视频详情区（点赞/评论/播放/发布时间）**不渲染**——`data-e2e` 元素只有导航栏（douyin-navigation/searchbar 等 68 个全是导航）、`window._ROUTER_DATA` 不注入、滚动触发/等 12s 都没用；`iesdouyin.com/share/video/<id>` 移动端页也跳回网页版同样不渲染。**标题/描述能拿到**（SSR），互动数据必须登录 cookie 注入才能抓（用户未提供时接受缺失，标注"未登录"）。redfox 抖音搜索也覆盖不了被限流的账号（论文辅导/SCI速成类被抖音搜索降权，翻 100 条都没有）——这类账号只能用户丢链接 + 登录态才能抓全

## 现成实现（复制即用）

- `~/.hermes/scripts/mednews_daily.py` 的 `CamofoxClient` 类（navigate 失败重建 tab + readyState 轮询 + 2 次重试）
- `~/.hermes/scripts/bili_daily.py` 的 `CamoFox` 类（B站搜索页提取版）
- `~/.hermes/scripts/fix_yt_dates.py` + `ytfix_loop.sh`（YouTube 视频页抓发布日期：navigate→立即静音→提取 `#info-strings yt-formatted-string` 的 "Premiered on Aug 20, 2026"→bash 循环每进程 20 条防杀→循环尾部关 tab）
- `~/.hermes/scripts/fix_yt_views.py` + `ytview_loop.sh`（YouTube 视频页抓播放量：选择器 `ytd-video-view-count-renderer span, .view-count`，文本 "137 views" 格式，正则 `([\d,\.]+)\s*([KMB]?)\s*views` 换算 K/M/B→整数）
- `~/.hermes/scripts/youtube_camofox_sync.py`（**YouTube 每日抓取 camofox 版，替代 redfox**：搜索页 `results?search_query=` 提取列表 → 对本地库新增的打开视频页补绝对日期/播放量/频道主页 → 直写本地 SQLite + LLM 打标。8 个英文医学关键词 + MED_KW 过滤。用户 2026-08-25 拍板 YouTube 弃 redfox 改 camofox 直抓——redfox youtube 接口无播放量、日期只有相对时间）

## 使用决策

- 网页站（有反爬风险）：**全部走 camofox**（NEJM 教训：curl 抓 RSS 也会被封 IP）
- 公开 API（medRxiv api.biorxiv.org / B站 view 接口）：免登录低频直连即可，不需要浏览器
- curl 仅作 camofox 挂掉时的最后兜底（fallback）
- **YouTube 数据抓取（2026-08-25 实测）**：camofox 免登录打开 `youtube.com/results?search_query=<kw>` 搜索页，`ytd-video-renderer` 提取 标题/链接/播放量/频道——**免费替代 redfox youtube API（¥0.03/次）**；精确发布日期需打开视频页抓（见 fix_yt_dates.py）
- ⚠️⚠️ **搜索型抓取必须按发布日期过滤窗口（2026-08-26 用户批评教训）**：YouTube 搜索按**相关性**排序（非最新）——医学关键词会搜出 2015-2016 年老教程视频，医学过滤后全入库=垃圾。**视频页日期提取必须用 `querySelectorAll('#info-strings yt-formatted-string, ytd-video-primary-info-renderer #date')` 全部拼接**（`querySelector` 单取第一个元素会拿到观看次数不是日期→全 None）；解析出日期后**>30 天丢弃、解析不出丢弃**（不要信任搜索排序）。适用于任何平台"抓最新内容"的搜索型抓取
- ⚠️ **能强制时间排序就别用相关度排序（2026-09-07 实测）**：YouTube 搜索 URL 加 `&sp=CAISBAgEEAE%3D` 即按上传时间排序，新视频排在最前；不加时新视频长期沉在相关度排序后面 → 连续多日"累计新增 0"被误判成"平台就是没新内容/真空窗"（实际是漏抓）。**任何搜索型源都先问一句：URL 能不能带"按时间排序"参数**

## 相关

- B站免 cookie 抓取细节：bilibili-api-scraping（camofox 搜索 + view 免登录）
- 医学资讯每日管道：medical-news-scraping
