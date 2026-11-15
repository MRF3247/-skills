# MedHOT 全量取数（Postgres，别用 /hot）

## 为什么不能用本地 API

`http://127.0.0.1:3001/api/site/hot` 只返回 **Top 10 精选排行榜**（`/api/site/stories`、`/latest`、`/daily` 全是 404）。拿它当日更素材，用户一眼就知道漏了条目。

2026-10 实测体量：10 天窗口内 `articles` 有 ~1400 篇、`analyses.selected` 为真的故事 **≤60** 个、单个 daily 日报 13 件大事＋10 条快讯。

## 连接

```bash
/Users/Jin/pgsql/16/bin/psql -h 127.0.0.1 -p 5433 -U postgres -d medhot
```

## 表结构与语义

| 表 | 关键列 | 说明 |
|---|---|---|
| `stories` | `id, public_id, title, status, **merged_into**, latest_at, digest, latest, summary` | 一条新闻事件（多源报道合并后）。去重列是 `merged_into`（带 d），写 `merge_into` 会直接报 `column "merge_into" does not exist`| 
| `story_signals` | `story_id, article_id, source_id, kind, observed_at` | 故事 ↔ 文章 的关联表（**没有 `fact_articles.story_id`**，别写错）|
| `articles` | `id, url, title, published_at, excerpt, body_text, source_id` | 单篇文章 |
| `analyses` | `article_id, selected, score, category, relevance, tags` | AI 打分；`selected=true` 才是站上“精选” |
| `sources` | `id, name` | 媒体名 |

**`stories.summary` 绝大多数是 NULL，有事实的是 `stories.digest`**（一段中文摘要＋关键数字），其次 `articles.excerpt` / `body_text`。写文案的材料按 digest → excerpt → body_text 顺序取。

## 取一个窗口内的全部候选（含多源合并）

```sql
-- 时间窗用 Asia/Shanghai 的日期算，和表里的「原文发布日」对齐
with s as (
  select st.id, st.public_id, st.title, st.digest, st.latest, st.latest_at,
    (select json_agg(json_build_object(
        'url', a.url, 'title', a.title, 'src', coalesce(src.name,''),
        'pub', a.published_at, 'score', an.score, 'sel', an.selected))
       from (select distinct article_id from story_signals where story_id=st.id) ss
       join articles a on a.id=ss.article_id
       left join sources src on src.id=a.source_id
       left join analyses an on an.article_id=a.id
      where an.selected) as arts
  from stories st
  where st.merged_into is null
    and st.latest_at >= '2026-10-09 16:00+00'   -- = 北京时间 10-10 00:00
)
select json_agg(s) from s where arts is not null;
```

只要摘要/正文时（不关心是否有文章链接）：

```sql
select json_agg(json_build_object('id',s.id,'title',s.title,'digest',s.digest,
  'ex',(select left(a.excerpt,700) from story_signals ss join articles a on a.id=ss.article_id
         where ss.story_id=s.id order by a.published_at desc limit 1),
  'bod',(select left(a.body_text,2000) from story_signals ss join articles a on a.id=ss.article_id
         where ss.story_id=s.id order by a.published_at desc limit 1)))
from stories s
where s.merged_into is null and s.latest_at >= '2026-10-09 16:00+00';
```

输出用 `-tAc` ＋ `json_agg`，直接落到 `/tmp/xxx.json` 再用 Python 处理；别在 shell 里拼长 SQL 字符串（引号会被吃掉，`null` 输入 JSON 会直接报 `invalid input syntax for type json`）。

## 与目标表去重

一个 story 常常对应 4 篇报道（FDA 新闻稿＋Medscape＋MedPage…），**在 DB 里已经合并成一个 story，不要再按文章数去重**。跨表去重用三道：

1. URL 完全相等（规范化：去 `www.`、去 query、小写、去尾 `/`）；
2. 标题 token 交并比（英文词 ≥4 字符 + 中文二元组，`len(交集)/len(已有标题token) > 0.28` 即视为同一条）；
3. DOI 相等（两边都推得出来时最可靠）。

⚠️ 标题相似度会把不同故事误合（“直肠癌 dMMR 获批” vs “结肠癌 dMMR 获批”），判定为重复时**回头确认一下是哪条记录命中的**，别直接删候选。

## 代表链接的选择

每个 story 的 `arts` 里挑一条做 `来源链接`，优先级（越靠前越适合作截图对象）：`FDA 新闻稿 > NEJM / Nature / Nature Medicine / Nature Biotechnology / The Lancet / JAMA > Medscape > MedPage Today`。监管类优先官方新闻稿；有 DOI 的论文页优先于二手报道。

## 站点静态快照（备用）

`https://mrf3247.github.io/medhot/` 的 `sitemap.xml` 有 500 个 `/story/` 页＋290 个 `/items/` 页；`/daily/<YYYY-MM-DD>/` 是日报，版面项锚点为 `aria-label="阅读<来源>原文：<标题>（新标签页）"` 的 `<a>`，前面紧邻的 `<p>` 是摘要。注意部分日期（周末）的日报是空壳（~43KB、无 `原文` 锚点），别当当天没有新闻。
