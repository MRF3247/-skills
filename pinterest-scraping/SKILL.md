---
name: pinterest-scraping
description: "Use when 需要从 Pinterest 搜集/下载图片素材（医学/科研/设计参考图等）。"
version: 1.0.0
metadata:
  hermes:
    tags: [pinterest, scraping, images, playwright, collection, reference]
---

# Pinterest 图片采集 (pinterest-scraping)

从 Pinterest 搜索并批量下载图片素材（医学论文海报、科研信息图、设计参考图等），用于小红书/B站视觉参考、素材库归档。**未登录即可工作**，每关键词约 30 个结果，单页无无限滚动。

## 环境与前置

- Playwright venv: `~/Documents/GitProgram/playwright-venv`（Python 3.11，playwright 1.62）
- **必须用系统 Chrome 内核**：`channel="chrome"`。系统 Chrome 位于 `/Applications/Google Chrome.app`。
- 若报 `Executable doesn't exist`：`~/Documents/GitProgram/playwright-venv/bin/python -m playwright install chromium`（下载 headless shell；但注意即使装了 headless shell 也不够，见坑 1）。
- 图片下载用 urllib + UA 头即可（无需浏览器会话），CDN 不校验 referer/cookie。

## 核心技巧

1. **搜索 URL**：`https://www.pinterest.com/search/pins/?q=<关键词 URL 编码>`，`domcontentloaded` + 等 5s。
2. **pin 链接 + 图片 + 描述一次取**（避免索引错位，页面里非 pin 的 img 如 logo 会混在 img 数组里）：
   ```js
   els => els.map(a => { const img = a.querySelector('img'); return {href: a.href, src: img ? img.src : '', alt: img ? img.alt : ''}; })
   ```
   选择器：`a[href*='/pin/']`，用正则 `/pin/(\d+)/` 去重。
3. **CDN 换尺寸拿大图**：搜索页拿到的是 `i.pinimg.com/60x60/<hash路径>.jpg`（或 236x），把路径段 `60x60/` 或 `236x/` 替换成 `originals/`（原图）即得大图；`originals` 偶发 403（新图/推荐图受限）→ 回退 `736x/`。已验证 1200x、originals 可用。
4. **断点续传**：按图片 hash 段为 key 存 cache.json，重跑跳过已完成；跨关键词去重（同一 pin 会出现在多个关键词结果里）；原子写（tmp + os.replace）。

## 快速使用

现成脚本：`/Users/Jin/Documents/Hermes/pinterest_daily.py`（技能内 scripts/pinterest_daily.py 为基线副本，以工作目录活版为准）

```bash
~/Documents/GitProgram/playwright-venv/bin/python ~/Documents/Hermes/pinterest_daily.py
# 自定义关键词 / 调整数量 / 强制重下：
# ... pinterest_daily.py --keywords "medical illustration,anatomy art" --max-per-keyword 8 --force
```

输出：`/Users/Jin/Documents/Hermes/Pinterest素材/YYYY-MM-DD/`（图片 + 清单.md[本地路径/Pin 链接/alt 描述] + cache.json）。默认 12 个医学/科研关键词，每关键词 6 张。

## 坑与规避

1. **headless shell 会被登录墙截断（本会话踩过的大坑）**：用默认 chromium（headless shell）访问搜索页，body 出现「登录以继续探索 Pinterest」，结果只剩 32 张 60x60 缩略图、`pins=0`（拿不到 pin 链接）。**改用 `channel="chrome"` 用系统 Chrome 后立刻恢复 pins=30**。这是 Pinterest 对 headless 指纹的动态风控，不是每次都触发（首访可能给完整版），判断标准：`a[href*='/pin/']` 数量是否为 0。
2. **个别关键词命中 0**：属正常（如 "medical infographic" 未登录无结果），不 panic，跳过继续。
3. **alt 描述**：60x60 缩略图 alt 多为空，236x 尺寸的图 alt 较全；描述缺失不影响下载。
4. **每关键词间停顿 3s**，降低被风控概率。
5. **不要擅自定义时任务**：用户规则「定时任务只在明确同意时用」——用户要求"每天搜集"时，先跑一次验证，再询问是否设 cron，不得默认排期。

## 验证

- 抽查 2-3 张下载图用 vision_analyze 确认内容与需求相关（本会话验证过：学术海报、How-to-Read-Scientific-Papers 信息图均对路）。
- 核对清单条目数 = 磁盘文件数（跨关键词重复会造成清单多于文件，此时看去重后是否相等）。

## 相关

- 批量管线健壮性模式（日志/失败隔离/续传/超时）见 skill: batch-pipeline-robustness。
- 采集后的图片整理（识别/重命名/双语提示词/归档 Obsidian）见 skill: visual-reference-pipeline。
