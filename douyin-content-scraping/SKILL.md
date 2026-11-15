---
name: douyin-content-scraping
description: 抖音博主主页图文/作品采集，未登录仅第一页，全量需扫码登录。
---

# 抖音博主内容采集（图文/作品）

用户会提供抖音主页链接（douyin.com/user/<sec_uid>）要求整理博主图文、保存运营相关内容。2026-08 实测完整路径如下。

## 反爬边界（实测 2026-08，别浪费时间重踩）

- **未登录 = 只有第一页**：`/aweme/v1/web/aweme/post/` 未登录只返回最新 24-38 个作品，翻页（max_cursor>0）一律返回 `{"status_code":0}`（17 字节空 body）。响应里 `not_login_module` 提示「看更多最新作品」——产品策略，不是签名问题。
- **PC 端页面未登录不加载作品流**（登录弹窗挡住，作品区为空；关了弹窗也不加载）。
- **m.douyin.com/share/user/<sec_uid>**：免签名白名单，但固定 15 个，滚动不翻页（reflow_source=reflow_page 忽略 max_cursor）。
- **iesdouyin.com 老接口**：`/web/api/v2/user/info/` 可用（用户信息：昵称/简介/作品数），`/web/api/v2/aweme/post/` 需 _signature 返回空。
- **curl 直连 API 需完整 cookie**：ttwid（ttwid.bytedance.com 注册接口可拿）+ __ac_signature（必须浏览器 JS 生成）→ 用 playwright 打开 www.douyin.com 等 7s 后导出 cookies。
- **a_bogus 签名**：纯 Python 旧版（Evil0ctal/dy-download-api abogus.py）和新版 JS（TikTokDownloader/static/js/a_bogus.js，never-jscore 执行）都只能过第一页——未登录翻页限制与签名版本无关。
- **全量必须登录**：playwright 有头弹窗让用户扫码，登录后作品流加载、滚动抓全（脚本见下）。

## 标准流程

1. **确认博主**：`iesdouyin.com/web/api/v2/user/info/?sec_uid=<SEC>` 拿昵称/简介/作品数（curl 即可）。
2. **免登录抓首屏**：playwright 拿 cookie + 新版 a_bogus + requests 调 `/aweme/v1/web/aweme/post/`（max_cursor=0），拿到最新 24-38 个（图文 type=68 通常占大头）。
3. **要全量**：跑扫码登录脚本（fetch_full_login.py），用户扫码后滚动抓全部作品。
4. **下载图文图片**：图文作品的 `images[].watermark_free_download_url_list`（无水印）→ 按作品建文件夹存原图 + meta.json。
5. **OCR 图内文字**：macOS 本地 Vision OCR（swift 脚本，中文准确、免费、批量）→ 每篇图文生成 markdown 笔记。
6. **分类归档**：按标题关键词分类（小红书运营/赛道分析/卖点文案/选题库/通用理念），生成 README 索引。

## 关键环境（本机）

- venv: `/Users/Jin/Documents/GitProgram/playwright-venv/bin/python`（已装 playwright、requests、gmssl、never-jscore）
- a_bogus JS: `/Users/Jin/Documents/GitProgram/tt-downloader/static/js/a_bogus.js`
- 参考实现: `/Users/Jin/Documents/GitProgram/dy-download-api/crawlers/douyin/web/`（abogus.py、web_crawler.py）
- 完整工作流脚本样板: `/Users/Jin/Documents/Hermes/抖音博主-谢无敌闪亮猫传媒/`（fetch_js.py 免登录首屏、fetch_full_login.py 扫码全量、download_images.py、ocr.swift、make_notes.py）
- 系统 python3.11 在 `~/.local/bin/python3.11`（pip 装包受 PEP668 限制，用 venv）

## 签名调用要点

- UA 必须与 a_bogus 生成时完全一致；推荐 Chrome 123 Windows UA：`Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36`
- 参数顺序：dict 顺序 urlencode，a_bogus 拼在 URL 最后
- never-jscore 调用：`JSEngine(js_code)` → `eng.call("generate_a_bogus", [url_params_str, ua])`
- 请求头要带 Referer: `https://www.douyin.com/user/<SEC>`

## OCR（macOS Vision）

```bash
swift ocr.swift <图片目录> <输出.json>   # 输出 {相对路径: [文本行]}
```
- 识别语言 zh-Hans + en-US，accurate 级别
- 一次进程处理整个目录（186 张约 1 分钟内）

## 单视频下载（yt-dlp + playwright cookie，2026-08-19 实测）

用户发单条视频链接（douyin.com/video/<id> 或 jingxuan 搜索页 modal_id）要求下载时：

1. **yt-dlp 直接跑必失败**（`Fresh cookies (not necessarily logged in) are needed`）——抖音 web 详情 JSON 需要新鲜 cookie。
2. **playwright 现取 cookie**（`/Users/Jin/Documents/GitProgram/playwright-venv/bin/python`，已装）：
   - headless 打开 `https://www.douyin.com/video/<id>`，`wait_for_timeout(8000)` 后 `ctx.cookies()` 导出。
   - **Netscape 格式两个坑**：① `expires` 是浮点必须 `int(float(x))` 取整，否则 yt-dlp 报 `invalid Netscape format cookies file`；② **domain 必须加前导点**（`.douyin.com`），否则同样报格式错。两坑都踩过，按顺序修。
   - 页面 title 可验证（如「豆包大笑 - 抖音」= 加载成功）。
3. **yt-dlp 下载**：`yt_dlp -f "bv*+ba/b" --no-playlist --cookies <file> -o out.%(ext)s <url>`。
4. **编码**：下载的 `bytevc1_720p` 标签实际是 **H.265 (hevc)**，ffmpeg 可正常解码（imageio-ffmpeg 提供二进制）。
5. **转 GIF 入库**：`ff -ss 1 -t 5 -i in.mp4 -vf scale=360:-1,fps=12 -loop 0 out.gif`（取精华片段），mp4 原片同目录保留（`<名>.mp4`），GIF 放 `素材/表情包/GIF动图/`，README 登记（来源链接用 douyin.com/video/<id>）。

## 陷阱

- 未登录翻页请求返回空 body 而非错误码——不要反复试签名版本，直接判定登录限制
- 抖音 web 参数里 `msToken` 传空串即可（首屏不校验）
- 图片 URL 有时效签名（x-expires），尽快下载
- 图文作品链接格式 `/note/<id>`，视频 `/video/<id>`
- aweme_type=68 且 images 非空 = 图文；type=0 = 视频
