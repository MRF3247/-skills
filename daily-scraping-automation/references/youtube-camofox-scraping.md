# YouTube camofox 直抓要点（2026-08-26 实测，用户批评驱动的修复）

场景：每日抓取 YouTube 医学视频（关键词搜索 → 医学过滤 → 入库）。redfox youtube/searchVideo 缺发布时间（只有 "2 weeks ago" 相对时间）和播放量，必须二次补 → **改 camofox 直抓，一次拿全**。

## 抓取流程（youtube_camofox_sync.py 模式）

1. 搜索页：`https://www.youtube.com/results?search_query=<kw>` → 提取 `ytd-video-renderer, ytd-rich-item-renderer` 里的 vid/标题/频道/时长
2. 医学过滤（标题+频道命中 MED_KW）
3. 查本地库去重（链接 UNIQUE）——已存在跳过
4. **新增的打开视频页**（https://youtu.be/<vid>，navigate 重试 3 次防唤醒竞态 500）→ 一次拿全：发布时间 + 播放量 + 频道主页
5. 入库 + 打标

## 关键陷阱（都踩过）

### 1. 日期提取：必须 querySelectorAll 全拼接，不能 querySelector 取单个
```js
// ❌ 错误：第一个 #info-strings yt-formatted-string 是观看次数不是日期
const dtEl = document.querySelector('#info-strings yt-formatted-string');
// ✅ 正确：全部拼接再正则
let txt = '';
document.querySelectorAll('#info-strings yt-formatted-string, ytd-video-primary-info-renderer #date')
  .forEach(e => txt += ' ' + (e.textContent || ''));
```
后果：日期字段全 NULL（用户批评"发布日期没收录"），还得 fix_yt_dates 二次补。

### 2. 必须按日期过滤只收 30 天内
YouTube 搜索按**相关性**排序（不是最新）——医学关键词会搜出 2012-2024 的老教程视频，不过滤会全入库（用户批评"11 年前的稿件都爬进来了"）。
```python
pub = parse_date(det.get("txt") or "")
if not pub: continue            # 无日期 → 丢弃（保守）
if (datetime.now() - pub_d).days > 30: continue  # 超 30 天 → 丢弃
```
parse_date 支持：`2026-08-24` / `Aug 24, 2026` / `2026年8月24日` / `N days/weeks ago`（相对时间换算）。

### 3. 爬稿件时同时收录日期+播放量，不要分两步
播放量选择器：`ytd-video-view-count-renderer span, .view-count`（parse "1,234,567 views" → int）。频道主页：`#owner ytd-channel-name a`。日期/播放量/频道在**同一次视频页 evaluate** 里拿全——分开两步必然有一步没跑。

### 4. 老视频清理
已入库的脏数据：`DELETE FROM content WHERE 子平台='YouTube' AND (发布时间 < 30天前 OR 发布时间 IS NULL)`——实测清掉 157 条超期 + 68 条无日期。

### 5. 静音纪律（用户强调）
navigate 后立即 JS `document.querySelectorAll('video').forEach(v=>{v.muted=true;v.pause()})`；循环结束 DELETE /tabs 关 tab。

## 性能
- 首次全量：8 关键词 × 相关排序，每条视频页 6s → 40-60 分钟（可接受，一次性）
- 每日增量：30 天内新增 ~20-40 条 → 3-5 分钟
- 幂等：链接 UNIQUE，重跑只处理新增

## 验证方法
- 抓完查库：`SELECT COUNT(*) FROM content WHERE 子平台='YouTube' AND 发布时间 IS NULL`（应 0）
- 手动探测单条：camofox open 视频页 evaluate 打印 txt/views，确认选择器在当前页面结构下生效
