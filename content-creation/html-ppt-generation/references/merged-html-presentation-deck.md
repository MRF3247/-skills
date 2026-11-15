<!-- 由 html-presentation-deck 合并而来（原技能目录已删除，原文保留）。源: /Users/Jin/.hermes/skills/content-creation/html-presentation-deck -->

---
name: html-presentation-deck
description: "用户要汇报 PPT / HTML 幻灯片时使用：KIMI 生成单文件 HTML 汇报，生成后必须数据交叉核验。"
version: 1.0.0
metadata:
  hermes:
    tags: [html, ppt, presentation, kimi, moonshot, report, deck]
---

# HTML 汇报 PPT 生成 (html-presentation-deck)

用户要求「写一套汇报 PPT」「HTML 幻灯片」「方案展示」时使用。方法：调 KIMI API（moonshot）让模型直接产出**单文件自包含 HTML**（内联 CSS/JS、无外部依赖），本地预览验证后交付。用户偏好审美高级、详细但不要废话、数据为王。

## 1. 调用 KIMI API（key 不落盘）

```python
import json, urllib.request, os
key = [line.split("=",1)[1].strip() for line in open(os.path.expanduser("~/.hermes/.env"))
       if line.startswith("KIMI_API_KEY=")][0]
body = {"model": "kimi-k2.5",
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": 32000, "stream": False}
req = urllib.request.Request("https://api.moonshot.cn/v1/chat/completions",
    data=json.dumps(body).encode(), headers={"Content-Type": "application/json",
    "Authorization": "Bearer " + key})
d = json.loads(urllib.request.urlopen(req, timeout=600).read())
html = d["choices"][0]["message"]["content"]
```

- 参考实现：/Users/Jin/Documents/Hermes/B站工作流/make_ppt.py
- max_tokens 给 32000（HTML 完整代码可能 15-25KB）；输出若被截断（结尾无 `</html>`）→ 减小页数或拆两段生成

## 2. Prompt 结构（用户偏好已固化）

- **页数规范**：明确「共 N 页 + 每页主题一句话」（12 页是已验证的舒适量：封面→数据底座→核心洞察→矩阵→漏斗→规律→方法论→红线→计划→转化→监控→结尾）
- **设计约束**（照抄）：深色学术风（深蓝黑底 #0b0f1a 系）+ 霓虹渐变点缀（青蓝/紫）+ 玻璃拟态卡片 + 大数字数据展示 + 纯 CSS 图表（柱状图/环形图/漏斗）；键盘方向键/空格翻页 + 底部进度点可点击 + 页面切换渐入动画；单文件自包含无外链；中文精炼不废话
- **数据要求**：所有数字用我提供的数据，不得编造；HTML 直接输出完整代码（含 `<!DOCTYPE html>`），不要代码块包裹，不要解释
- 把要展示的数据结构化写进 prompt（分层数字/矩阵/表格/引语），不要只丢一份长文档让模型自己挑——模型会挑错重点

## 3. 交付与预览

- 保存为 `内容增长/xxx-汇报PPT.html`（用户知识库惯例）
- **browser 工具不支持 file:// URL（400）**：起本地 HTTP 服务预览——`python -m http.server 8899` 指向 html 所在目录，browser_navigate 打开 `http://localhost:8899/文件名.html`，渲染正常即可
- 验证清单：① 文件以 `</html>` 闭合 ② slide 数=约定页数 ③ 数据断言（见下）④ 关键数字齐全

## 4. 数据交叉核验（强制步骤，踩过坑）

LLM 会用**真实数字配编造示例**（kimi 实测：把 1604 万播放安到编造标题「3个设置让ChatGPT论文质量翻倍」上）。生成后必须：

1. 把「每个关键数字 + 它应该配套的真实文本」配对 grep/脚本断言（如 `1604 ↔ 两步解决90%`、`80.7% ↔ 爷爷扛过来了`），不匹配即编造
2. **示例性内容**（示例标题/案例/引用）是编造重灾区；统计性数字（总量/占比）一般准确
3. 修复：脚本替换编造文本为真实条目（数字不动、换真实文本），替换后重新断言无残留
4. 通用原则：LLM 输出的任何「看起来像事实的示例」都假设可能编造，除非来自我们提供的原始数据

详见 batch-pipeline-robustness §8d（同一起事故的通用化记录）。

## 相关

- 数据来源与选题调研：bilibili-video-pipeline / 腰部选题库 / 避雷分析（Obsidian 内容增长 文件夹）
- 后台生成类长任务：batch-pipeline-robustness
