---
name: html-ppt-generation
description: "Use when 用户要汇报PPT/演示稿：KIMI API 生成单文件 HTML PPT + AI 幻觉数据核查。"
version: 1.0.0
metadata:
  hermes:
    tags: [ppt, html, kimi, moonshot, report, presentation]
---

# HTML 汇报 PPT 生成 (html-ppt-generation)

用 LLM API（KIMI）生成单文件 HTML 汇报 PPT。触发：用户要「汇报 PPT」「演示稿」「方案展示 HTML」并要求审美高级。

## KIMI API 直接调用（绕开 vision_analyze/工具链）

- 凭证：KIMI_API_KEY 在 ~/.hermes/.env（moonshot），直接 HTTP 调 `https://api.moonshot.cn/v1/chat/completions`，Authorization: Bearer
- 模型：kimi-k2.5（文本+图像输入；生成 HTML/OCR 都可靠）
- **max_tokens 要给足**：完整 HTML PPT 需 24000-32000；OCR 用 2000-4000
- 图像输入：`{"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}}`
- 用途：①图片 OCR（vision_analyze 401 时的兜底）②生成 HTML PPT ③任意文本生成
- 模型列表可查 `/v1/models` 确认可用模型名（勿假设）

## 生成 HTML PPT 的 prompt 规范

单次调用生成完整单文件（自包含，无外链）：
- 明确要求：所有 CSS/JS 内联、无外部依赖（不引外链字体/库/图片）
- 审美指定：深色学术风（#0b0f1a 系）+ 霓虹渐变 + 玻璃拟态卡片 + 大数字 + 纯 CSS 图表（柱状/环形/漏斗）
- 交互指定：键盘方向键/空格翻页 + 底部进度点可点击 + 渐入动画
- 页数明确（如 12 页）+ 每页主题清单 + 每页要放的数据
- 结尾：「数据必须用我提供的，不得编造；直接输出完整 HTML，不要代码块包裹，不要解释」
- 输出清理：去掉可能包裹的 ```html 代码块标记

## ⚠️ AI 幻觉核查（必须做，本次踩坑）

LLM 生成 PPT 会**编造示例内容**——数字真实但配套标题/案例是编的（如把真实播放 1604 万安到编造的「ChatGPT论文质量翻倍」标题上）。核查流程：
1. 提取 PPT 中所有「数据-名称」配对（数字 ↔ 标题/案例/来源）
2. 与源数据文档交叉核对（每对都要对得上）
3. 发现编造 → 用 Python 精确替换为真实内容（正则定位完整单元格文本再替换，注意子串变体）
4. 验证：grep 确认无残留编造词 + 关键数字全部在位
- 通用原则：**任何 AI 生成物（分析/PPT/报告）里引用的示例、原话、数据配对都必须可溯源**；评论引用要对得上抓取缓存，播放数据要对得上 catalog

## 数据注入式 HTML（仪表盘/总览页，2026-08 踩坑总结）

当数据量大（15 账号 × 月度序列）、不适合塞进 prompt 时：**让 KIMI 生成带占位符的模板，脚本注入数据**。

1. **prompt 约定**：明确要求 `const DATA = __DATA__;`（原样保留占位符），并给数据结构示例（字段名必须与最终注入的 JSON 完全一致——KIMI 可能自创字段名，如把数组写成单值字段 `median` vs 注入数据的 `med`，导致 `values.filter is not a function`）
2. **注入后校验**：
   - 占位符无残留（`"__DATA__" not in html`）
   - **浏览器实测**（HTTP 服务 + browser_navigate + console 查 `Array.isArray(DATA)` 和长度）——KIMI 字段名错误只有实测能暴露
   - 交互实测：全选/全不选/单选 checkbox、指标切换按钮、空状态、legend 更新
3. **KIMI 输出不稳定**：可能漏写占位符 → 重试循环（3 次，每次检查占位符存在）
4. **KIMI 防御性写法要清理**：它可能生成 `const DATA = typeof [数据] !== 'undefined' ? [数据] : generateMockData();`（数据出现两次 + mock 函数残留）——用正则清理为单份 `const DATA = [...];`，删除 `generateMockData` 函数定义（文件体积可减半）
5. **JS 错误定位**：页面空白但 DOM 部分渲染时，注入 `window.onerror` 捕获显示错误（如 `TypeError: values.filter is not a function @line N`），定位后移除调试代码
6. **数据聚合注意**：catalog 的 fans 字段常为 0 或「46.49万」字符串格式——从 accounts.yaml 读或写万格式解析函数

## 本地预览（浏览器工具不支持 file://）

browser_navigate 打开 file:// 本地 HTML 会 400——用临时 HTTP 服务：
```bash
cd <目录> && python -m http.server 8899  # 后台
# 然后 browser_navigate http://localhost:8899/文件名.html
```
渲染后用 snapshot 检查每页内容完整性（标题/数据/图表是否都渲染）。

## 相关

- 运营方案文档配套见 bilibili-batch-ops（B站选题分析数据源）
- 小红书笔记图 OCR 用 KIMI 兜底见 xiaohongshu-content-scraping

---

## 已合并的同类技能（2026-09-23 归并）

以下技能内容已并入本技能，原文存档在 `references/`，脚本/模板在 `scripts/<名称>/`、`templates/<名称>/`。技能清单里不再单独出现它们；需要时读对应文件。

| 原技能 | 适用范围 | 原文 |
|---|---|---|
| `html-presentation-deck` | 用户要汇报 PPT / HTML 幻灯片时使用：KIMI 生成单文件 HTML 汇报，生成后必须数据交叉核验。 | `references/merged-html-presentation-deck.md` |
