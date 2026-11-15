# 从 MedHOT 库里挖一个话题的稿件：SQL 与命令配方

前置：`cd /Users/Jin/Documents/GitProgram/MedHOT && ./medhot.sh status`（会同时打印「稿件 N 条 / 已处理 / 精选 M 条」）。库没起就 `./medhot.sh start`。

```bash
PSQL=/Users/Jin/pgsql/16/bin/psql
$PSQL -h 127.0.0.1 -p 5433 -U postgres -d medhot -c "..."
```

## 相关表与字段（只记这几列）

- `articles`：`id` · `source_id` · `title` · `url` · `published_at` · `body_text`（整段单行）· `processing_state`（站点只展示 `analyzed` + `relevance=pass`）
- `analyses`：`article_id` · `relevance` · `selected` · `score` · **`title_zh`** · **`summary_zh`** · `reason_zh` · `category` · `tags` · `subjects` · `model`
- `facts`：`id` · `public_id` · `story_id` · `title` · `subject` · `action` · `object` · `occurred_at`
- `fact_articles`：`fact_id` → `article_id`（同一事件的报道集合）
- `stories`：`id` · **`public_id`** · `title` · `first_report_at`

## 1. 关键词一次铺开：先判「有没有」

```sql
select count(*) filter (where title ilike '%tucatinib%' or body_text ilike '%tucatinib%') as generic,
       count(*) filter (where title ilike '%Tukysa%'  or body_text ilike '%Tukysa%')  as brand,
       count(*) filter (where title ilike '%HER2CLIMB%' or body_text ilike '%HER2CLIMB%') as trial,
       count(*) filter (where title ilike '%图卡替尼%' or body_text ilike '%图卡替尼%') as zh
from articles;
```

通用名 / 商品名 / 试验代号 / 中文译名四路一起查。**中文那一路恒 0 是正常的**（库里几乎全是英文源），别据此回答「站上没有」。

## 2. 命中列表 + 中文分析结果

```sql
select ar.published_at::date as pub, ar.source_id, left(ar.title,95) as title, a.selected, a.score
from articles ar left join analyses a on a.article_id = ar.id
where ar.title ilike '%KEY%' or ar.body_text ilike '%KEY%'
order by ar.published_at desc limit 40;
```

要看模型写的中文标题/摘要就把 `a.title_zh, a.summary_zh, a.category, a.tags` 加进 select，并加 `-x` 竖排（摘要很长，横排会被 psql 折成不可读）。同一话题的相邻新闻（同期同一治疗领域的其他批准）用 `published_at > now() - interval '45 days' and (title ilike '%breast cancer%' ...)` 扫一遍，选题时能当对照背景。

## 3. 事件聚合：这件事有几篇报道

```sql
select f.public_id, f.title, fa.article_id
from facts f left join fact_articles fa on fa.fact_id = f.id
where f.id = <fact_id>;                -- fact_id 从标题命中 facts 得到
select s.id, s.public_id, s.title, s.first_report_at::date from stories s where s.id = <story_id>;
```

站内 URL 拼法：条目页 `/items/<article_id>/`、事件页 `/story/<stories.public_id>/`。发链接前用浏览器各开一次。

## 4. 取全文（`read_file` 不够用）

```bash
$PSQL ... -t -A -c "select body_text from articles where id='<article_id>';" > /tmp/art.txt
python3 -c "import textwrap;print(textwrap.fill(open('/tmp/art.txt').read().strip(),120))"
```

`body_text` 存成一行，`read_file` 只回开头约 1KB 且仍报 `truncated:false`——不要以为那就是全文。

## 5. 外链可用性：用浏览器，不用 curl 状态码

curl 的 404/403 **不能判定链接失效**：`fda.gov` 对 curl 回 404、药企新闻稿站与 Medscape 回 403，浏览器打开全部正常。批量粗筛可以用 curl，最终发出去的每条链接以 `browser_navigate` 打开确认为准。本机 TUN 代理下 `web_extract` 还可能回 `Blocked: URL targets a private or internal network address`（DNS 假 IP 段），同样改用浏览器。
