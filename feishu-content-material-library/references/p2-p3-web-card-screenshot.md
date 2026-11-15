# P2/P3 网页卡片截图（camofox 方案）

目标：把「一页真实网页」截成 1080×1440（3:4）的小红书图文卡片，不白屏、不删正文、高亮落在数字上。

## 为什么用 camofox 而不是 curl + Chrome

| 情况 | 做法 |
|---|---|
| 站点对 curl 返回 403 / Cloudflare 验证（Medscape、MedPage、NEJM、PNAS 一类）| camofox 导航后再截图，真实浏览器指纹能过 |
| 正文在内部滚动容器里（`body.scrollHeight` ≈ 视口高，`scrollIntoView` 无效）| 先跑 unwrap 脚本把 overflow:hidden/auto 容器展开，再截全页 |
| 普通静态页（ScienceDaily、博客、gov 通知）| camofox 也适用，步骤完全一样 |
| 付费墙只给一屏摘要、或全页渲染直接 500 | 换 PMC／出版社 OA／预印本链接；都拿不到才退回新闻页，并在汇报里写明实际版本 |

Chrome headless + 本地 HTML 副本只能处理静态页；站点的 CSS 依赖 JS 时本地副本会截出纯白图，别在那条路上反复调。

## 端点契约（实测）

```
GET  /health                          -> {"browserRunning":…,"activeTabs":…}
POST /tabs {userId,sessionKey}        -> {tabId}
POST /tabs/{id}/navigate {userId,url} -> {httpStatus}
POST /tabs/{id}/viewport {userId,width,height}   # 高度上限≈2400，6000 会 400
POST /tabs/{id}/evaluate {userId,expression}     # 结果在 result 字段
GET  /tabs/{id}/screenshot?userId=..&fullPage=true   # 必须 GET；POST 404
DELETE /tabs/{id}?userId=..
```

导航偶发 500（浏览器唤醒竞态）：失败 sleep 3-4s 重试，最多 3 次。

## 流程（脚本：`scripts/shot_web_card.py`）

1. navigate → 等 5s → 静音视频。
2. 注入隐藏 CSS：只黑名单明确广告/导航/弹窗 class。**绝不能写 `[class*=paywall]`／`[class*=sticky]`／`[class*=article-]`**——出版社正文容器就叫这些名字，一写正文全没。
3. 按文本移除残留壳：`ADVERTISEMENT`、`Accept all`、`Log in or register for free`、`我来说两句`、`24小时热文` 等，长度阈值 ≤250 字（防误删正文段）。
4. unwrap 内部滚动容器（`scrollHeight > clientHeight+100` 且 overflow 为 hidden/auto/scroll → visible/auto height）。
5. 高亮：只在 `p`（或其他传入 selector）里包 `<mark class="hlmark">`，最多 2 段；颜色 `rgba(255,235,59,0.55)`。
6. 取 mark 的文档坐标（`getBoundingClientRect().top + scrollY`）——**不要用黄色像素检测定位**，页面上原有的淡黄 Key Points 框会让你把 P3 裁成 P2。
7. `fullPage=true` 截图 → 宽度 1200 左右，`win_h = W*4/3` → P2 从首个非白行开始裁，P3 从 `mark_y - 0.30*win_h` 开始裁 → 缩放 1080×1440（缩小比放大清晰）。

## 自检

- 单张：`vision_analyze` 问「有没有正文段落／标题日期可读／高亮在哪些数字／有没有登录墙广告」——只问能判定对错的点。
- 批量：把全部 P2/P3 缩成 270×360 拼 contact sheet，一次看完；再对可疑格回看原图。
- 程序指标：`ink = (gray<200).mean()*100`。`ink<4%` ≈ 大半张白，`ink>90%` ≈ 一整块深色大图；两张图逐像素差≈0 说明 P3 裁成了 P2。
- 常见缺陷对照：高亮在标题不在结果段（selector 太宽，命中 li/提示框）；P3 顶部重复 P2（mark 在文首，需下移裁切起点）；底部被截断（crop 超出图像高，需 clamp）。

## 裁切几何

```
win_h = int(W * 4 / 3)          # 保持 3:4，不改宽高比
P2: top = 首个非白行; clamp(0, H-win_h)
P3: top = mark_y - 0.30*win_h; clamp(0, H-win_h)
```

`mark_y` 是文档坐标，截图是全页从 0 开始，所以 1:1 映射；若图片宽度与视口宽不同，先乘 `W/innerWidth`。
