---
name: obs-live-scene-design
description: "Use when 用户搭 OBS 直播间画面（PPT+露脸、1920x1080）或要直播视觉方案时。"
version: 1.0.0
author: Hermes Agent (curated)
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [obs, 直播, 场景布局, overlay, 1920x1080, 视觉方案]
---

# OBS 直播画面搭建（obs-live-scene-design）

## When to use
用户用 OBS 布置直播间（典型：PPT + 露脸摄像头，1920x1080 横屏）、要直播画面布局参考、做透明 PNG overlay/底板、或要直播视觉方案时。完整方案文档（含全部链接）：`/Users/Jin/Documents/Hermes/OBS直播画面方案.md`（2026-08-07 版，含案例链接）。

## 基础配置（OBS）
- 画布 1920x1080、输出 1920x1080、30fps、码率 4500-6000kbps
- PPT 用「窗口捕获」而非「显示器捕获」（不受桌面弹窗/通知干扰）；裁剪掉软件自身边框
- 摄像头：「视频捕获设备」，1080p（光线差降 720p 保帧率）
- 抠像：绿幕用「色度键」滤镜；无绿幕用 OBS 28+ 内置「背景移除」滤镜（效果看光线，先测）
- 场景至少 4 个：开场暖场 / 正式讲解 / 答疑互动 / 结束收尾，别一个布局播全场
- 音频：麦克风+桌面音频分轨，别用电脑内置麦（收风扇/键盘声）

## 三种布局模式（知识/教学直播，按场景选）
1. **PIP 画中画（最推荐，讲 PPT 为主）**：PPT 满屏 + 人像小窗右下/右上角。人像窗用 4:5 或 3:4（不用 16:9 全宽人太小、不用 9:16 黑边浪费），加圆角+品牌色描边(2-4px)+极轻投影
2. **左右分屏（答疑/连麦）**：左 2/3 PPT + 右 1/3 主播竖窗（人像大、表情手势清楚），中间 2px 分隔线或渐变色带
3. **上下条幅式（读论文/图表多）**：上 3/4 PPT + 底部条幅（人像半身窗+标题栏+引导关注）

## 视觉系统
- 配色：米白/浅灰蓝背景 + 1 个强调色（医感青/深蓝/暖橙），避开高饱和游戏风；全画面 ≤2 个强调色
- 透明 PNG 底板固定元素（放 OBS 图层最上层）：顶部标题条（大字 48-60px 起步，1080p 下才清晰）、底部信息条（账号名+直播主题+关注引导，半透明底）、人像框+身份标签（如「XX 主治医师」增强专业信任）
- 字体：无衬线大字（思源黑体/阿里巴巴普惠体/得意黑），不用衬线体（屏幕小字会糊）
- 用户账号风格：延续小红书「大字+留白+手写涂鸦」方向，人设统一

## 避坑清单
- 平台安全区：重要内容勿贴最底部/最右侧 10%（平台叠 logo/角标/字幕）
- 人像别挡 PPT 关键内容：开播前切到最挤的一页检查
- 摄像头放屏幕顶部正中偏上，人物视线在画面上 1/3 处，避免俯视/仰视
- 背景别用纯白墙（反光、抢注意力、人脸曝光）；灰布/书架/绿幕都行
- 面光为主（环形灯或 LED 放摄像头同侧），人物背后不要强光源
- 每场开播前预览检查：PPT 切边、人像被挡、底部信息条被平台字幕压住

## 底板透明 PNG 生成管线（2026-08-07 实测）
直播底板（标题条/信息条/人像框/角标）文字必须精确，不能 AI 生图（中文乱码）。用 HTML + Chrome headless 渲染透明 PNG：
1. 每元素一个独立 HTML，1920×1080 画布（`html,body{width:1920px;height:1080px;background:transparent}`），元素用 `position:absolute` 按最终屏幕位置定位
2. 渲染命令：`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --headless --disable-gpu --hide-scrollbars --force-device-scale-factor=1 --default-background-color=00000000 --window-size=1920,1080 --screenshot=out.png "file://$(pwd)/in.html"`
3. 透明验证：PIL 检查四角 alpha 通道（`--default-background-color=00000000` 是透明关键）
4. 视觉审核用 kimi-k2.5（直调 api.kimi.com/coding/v1，见 xiaohongshu-posters 的 kimi 审核模式），两轮收敛
5. 验证案例目录：`/Users/Jin/Documents/Hermes/视频号直播视觉方案/elements/`（含完整文档）

**坑（实测踩过）**：
- 改 HTML 时 CSS 和 body 文字节点都要改——只改样式不改 `<div>` 内容会残留旧文字（kimi 审核抓到）
- 胶囊等小元素 `bottom:-30px` 相对父容器是「底部超出 30px」→ 胶囊顶会侵入框内，需 `bottom:-(高+间隙)` 才完全分离
- 空白胶囊（直播时 OBS 文本源叠字）：`min-width:200px; height:56px; background:rgba(255,255,255,0.92); border:3px solid 主色`
- 圆角统一三档：大元素 16-20px / 胶囊 999px / 不用其他值
- kimi 会把模拟占位图误判为「PPT 文字不可读」——审核时区分真实元素与合成预览里的占位块

## 直播底图 AI 生图路线（2026-08-07 实测，用户指定 kimicode→MiniMax）
用户明确要「kimicode 写提示词 + 调教 MiniMax 生图」做直播底图，不要 HTML 元素贴片（独立元素贴片有拼贴感——每个 AI 元素自带背景色，贴到统一底上色差突兀，kimi 审核判「图层叠加痕迹」）。**正解：单张完整场景底图**（所有 UI 框架画在同一张米白背景上，中央留白给 PPT/摄像头，文字全部 OBS 文本源叠）。
- 流程：写需求文档（元素位置/尺寸/圆角/间距全写死）→ kimicode k3-256k 生成英文提示词 → MiniMax image-01 抽卡迭代（8 版：4分→6→6→6.5→7→7.5→8.0→6.5，v7b 定稿）
- **MiniMax 提示词 1500 字符硬限制**：kimi 写的详细提示词常超限，需手动压缩（砍冗余修饰、保留数字参数），报错 `prompt length must be less than 1500`
- **MiniMax 单图精确执行多元素 UI 布局上限 ≈8/10**：四元素（标题条/角标/人像框/信息条）总有一两个偏差（元素位置漂移、多余小装饰、红点变白点）。抽卡可收敛但到不了完美——8 分够用，别无限迭代
- 关键提示词语义（实测有效）：「flat 2D vector UI」「decorative frames, not functional controls」「no text, no icons, no numbers」；「dashboard template」语义易画出功能控件（数字/图标残留）；「Soft UI / soft shadows」画得最干净（v7b 是新拟态风格）
- 反面教训：「no pills, no capsule objects」反而可能引出胶囊；「STRICTLY flat no shadows」版本反而更易出 3D 残留——负面词堆砌≠执行好，简洁+明确组件关系更稳
- 审图：kimi-k2.5（vision_analyze 若 401 用 kimi_see.py），重点查乱码文字/元素漂移/中央留白/统一性
- 案例目录：`/Users/Jin/Documents/Hermes/视频号直播视觉方案/`（需求文档+生成脚本+8 版抽卡存档+定稿 v7b）

## 案例/模板资源（2026-08-07 逐条验证）
- B站 医学博士直播画面（可直接看效果）：
  - BV1Yh41167TS 普外科曾医生首次直播讲痔疮防治（经典医生露脸+讲解）
  - BV1ss4y1Y7HH 张煜医生直播回放
  - BV1h43m6JEXQ 「聊医学：中西医为什么都错了」直播录屏
  - BV16XuW64EJh 偏口鱼博士（复旦医学硕士/瑞典博士在读）直播录屏
  - BV1hauA6nESS 钱博士直播回放
  - BV1RvDzBbE9U 影像科刘医生系列课程
- 布局搭建教学：BV1H44y1b7MD 虚景+PPT+手写三屏联动（B站）；YouTube lfnLdMb8EAc 教学 OBS 三种布局逐场景演示；neoacademic.com 图文教程（PPT 讲座+摄像头推流）
- 模板站：Canva twitch-overlays（免费在线改 1920x1080）、稿定设计「直播背景」（中文）、nerdordie/streamdesignz（付费参考边框/信息条做法）
- ⚠️ B站直播回放可能被删/转私密，引用前 curl 视频页验证 `<title>`；给用户前逐条验证并标注快照日期

## 相关
- 找直播案例/视频搜索技巧：bilibili-research（search.bilibili.com HTML 抓取 + 链接批量验证模式）
- 直播选题/内容方向：video-content-strategy
