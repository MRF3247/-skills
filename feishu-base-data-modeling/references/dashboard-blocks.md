# 仪表盘 block：可复制模板与实测坑

前提：`+dashboard-block-create` 前必须知道 `dashboard_id`、组件 `name/type`、真实表名与字段名（`+table-list` / `+field-list`）。**组件必须串行创建**，不能并发。

## 已实测可用的 data_config

假设表名「公众号数据」，字段：记录类型（单选）/ 渠道（单选）/ 日期 / 周起始日（日期）/ 内容标题 / 阅读人数 / 分享人数 / 微信收藏人数 / 发表篇数。

指标卡（单指标 + 筛选；`number_format` 仅 statistics 支持）：

```json
{"table_name":"公众号数据","series":[{"field_name":"阅读人数","rollup":"SUM"}],
 "filter":{"conjunction":"and","conditions":[
   {"field_name":"记录类型","operator":"is","value":"渠道日趋势"},
   {"field_name":"渠道","operator":"is","value":"全部"}]},
 "number_format":{"formatName":"digital","precision":0}}
```

时序柱状图（x=周起始日，逐周求和）：

```json
{"table_name":"公众号数据","series":[{"field_name":"阅读人数","rollup":"SUM"}],
 "group_by":[{"field_name":"周起始日","mode":"integrated","sort":{"type":"group","order":"asc"}}],
 "filter":{"conjunction":"and","conditions":[
   {"field_name":"记录类型","operator":"is","value":"渠道日趋势"},
   {"field_name":"渠道","operator":"is","value":"全部"}]}}
```

两维拆解（x=周，系列=渠道）：`group_by` 数组第二项就是系列维度，最多 2 项。

```json
{"group_by":[{"field_name":"周起始日","mode":"integrated","sort":{"type":"group","order":"asc"}},
            {"field_name":"渠道","mode":"integrated"}],
 "filter":{"conjunction":"and","conditions":[
   {"field_name":"记录类型","operator":"is","value":"渠道日趋势"},
   {"field_name":"渠道","operator":"isNot","value":"全部"}]}}
```

多指标组合图（combo，`series` 可多个）：

```json
{"table_name":"公众号数据","series":[
   {"field_name":"分享人数","rollup":"SUM"},
   {"field_name":"微信收藏人数","rollup":"SUM"},
   {"field_name":"发表篇数","rollup":"SUM"}],
 "group_by":[{"field_name":"周起始日","mode":"integrated","sort":{"type":"group","order":"asc"}}],
 "filter":{"conjunction":"and","conditions":[{"field_name":"记录类型","operator":"is","value":"账号日指标"}]}}
```

排行榜（ranking）：单分组 + 单指标，排序只能写在 `group_by[0].sort`（`type` 仅 `value`），`limit_size` 默认 10。

```json
{"table_name":"公众号数据","series":[{"field_name":"阅读人数","rollup":"SUM"}],
 "group_by":[{"field_name":"内容标题","mode":"integrated","sort":{"type":"value","order":"desc"}}],
 "filter":{"conjunction":"and","conditions":[
   {"field_name":"记录类型","operator":"is","value":"内容来源"},
   {"field_name":"渠道","operator":"is","value":"全部"}]},
 "limit_size":10}
```

text 组件无数据源，只有 `text`（Markdown 支持标题/加粗/列表，**不支持链接、表格、代码块**）：

```json
{"text":"# 看板口径\n口径：自然周（周一至周日）。\n\n## 北极星\n1. **剔除爆款后的篇均阅读**\n2. **收藏 + 分享**"}
```

## 多账号 / 多数据源看板（大盘 + 每账号一条线）

一张图的 `data_config` 只认**一张表**，四个账号的数据分散在四张表时画不到一张图里。做法是建一张 helper 汇总表，再让图去读它。

1. helper 表用**长格式**，一账号一周一行：`记录名称` / `周`(text，如 `10/19`，横轴就用它，标签干净且 `group` 升序即时间序) / `周起始日`(datetime) / `账号`(select) / 各指标 number / `口径备注`。10 个 `+field-create` 塞一次 `+table-create --fields @./fields.json`（数组第一项即主字段）。
2. 一次 `+record-batch-create` 灌全部行（周×账号），从各源表按 `记录类型`/`渠道` 汇总后算好再写，别指望图里跨表 JOIN。
3. 多折线：两个 `group_by`——第一项=横轴，第二项=系列（图例）。`[{"周"},{"账号"}]` 就是「4 账号 × N 周」的 4 条线，`+dashboard-block-get-data` 应返回 4×N 行。
4. 指标在某平台根本没有（公众号无点赞/关注）时该行留 **null**，空值会被聚合排除，图例自然不出现那个账号——不要填 0（0 会被当成真实数据画成一条贴底直线），并在组件名里如实标「（小红书×2）」。但**重算脚本不得把人工补录过的字段回写成 null**，见下方「人工补录」。
5. 大盘合计卡的筛选按 `周` 文本 `is` 最新周标签（如 `10/19`）：周更时人要改这 4 张卡的 `value`，交付时把这条维护动作写出来；「本周」= 最新**完整**周，周一改版时本周刚开始，别拿半周数据当本周。
6. ranking 同样只能单表单指标；跨账号内容 TOP 榜要先有「内容明细」helper 表（账号/标题/周/阅读），否则只能出单账号榜——源表若只有少数几行「全部」渠道记录，榜单实际只有几条，交付时点名这是采集缺口而不是 bug。

## 大盘主线 + 每期分账号小柱（宽表 + combo）

长表画不出这个形态：长表一条记录只代表一个账号，而 `series` 只认字段，没法表达「合计一条线 + 分账号一组柱」。做法是再建一张**宽表**（一周一行）：`记录名称` / `周` / `周起始日` / `大盘` / 各账号各一列，由长表按周聚合生成，两张表用同一个脚本刷。

```json
{"table_name":"周阅读宽表",
 "series":[{"field_name":"公众号","rollup":"SUM"},
           {"field_name":"服务号","rollup":"SUM"},
           {"field_name":"小红书SciLink","rollup":"SUM"},
           {"field_name":"小红书刀客轻研","rollup":"SUM"},
           {"field_name":"大盘","rollup":"SUM"}],
 "group_by":[{"field_name":"周","mode":"integrated","sort":{"type":"group","order":"asc"}}]}
```

**飞书 combo 的柱/线由 `series` 顺序决定：第一个指标画柱，其余画线。** 所以「大盘一条折线 + 每个周节点四根并排小柱」必须把四个账号排前面、大盘排最后；反过来（大盘在前）会得到「大盘一根大柱 + 四账号四条线」，正好相反。改完刷新页面视觉确认一次，`ok:true` 只代表配置写进去了。

## 人工补录（后台导出拿不到的数）

平台导出里没有、用户会在附件字段贴后台页面截图的指标（公众号的赞 / 在看 / 留言 / 关注），**不要直接手改表记录**——重算脚本下一次就把它们冲掉。落到脚本目录的 `rollup_manual.json`，键是 `账号|周起始日`：

```json
{"公众号：刀客轻研|2026-10-19": {"赞":12,"在看":4,"评论":1,"来源":"微信后台「数据概况·最近7天」截图"}}
```

重算脚本合并后统一口径（公众号 `点赞 = 赞 + 在看`，小红书用原生点赞）。两条硬规则：源表没有的字段**跳过该 key 不写**（写 null 会清空人工值）；`口径备注`/`数据来源` 把截图来源追加进去。读截图用 `vision_analyze`：先整图定位，再 `region` 裁到指标行逐个数核对，最后用「阅读/分享」与表内同周合计对拍确认周窗口。

## 坑

- `table_name` 用**表名称**，不能用 `table_id`；字段名必须来自 `+field-list`。
- `series` 与 `count_all` 二选一，同传必报错。
- 「全部」汇总行和分渠道行同时存在时，拆解图里必须 `isNot 全部`，否则总额翻倍。
- `+dashboard-block-list` 的返回结构是 `data.items`（含 `total` / `has_more`），**不是** `data.blocks`；拿到 `block_id` 后 `+dashboard-block-get-data` 才能读图表的计算结果。
- `+dashboard-block-update` 不能改 `type`；要换图表类型只能删了重建。
- 布局：用户没给坐标就建完后 `+dashboard-arrange` 一次；`--position` 必须四个 key 齐全（`x/y/w/h`）。
- 浏览器预览看到空白 canvas + “This browser is not supported” 不代表图表错，用 `+dashboard-block-get-data` 判定——那才是图表真实算出的数字。
- **`text` 组件只建不改**：`+dashboard-block-update` 更新 text 会把正文二次编码（读回是带 `"` 的 JSON 串），且 CLI 会剥掉真换行（多行 Markdown 变一行、`\n` 字面量也不渲染）。口径说明写成**单行长串**用「｜」分段，要改就 `+dashboard-block-delete` 后 `+dashboard-block-create` 新建。
- **`+dashboard-block-update` 后立刻 `get-data` 可能返回旧配置的缓存结果**（行数、维度都对不上旧 config）。先 `+dashboard-block-get` 读回 `data_config` 确认已落库，等 1–2 秒再取数；把「图不对」当 bug 前先排除缓存。
- **改版已有看板优先复用旧块**：`type` 不能改，但同族图可原地换用途（旧 column「周阅读趋势」→ 新「本周各账号阅读对比」），省掉删建、保住用户可能还在看的块；`--position` 是 12 列栅格，`{"x":0,"y":0,"w":3,"h":2}` 四张卡铺满首行即是「大盘」。顶层 `data_config` 是 key 级合并，只传要改的 key。
- `+record-batch-create/update --json` **不吃 `@file`**：`--json @rows.json` 报 `positional arguments are not supported (got ["@rows.json"])`；payload 落盘后用 `--json "$(cat rows.json)"`。`+table-create --fields @./fields.json` 的 `@` 写法是认的，两者别混。
- **`+record-list --limit` 上限 200**（不同版本不同，超了报 `must be between 1 and 200`），用 `--offset` 翻页；终端的 stdout 超过约 20KB 会被截断，`json.loads` 直接报 `Expecting ',' delimiter` —— 一律 `--format ndjson --output ./x.ndjson` 落盘再按行解析。

## 读回核对片段

```bash
lark-cli base +dashboard-block-list --base-token $B --dashboard-id $D --page-size 100 --as user \
  | python3 -c "import sys,json;[print(b['block_id'],b['type'],b['name']) for b in json.load(sys.stdin)['data']['items']]"

lark-cli base +dashboard-block-get-data --base-token $B --block-id $ID --as user \
  | python3 -c "import sys,json;d=json.load(sys.stdin)['data'];print([x['field_name'] for x in d.get('dimensions') or []]);[print({k:(v.get('value') if isinstance(v,dict) else v) for k,v in r.items()}) for r in d['main_data']]"
```
