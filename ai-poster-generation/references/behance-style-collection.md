# Behance 医学视觉素材采集（2026-08-07 实测）

国外高质量医学/科学视觉的采集渠道，作为 Pinterest 之外的第二路。Behance 项目质量高（The Lancet 期刊封面、医学插画合集、科学海报、解剖图集、Biomedical Scientist 编辑插画），适合拓展风格库。

## 关键事实

- **无需登录**：搜索页 `https://www.behance.net/search/projects?search=<关键词 URL 编码>` 浏览器访问返回 200，结果完整（10,000+ 项目/热门关键词）。
- **Dribbble 202 响应**（反爬）不靠谱，Behance 优先。
- 搜索结果里混有 promoted 广告项目（非目标风格，如水果插画/电影海报），提取时注意 alt 筛选。

## 提取流程

1. browser_navigate 搜索页
2. browser_console 提取（**不能用 `article img` 选择器——懒加载后 DOM 变化会取空**，用全页 img + 域名过滤）：
   ```js
   (() => {
     const imgs = Array.from(document.querySelectorAll('img'));
     const seen = new Set();
     const out = [];
     for (const i of imgs) {
       const s = i.src || '';
       if (s.startsWith('http') && s.includes('mir-s3-cdn-cf.behance.net/projects/') && !seen.has(s)) {
         seen.add(s);
         out.push({alt: (i.alt || '').slice(0, 40), src: s});
       }
     }
     return JSON.stringify({count: out.length, items: out});
   })()
   ```
   一次约 24 个/页。排除 ribbon/badge 图标（`a5.behance.net` 域名）。
3. 下载：把 JSON 喂 `python3 /Users/Jin/Documents/Hermes/behance_collect.py "<JSON>" [输出目录]`

## URL 规律

- 缩略图：`https://mir-s3-cdn-cf.behance.net/projects/404/<hash>.<ext>`（404 是裁剪预览，~400px）
- 原图：`/projects/404/` → `/projects/original/` 替换，已验证有效（`curl` 带 UA 直接下，不需要 cookie）
- 例外：个别项目 URL 直接就是 `/projects/original/`（老项目），无需替换

## 超长图回退（重要）

Behance 项目封面常是**整个作品集的竖排长图**（如 1400×11176 = 一张图包含所有作品）。直接入参考库会污染。规则：
- 高 > 4000px 或 高宽比 > 3.5 → 回退缩略图版（`/projects/404/`，已是正方形裁剪预览）
- behance_collect.py 已内置此逻辑

## 实测批次（2026-08-07）

- `medical illustration`：24 张（Lancet 封面、医学插画合集、Biomedical Scientist、Science illustrations 等）
- `scientific poster design`：17 张（Zion 生物多样性海报、Neurology poster、DRUGS POSTER、Epitaphium 解剖图集、Neuroimaging 编辑插画）
- 落盘：`Hermes/Pinterest素材/2026-08-07_国外医学画风拓展/behance/`（01_ 起编号 + alt 清理文件名）

## 工具沉淀（DRY）

`Hermes/behance_collect.py`（2026-08-07 从 4 个 /tmp 一次性脚本合并正式化）：
- 用法：`python3 behance_collect.py "<JSON>" [输出目录]`（JSON = [{alt, src}]）
- 功能：404→original 替换、超长图回退、断点续传（同名跳过）、py_compile + 真实调用验证通过
- 同类教训：会话中反复用的采集/转换逻辑直接沉淀为常驻工具（如 `Hermes/kimi_see.py`），不要每次重写 /tmp 脚本——既符合 DRY，也避免「已删临时脚本」反复触发验证。
