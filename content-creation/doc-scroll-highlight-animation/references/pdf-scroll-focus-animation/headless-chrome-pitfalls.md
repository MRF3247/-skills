# 无头 Chrome 自检三坑 + 迭代改版验收清单

## 无头 Chrome 自检的坑（实战血泪）
- 改 HTML 前先把每个 `<script>` 块抽出来跑 `node --check`；运行时错误会让 renderAt 静默早退，页面停在 t=0 初始态（无卡片无压暗），看起来像「参数没生效」。
- `--enable-logging=stderr` 在 `--headless=new` 下抓不到 console.log/error；诊断信息要渲染进 DOM（大字号固定位置）再截图读；`document.title` + `--dump-dom` 读不到（抓的是初始 DOM）。
- 多次 patch 容易把 HTML 截断（一次替换吞掉半个 style 属性 + 半个 script 开头），每次改完必须：node --check 全部块 + 全帧截图回归。
- 诊断框会被 stage 层盖住；`?v=N` 参数破 file:// 缓存。
- 量色域要分开设阈值：印章砖红 #c0392b=(192,57,43) vs 马克笔混白粉红≈(255,150,150)，别把笔迹当印章量。
- CSS `padding-right` 只影响文字排版，不改变盒子 getBoundingClientRect —— 用盒子 rect 算「文字让出的天窗」会算错，要用布局常量 × 缩放比。

## 迭代改版验收清单（用户逐条对，全部像素级）
- 删标签/删字幕/删登记号：全帧截图左上、右上、底部三处确认无残留。
- 「开头不动」类：t=0.5 帧必须是文档原始状态。
- 印章不遮字：印章 bbox 与文字 bbox 求交 + 放大目检双确认；章内深色文字像素应为 0。
- 中文换行：关键词组 `white-space:nowrap` 包住防拆词；句末补句号；放大截图逐词核对（曾把「结直肠癌」拆成「结直肠/癌」）。
- 交付前清调试残留：DBG 文本、errbox、console.log 全删后再跑全帧回归。
- 全帧帧差：330 帧 0 重复（renderAt 必须是 t 的纯函数，无 CSS transition 残留）。