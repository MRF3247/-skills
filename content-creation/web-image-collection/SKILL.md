---
name: web-image-collection
description: "从 Pinterest 等图库批量搜集参考图时使用：风控绕过、CDN 大图下载、断点续传。"
version: 1.0.0
metadata:
  hermes:
    tags: [image, collection, pinterest, scraping, playwright]
---

# 网页图库批量采集 (web-image-collection)

从 Pinterest 等图库网站按关键词批量搜集参考图（小红书/B站/视频号视觉参考、素材库积累）。产出可直接进 `visual-reference-pipeline`（本地资源库/浏览器采集 → 去重 → 识别 → 归档）。

## Pinterest 采集（已实测可用，未登录）

脚本：`/Users/Jin/Documents/Hermes/pinterest_daily.py`
环境：`~/Documents/GitProgram/playwright-venv`（playwright 1.62+，chromium 已装）

```bash
~/Documents/GitProgram/playwright-venv/bin/python ~/Documents/Hermes/pinterest_daily.py
# 自定义关键词：--keywords "medical poster,anatomy art"
# 强制重下：--force
```

**关键点（都是实测踩出来的）：**
- **必须 `channel="chrome"` 用系统 Chrome**——默认 headless shell 会被 Pinterest 登录墙截断：页面正常 200、能拿到 60x60 缩略图但 `a[href*='/pin/']` 数量为 0、body 出现「登录以继续探索」。换 channel="chrome" 后 pins=30 恢复正常
- **pin 卡片选择器**：`a[href*='/pin/']` 内用 `a.querySelector('img')` 一个选择器同时取 href/src/alt——分开取两个数组再按索引配对会错位（页面还有 logo 等非 pin 图片）
- **大图下载**：搜索页只给 60x60/236x 缩略图，i.pinimg.com CDN 支持把路径段换成 `originals` 或 `736x`/`1200x` 直接拿大图；originals 偶发 403（部分图需 referer），自动回退 736x
- **跨关键词去重**：同一 pin 会出现在多个关键词结果里，用全局 seen set（按图片 hash 段）去重，否则清单重复计数
- **断点续传**：cache.json（按日）记录已完成下载，重跑跳过；原子写（tmp + os.replace）；单张下载失败隔离不影响整批
- **每关键词之间停顿 3s** 降低风控概率；未登录每关键词约 30 pin，12 关键词 × 每词 6 张 ≈ 60 张/天
- **输出**：`/Users/Jin/Documents/Hermes/Pinterest素材/YYYY-MM-DD/`（图 + 清单.md 含 pin 链接可追溯 + cache.json）

## 交接流水线

1. 图片 mv 到 `/Users/Jin/Documents/本地资源库/浏览器采集`（流水线入口）
2. 跑 `visual-reference-pipeline`：先 `python3 dedup.py` 查重（自动删 MD5 重复、疑似重复移出待确认）→ 识别 → 重命名 → 双语提示词 → 家谱文档 → 归档

## 替代方案：camofox-browser

`/Users/Jin/Documents/GitProgram/camofox-browser`（npm start → localhost:9377）是 Hermes browser 工具的底层服务，Firefox 内核 C++ 级指纹伪装，反检测比 playwright 更强，也能正常渲染 Pinterest（Hermes browser_navigate + snapshot 直接可用，带 element refs 和完整 pin 描述）。两个方案互为备份；camofox 是常驻服务，重启电脑后需手动 `npm start`。

## 通用图库采集模式（迁移到其它图源）

1. 先探测风控：headless 壳 vs 系统 Chrome 内核 vs 反检测浏览器，看哪个能过（症状：页面 200 但核心元素为 0）
2. 图片 CDN 常支持路径换尺寸拿大图（缩略图 URL 的尺寸段替换）；403 时回退小一档
3. 断点续传 cache + 原子写 + 单条失败隔离（见 skill: batch-pipeline-robustness）

## Canva 模板站采集（2026-08-07 实测全通）

Canva 小红书图文模板批量扒取：**免登录路径** `/rednote/templates/posts/`（用户给的 `canva.cn/s/templates` 要登录）；列表页懒加载 headless 不触发 → 从详情链接提取 templateId；图片从详情页 og:image 拿（**必须反转义 `&amp;`**，否则签名 URL 失效）；下载用「浏览器 btoa(url) 传回 → curl 直下签名 URL」最稳（base64 大结果会被持久化截断）。官方主题分类归档（20 主题 fTheme 参数 + 官方确认/语义推断双来源标注）见 references/canva-template-scraping.md；完整流程、限流对策（每批 10 个 + 重试 3 次）、素材库归档结构（`Documents/素材/小红书模板/`）、以及**医学/论文/学术主题筛选**（kimi code 纯视觉审核 + 不适合移入 `_待删除/` 不直接删）同见该文件。
