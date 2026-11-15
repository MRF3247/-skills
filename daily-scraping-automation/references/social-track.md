# 社媒互动数据追踪（social_track.py 模式，2026-08-26 实测）

场景：小红书/抖音新稿件发布后的互动增长追踪（对齐 B站播放追踪机制）。公众号已有（抓取顺带补阅读量）；小红书浏览量平台不公开（只追赞/藏/评），抖音可追播放。

## 机制（门槛版——全量追踪太贵）

```
发布（t0）→ 观察 2 天 → 检查赞>50 或 评>10？
  ├─ 达标 → 进 7 天队列（状态文件 social_track.json：{link: {平台,标题,进队,天}}）
  │         → 每日查详情 → 更新本地 content 互动字段 → 天+1 → 满 7 天退队
  └─ 未达标 → 不追
```

- 进队窗口：**发布时间 ∈ [今天-9, 今天-2]**（2 天观察 + 7 天追踪）——注意别用"入库时间"窗口：一次性建库的数据入库时间集中在同一天，会把历史快照全拉进队（实测 366 条→改发布时间窗口后 162 条→初始队列仍含建库快照属正常，首轮成本一次性）
- 每日查询量 ≈ 队列大小（~30-160 条）× ¥0.02 ≈ **¥0.2-1/天**（初始建库快照那轮 ~¥3 一次性）

## 接口（redfox，参数都是 workId）

| 平台 | 路径 | 返回关键字段 |
|---|---|---|
| 小红书 | `/story/api/xhsUser/queryWorkDetail` | workLikedCount / workCommentsCount / workCollectedCount / workShareCount |
| 抖音 | `/story/api/dyData/queryWork` | likeCount / commentCount / collectCount / shareCount / viewCount |

- 抖音 `queryWorkDetail` 和 `getWork` 都是 **404**——只有 `queryWork` 对。
- 从链接提取 workId：小红书 `/explore/([a-zA-Z0-9]+)`；抖音 `(\d{15,25})`。
- 找新接口路径：GitHub `redfox-data/redfox-python-sdk` 仓库，`redfox/endpoints/douyin.py` 等源码 grep `/story/api/`，比猜路径快。

## 集成

- 抓取完成后 `enqueue()`（进队检查）；每日 `update()`（查详情+更新+退队）——pipeline 阶段 2 并行一路 `python3 social_track.py`（默认 all：enqueue+update）
- 状态文件原子写：写 `.tmp` 再 `os.replace`
- 每查询间隔 1s；post 加重试（失败天+1 不阻塞）

## 验证

- `python3 social_track.py enqueue` 后检查状态文件条数与窗口 SQL（发布时间 BETWEEN）
- update 后抽查本地库互动字段是否变化
