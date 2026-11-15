# Canva 模板站批量采集（2026-08-07 实测全通）

目标：把 Canva 的小红书图文模板示意图批量扒下来存素材库。用户给的是 `canva.cn/s/templates?...` 链接——**该路径要登录**，但 Canva 有免登录的模板分类页，内容更精准。

## 免登录路径（关键）

- ❌ `https://www.canva.cn/s/templates?query=...` → 弹出登录遮罩，无内容
- ✅ `https://www.canva.cn/rednote/templates/posts/` → 小红书帖子模板分类页，**免登录**，10,096 个模板，21 页
- ✅ `https://www.canva.cn/templates/?query=xxx` → 通用搜索页也免登录（但搜 xiaohongshu 返回的是英文名片/公告，不准）
- 分页规律：`?continuation=50` / `?continuation=100` ...（每页 50 个）
- 子分类：`/rednote/templates/red-covers/`（小红书封面）、`/rednote/templates/videos/`（社媒视频）
- 页面内嵌 SSR HTML：模板名称（alt）+ 详情页 URL 都在快照里；每页 50 个模板、价格标签（免费/高级版）也标注

## 懒加载陷阱（headless 必踩）

列表页模板图是 IntersectionObserver 懒加载：headless 里 scrollTo 不触发，**img.src 全空**（只有 10-11 张初始图有 src）。别死磕懒加载——**从详情链接提取 templateId**：

```js
// 每页 50 个模板 id + alt 名称
const links = Array.from(document.querySelectorAll('a[href*="/templates/EA"]'));
const seen = new Map();
for (const a of links) {
  const m = a.getAttribute('href').match(/\/templates\/(EA[A-Za-z0-9_-]+)\//);
  const img = a.querySelector('img');
  const alt = img ? img.alt : '';
  if (m && !seen.has(m[1])) seen.set(m[1], alt);
}
```

模板 id 形如 `EAHJPAfo1kM`（EA 开头 + base64 字符）。

## 图片 URL：详情页 og:image（签名 URL）

模板缩略图在详情页 `<meta property="og:image">` 里：
`https://template.canva.cn/{id}/N/0/299w-{hash}.jpg?X-Amz-...签名参数`（299×400，小红书 3:4）

**必须反转义 HTML 实体**：meta content 里 `&` 是 `&amp;`，直接 fetch 会返回 `application/xml` 的 `AuthorizationQueryParametersError`（签名参数被破坏）。反转义：

```js
const ta = document.createElement('textarea'); ta.innerHTML = m[1]; const url = ta.value;
```

详情页还白送：尺寸（1242×1660 标准小红书）、**配色 hex 值**、**字体列表**——都是超高价值素材。

## 下载：两条路径

**路径 A（浏览器 fetch → base64 → 落盘）**：可行但大结果会被 hermes 持久化输出**截断**（base64 长度非 4 倍数 → `Incorrect padding`，重复抓还会随机截断）。适合少量图。

**路径 B（推荐，稳定）**：浏览器只提取 og:image URL → **btoa 编码传回**（避免特殊字符截断）→ Python 解码 → **curl 直接下载**。S3 签名 URL 在 query string 里，curl 不需要 cookie（之前 403 是手改 URL 签名失效，不是反爬）。urlB64 提取：

```js
const urlB64 = btoa(unescape(encodeURIComponent(url)));
```

```python
url = base64.b64decode(urlB64).decode()
subprocess.run(["curl", "-s", "--max-time", "30", "-o", fname, url])
```

**注意 blob.type 不可靠**：部分模板 og:image 返回 `application/octet-stream`（不是 image/jpg）但数据是有效 JPEG——不要用 `blob.type.includes('image')` 当唯一判据，看字节头 `FFD8FF` 或直接存盘验证。

## 批量限流对策

连续 fetch 20 个详情页会触发临时限流（og:image 提取正常但图片 fetch 返回 application/xml，或直接空返回）——**不是模板问题**，单独重试同一张必成功。对策：
- 每批 10 个（20 个会超时：console 30s read timeout）
- 间隔 1-1.5s，失败自动重试 3 次（间隔 2-3s）
- 顽固失败的（重复截断/octet-stream 误判）最后单独用路径 B 补

## 素材库归档结构（用户定义）

用户说「素材库」= 他保存字体、表情包的文件夹 = `/Users/Jin/Documents/素材/`。本次建成：

```
素材/小红书模板/
├── 00_素材库索引.md
├── Canva小红书图文模板/   # 150 张（清单 _清单_p1~3.json + 00_索引.md）
├── 排版样图/<分类>/      # 165 张，19 类（按文件名前缀：审美提升/构图方式/12种封面...）
└── 视觉风格样图/<家族>/  # 340 张，11 家族
```

- 排版样图按文件名前缀分类（`审美提升_01.jpg` → 审美提升/）
- 视觉样图按**家谱文档表格的 alt** 分类（alt 无扩展名，用扩展名探测循环匹配源文件：`.jpg/.png/.webp/.jpeg/.gif`，gif 容易漏）

## 素材库路径备忘

- `/Users/Jin/Documents/素材/` = 字体（23 组）+ 表情包 + 小红书模板（本次新增）
- 工具脚本留在 `素材/小红书模板/Canva小红书图文模板/`：save_canva_b64.py（base64 落盘，容错跳过坏数据）、canva_save_images.py（备用）

## 官方主题分类归档（用户要求「按官方分类放好」）

Canva 官方分类维度 = 筛选栏的「主题」（用途类：分享/宣传/活动/招聘/促销/培训/招生/祝福/介绍/庆祝/聚会/公益/开业/比赛/婚礼/感谢/讲座/会议/交流/邀请，共 20 个）。模板列表页 HTML 的 script 里能直接 grep 到全部枚举值。

**URL 规律**：`/templates/?category=tAEUgd5tLWo&fTheme=THEME_XXX`（category 参数来自用户分享链接 `adj=` base64 解码；`category=tAEUgd5tLWo` 即「小红书帖子」分类）。fTheme 枚举：`THEME_SHARE/PROMOTE/EVENT/RECRUITMENT/SALE/TRAIN/ENROLLMENT/BLESS/INTRODUCE/CELEBRATE/REUNION/GOOD/OPENING/COMPETITION/WEDDING/GRATEFUL/LECTURE/MEETING/COMMUNICATE/INVITE`。翻页与列表页一致（`&continuation=50`）。

**抓取分类页 id**：fetch 分类页 HTML → `html.matchAll(/\/templates\/(EA[A-Za-z0-9_-]+)\//g)` 去重提取。浏览器内一次最多 3 主题 × 4 页（60 次 fetch 会 30s 超时）。

**关键认知（勿再浪费时间翻页）**：官方主题筛选页只覆盖**打了主题标签的模板**——从全量热门列表抓的 150 张里仅约 1/3（54 张）出现在任意主题页前几页，其余 96 张翻 8-10 页也找不到。**主题标签不是全覆盖维度**（还有风格/行业/格式等维度，且很多模板根本没打标签）。

**最终方案**：官方确认（54 张，出现在官方主题页）+ 语义推断（其余按模板名关键词归入官方 20 主题）+ 索引标注来源（「官方确认」/「语义推断」），归档脚本 `canva_classify_v2.py`（含关键词表 + 来源标注 + 01_主题分类索引.md 生成；幂等可重跑）。归档结构：`Canva小红书图文模板/主题/<官方主题名>/`。10 个分类实际用上（分享 70/培训 21/宣传 19/介绍 16/活动 8/招生 5/祝福 4/招聘 3/促销 2/通知 2），「通知」是语义推断补充的关键词类（官方无此主题，可并入宣传/公告类）。

## 医学/论文/学术主题筛选（kimi code 视觉审核，2026-08-07）

用户要求「用 kimi code 检查哪些图适合医学/论文/学术主题，不相干的删掉」。**关键纠正：从视觉风格角度判断，不读图里文字**（用户原话：「从视觉风格的角度来分析哈，不是说让你提取文字什么的」）。判断依据是视觉元素：医学插画/解剖/细胞分子图形、DNA/基因/科研图标、科学图表/数据可视化、学术海报版式、复古医学图谱、实验室/手术/显微镜场景、极简专业排版、学术期刊封面气质。不适合：风景/美食/美妆穿搭/卡通萌宠/娱乐拼贴/婚礼庆典/运动健身/儿童涂鸦等视觉题材。

工作流（脚本在 `Canva小红书图文模板/`）：
- `kimi_canva_filter.py`：逐张调 kimi code k3-256k，prompt 要求「只看视觉风格，不读文字」，输出 JSON `{"suitable": bool, "reason": "视觉理由"}`；结果落 `_筛选结果.json`（断点续传，后台跑）
- **安全删除原则：不适合的移到 `_待删除/` 文件夹，不直接 rm**（用户确认后再彻底删，防误删不可恢复）
- `apply_canva_filter.py`：移动 + 生成 `02_筛选清单.md`（✅适合 / ❌不适合含理由 / ⚠️解析失败待补跑）
- 常见失败：kimi 偶发空返回（解析失败）——单张重跑即可；批量 150 张约 40-60 分钟（每张 10-60s）


