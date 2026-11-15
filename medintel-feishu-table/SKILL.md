---
name: medintel-feishu-table
description: Use when 同步/维护「每日医学情报总表」（MedHOT × 每日医讯 → 飞书多维表格）。
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [feishu-bitable, medical-news, sync, medhot, med-news-hub]
    related_skills: [medhot-medical-news-site, med-web-dashboard, lark-base]
---

# 每日医学情报总表（MedHOT × 每日医讯 → 飞书多维表格）

## When to Use

- 用户要看/改「每日医学情报总表」，或问「今天同步了多少条」「哪个系统漏了什么」
- 同步断了要补跑、要改窗口天数、要加列、要建新月份表
- MedHOT 或每日医讯任一改了库表结构 / 字段含义，需要跟着改同步逻辑
- 用户要我扫源发现漏收的新闻、补录到表里

## 对象坐标（2026-10-14 建）

- 表格：**每日医学情报总表**，在知识库「不卷@医时」（space_id `7673753190189337892`）
- wiki 节点 `SeOzwYIv3ihYcWkV8CncZof6nLh` · **base_token `LxE4bRFqHaWoyxsPBEFc8BcInOe`**
- 链接 https://my.feishu.cn/wiki/SeOzwYIv3ihYcWkV8CncZof6nLh
- 按月分表（`2026-10`…），27 列；首表 table_id `tbljRVqpA4FBnwrc`（新月份表自动创建）
- 同步脚本 `~/.hermes/scripts/medintel_sync.py` + 包装 `medintel_sync.sh`；launchd `com.medintel.sync` 每天 **09:30** 跑（窗口 2 天）
- 手动补跑：`bash ~/.hermes/scripts/medintel_sync.sh [天数]`；日志 `/tmp/medintel_sync.log`

## 设计（用户拍板）

1. **登记范围 = 全部合格稿**（不是只登精选）：`publications.visibility='public' AND title<>''`。原因：精选门槛 T1=60/T2=76 对医学稿太严，有几天精选是 0 → 只登精选会出空表。表里用「MedHOT精选」复选框 + 评分区分，这张表顺带就是门槛校准的人工标注底稿。
2. **一行 = 一篇内容**，唯一键 = 规范化链接（去协议/www/查询串/尾斜杠）。两个系统命中同一键 → 合并成一行：MedHOT 的评分和医讯的播放/互动落在同一行。
3. **「覆盖」列**（两边都有 / 只有 MedHOT / 只有每日医讯）是这张表最值钱的东西：一眼看出 MedHOT 漏掉的中文内容（B站/YouTube/行业站）、以及只有 MedHOT 有的论文与海外情报。
4. **按月分表**：飞书单表行数上限（基础版 2 万行，旗舰 5 万，最大可扩 200 万）——每天合计 150–300 行，2–3 个月就撞满 2 万，所以按月建表，脚本自动建新月份表。
5. 更新不写「备注」「录入来源」→ 保护人工补录行的人工标注。

## 时间窗口径

MedHOT 是 24 小时持续抓取、**没有「抓完」时刻**，所以不是「等它跑完再同步」，而是**定时 + 时间窗 + 唯一键去重**：

- MedHOT：`coalesce(p.published_at, a.discovered_at) >= now() - interval '2 day'`
- 医讯：`发布时间 >= date('now','-1 day') OR 入库时间 >= date('now','-1 day')`
- 每天 09:30 跑（医讯 05:00 流水线 05:17 结束，MedHOT 也已落库稳定）

## 踩过的坑（重写脚本前必读）

1. **`--format ndjson --output` 时 lark-cli 的 stdout 是 manifest，不是 `{ok,data}` 信封**！用它做统一封装校验会把成功当失败（报错 `error: {}`）。读记录导出必须直接 `subprocess.run` + 读 ndjson 文件，并带 `--overwrite`（否则二次运行报 `output file already exists`）。
2. **`--field-id` 必须传字段 ID，不能传字段名**（传中文名报 `not_found`，错误体还是空的）。每次先 `+field-list` 把 名字→field_id 解析出来（新月份表的 field_id 与首表不同）。
3. **MedHOT 的 `publications.category` 是英文键**（research/clinical/industry/policy/public-health/opinion/explainer），表里选项是中文 → 必须映射，否则批量写入报 `800030005 not_found: Provide an existing option value`。
4. **医讯库 `主分类` 有 LLM 垃圾值**（`「日常其他」`、`【主分类】日常其他`、`【模糊分类】实用干货,医学新闻`、甚至「没有正文内容，无法打标…」）→ 用白名单 `pick_option()` 从字符串里挑第一个合法选项，挑不到就留空。
5. **医讯库 medRxiv 的 `链接` 是裸 DOI**（`10.64898/2026.10.07.26364583`，没有 scheme）→ `urlsplit` 拿不到 host，会被当成无链接。`norm_key` 里正则 `^10\.\d{4,9}/` 命中就补成 `https://doi.org/...`。
6. **不能用内置 `hash()` 做唯一键**：Python 每个进程的字符串哈希随机化 → 每次运行都生成新键 → 同一批数据反复新增。要用 `hashlib.md5`。排查特征：表里出现 `mednews:<纯数字>` 键、记录数越跑越多。
7. **医讯内部同一链接会重复**（同一条稿两行）→ 合并逻辑要区分「跨系统合并」和「医讯内部重复」，否则「覆盖」会被误标成「两边都有」。
8. **一次性写量**：单表单批 ≤200 条且必须串行（并行报并发冲突 1254291）；543 条 ≈ 3 批、约 30 秒。
9. 字段值格式：单选 `["值"]`、多选 `["A","B"]`、复选框 `true/false`、日期用毫秒时间戳、文本直接给字符串；不适用/清空传 `null`（单选清空传 `[]`）。

## 日常维护

- 看效果：表里「覆盖」列筛「只有每日医讯」= MedHOT 没抓到的中文内容；筛「MedHOT精选=true」= 当天进精选的。
- 补漏（用户定的口径）：**我扫源发现漏收 → 每天固定时间随表一起补**，补录行标「录入来源=人工补录」+ 填「备注」写漏收原因。
- 想临时停更：`launchctl unload ~/Library/LaunchAgents/com.medintel.sync.plist`。
- 换 base/表：改脚本顶部 `BASE_TOKEN` + `FIELDS`（新月份表按它建列）。
