# 浏览器自动化工具选型（2026-08-31 调研）

触发：用户问「XX 浏览器/工具能不能爬小红书」「XX 跟 YY 比怎么样」时直接引用本文件，不必重新调研。

## 品类地图（三类，选型先归类）

### 1. 真浏览器桥（借真实登录态）—— 能破小红书评论墙

共同点：本地桥服务 + 浏览器扩展（CDP 或 WebSocket），Agent 操作**你已登录的 Chrome/Edge**；目标网站看到=你本人操作。
**对小红书的意义：评论 API 的 x-s 签名由页面 JS 自动生成（依赖正常浏览器会话），真实登录浏览器是唯一理论可行的评论抓取路径**——⚠️ 理论推理，未实测。
共同代价：操作的是**真账号**，被风控标记的是真实 IP/账号（不是一次性指纹），只适合低频轻操作，60s 纪律照守、风控即停。

- **BrowserSkill**（腾讯开源，MIT，2026 新项目）：`bsk` CLI+daemon+扩展。支持 Cursor/Claude Code/Codex/Hermes Agent/DeepSeek Harness 等；Chrome/Edge（**Firefox 计划中**）；独立 Agent Window 不打扰用户；human-in-loop（验证码/登录弹窗真人接管）。安装：`curl -fsSL https://raw.githubusercontent.com/Tencent/BrowserSkill/main/install.sh | sh` + Chrome Web Store 扩展。
- **Kimi WebBridge**（月之暗面官方，即用户口中的「web bridge」）：本地桥服务+扩展（CDP 实现）。同样支持 Kimi Code/Claude Code/Cursor/Codex/**Hermes Agent**/OpenClaw。与 BrowserSkill 同品类直接竞品，架构几乎一致，二选一即可。
- **Codex Chrome 扩展**（OpenAI 官方）：仅 Codex 可用（对话框 `@chrome` 调用），不通用，不适用 Hermes。
- **Tabbit**（美团 AI 浏览器，2026-03 公测）：浏览器内置 Agent（消费级），Agent 是给人界面指挥的，不适合脚本/批量管线；有 CDP 端点（官方 Tabbit-Devtools-Skill）可外接，但新产品稳定性未验证。对爬虫无增量。

### 2. 伪装浏览器（免登录 + 防封 IP）—— Camofox

**Camofox = headless Firefox + C++ 指纹伪装**，REST API（localhost:9377）。**Firefox 内核 → 装不了 Chrome 扩展 → 与 BrowserSkill/Kimi WebBridge 不兼容**（BrowserSkill 的 Firefox 支持还在计划中）。
定位：免登录抓搜索页/RSS/视频页，绕 IP 风控；但 IP 级风控照样死（风控是 IP 级不是会话级）。

### 3. 可编程框架（批量/调度/自己做产品）—— browser-use

**browser-use**（瑞士团队，MIT，GitHub 头部项目，benchmark #1）：
- Python 库（`pip install browser-use`），`Agent` 类自己写代码调，LLM 自主操作浏览器；适合写批量/并行/调度爬虫
- 复用真实登录态需要配置（`real_browser.py` 连 CDP 到已有 Chrome profile），非开箱即用
- **代理轮换/验证码解决/stealth 指纹全在付费云**（Browser Use Cloud）；开源版默认 Playwright 自动装 Chromium（无登录态、易被小红书风控），开源版对小红书没有比 curl/camofox 更强的点
- 也有 harness 接入形态（`browser-use skill install`，支持 Hermes 等）
- 结论：用户场景（素材采集、破评论墙）用不上；真撞验证码/大规模并行是商业云付费场景

## 对小红书采集的选型结论

| 需求 | 方案 |
|---|---|
| 破评论墙（低频单条） | 真浏览器桥：BrowserSkill 或 Kimi WebBridge 二选一（**理论可行，未实测**，装了先拿 1 条笔记验证） |
| 免登录正文/图片/互动 | 现有 curl + cookie 文件管线（详情页 `__INITIAL_STATE__` 正则提取） |
| 防封抓搜索页/RSS/视频页 | Camofox |
| 验证码/大规模并行 | 商业云（browser-use Cloud 等），不是免费开源路径 |

## 关键事实速查

- BrowserSkill 扩展只支持 Chrome/Edge（Firefox 计划中）→ 装不进 Camofox（headless Firefox），两者理念也相反（真实登录 vs 伪装），是替代关系不是互补
- Kimi WebBridge 官方支持 Hermes Agent；架构=本地桥服务+扩展+CDP，本地数据不出设备
- browser-use 开源版免费可自用，验证码/代理/stealth 是付费云卖点
- 真浏览器桥共同风险：操作真账号，被风控伤真号 → 只适合低频、轻操作、用户知情
- 用户问这类问题通常是好奇/选型心态（「我突然好奇」）——先给结论+归类，别抢跑安装；用户拍板要装再动手
