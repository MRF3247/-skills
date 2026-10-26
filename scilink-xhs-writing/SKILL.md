---
name: scilink-xhs-writing
description: "Use when 写刀客轻研小红书图文：dbs 定结构标题，Kimi 成稿，脚本自检。"
version: 1.0.0
author: MRF3247, Hermes Agent
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [xiaohongshu, scilink, copywriting, dbs, news-writing, anti-ai-slop]
    related_skills: [dbs, dbs-content, dbs-xhs-title, dbs-ai-check, dbs-content-risk-check, chinese-social-copywriting, lark-doc, scilink-ref-style-poster]
---

# SciLink 小红书图文成稿（dbs 编排版 v1.0）

一句话：**素材 → dbs 定结构与标题 → Kimi 新闻口吻成稿 → 脚本机检 → AI 味与风险复检 → 落盘（可选写回飞书）**。全流程可复现，不靠手感。

产出规格固定：正文 ≤1000 字（含标点、含 tag），tag 恰好 5 个，末位 `#刀客轻研`，标题 ≤20 字。

## When to Use

- 用户给长文 / 飞书文档 / 论文 / 新闻，要一篇小红书图文正文
- 用户说「AI 味太重」「改成新闻报道口吻」「重写小红书」「按批注改」
- 一条稿已完成，要落盘 + 附事实核对表 + 评论区置顶出处

不适用：封面出图（用 `scilink-ref-style-poster`）、B 站口播稿、公众号长文。

## 前置

| 依赖 | 检查 |
|---|---|
| dbs 系技能 | `dbs`、`dbs-content`、`dbs-xhs-title`、`dbs-ai-check`、`dbs-content-risk-check`（缺哪个先 `skill_view` 确认） |
| Kimi API Key | `KIMI_API_KEY` 在 `~/.hermes/.env`；`scripts/kimi_write.py` 自动读取，**不要打印 key** |
| 写回飞书（可选） | `lark-cli` 已登录；见 `references/feishu-writeback.md` |

## 装备

| 文件 | 作用 |
|---|---|
| `scripts/xhs_check.py` | 字数 / tag / 标题 / AI 句式黑名单机检。退出码 1 = 必须回改 |
| `scripts/kimi_write.py` | 调 Kimi 写稿。已处理思考链吃 token、temperature 限制、限流重试 |
| `templates/kimi-prompt.md` | 写稿 prompt 骨架（事实清单 / 结构 / 禁令 / 文体 / 字数） |
| `references/ai-slop-blacklist.md` | 三档黑名单、真实批注改写对照、新闻腔六条落地做法 |
| `references/feishu-writeback.md` | 写回飞书文档、读批注、替换会丢批注的坑 |

## dbs 分工（别串岗）

| 阶段 | 主 Skill | 它负责 | 本 Skill 负责 |
|---|---|---|---|
| 结构 | `dbs-content` | 形式匹配 + 五维诊断，产出结构判断 | 落成 5 段大纲 + 砍料清单 |
| 标题 | `dbs-xhs-title` | 75 条公式库匹配，给候选标题 | 筛到 ≤20 字、贴主题、给 Top3 |
| 写稿 | —（Kimi） | — | 按 prompt 骨架出正文 |
| AI 味 | `dbs-ai-check` | 逐处标 AI 指纹 | 按报告回改并复跑机检 |
| 发布 | `dbs-content-risk-check` | 平台机审 / 医疗类目 / 导流 / 绝对化 | 定 tag、定评论区出处、落盘 |

**硬规则**：

1. **`dbs-content` 只做诊断和结构，不代写**（它自述「你不帮人写内容，你帮人诊断内容该怎么做」）。把写正文派给它 = 拿到一份诊断报告交差。
2. **`dbs-xhs-title` 只是公式匹配器**。每条候选标题必须能溯源到公式编号 + 原始爆款 + 为什么选，自由发挥视为没用工具。
3. 用户说「调用 dbs」时先跑 `dbs/scripts/check-update.sh`（有输出才把更新提醒放回复末尾）。

## 流程

### Step 0 · 取素材，先做事实骨架

读原稿（飞书长文：`lark-cli docs +fetch --doc "<URL>" --as user --doc-format markdown`），把可用事实按编号列成表：时间、主体、机构、动作、数字、出处。数字照抄，不换算、不四舍五入、不加「近 / 约」。

**完成判据**：正文里每一个数字都能在这张表里找到同值同语境的一行。

### Step 1 · `dbs-content` 出结构

按它的 Phase 2（形式匹配）+ Phase 3（五维诊断）跑，只取结构结论：五段职责 + 该砍掉哪些素材。

经验顺序：「硬事实与量级 → 机制/拆词 → 为什么会发生 → 怎么被发现 → 下游代价」。离读者最远的素材（导师连带责任、机构历史撤稿率）先砍。

**完成判据**：每段能用一句话说清讲什么；砍掉的素材写成一行清单。

### Step 2 · `dbs-xhs-title` 出标题

3–5 条候选，覆盖至少 3 类触发器；每条标公式编号 + 原始爆款 + 一句话理由；末尾给 Top3。硬约束：≤20 字（含标点）、留悬念但不许让读者看不出讲的是什么事。

**新闻事件类选题的坑**：公式库里 #1/#7 那类悬念公式套上去会跑偏——用户会因为「标题不贴主题」直接打回。改用 #26 数字锚定 + #24 人群限定（例：「印度学者造假被查，41 篇论文撤稿」）。

**完成判据**：Top1 可直接发；每条候选都能指回公式编号。

### Step 3 · Kimi 写正文

1. `cp <skill_dir>/templates/kimi-prompt.md /tmp/p.md`，填 `{{}}`：事实清单、五段职责、字数、5 个 tag。
2. `terminal(command="python3 <skill_dir>/scripts/kimi_write.py /tmp/p.md --out /tmp/draft.md", timeout=300)`

**完成判据**：`/tmp/draft.md` 有正文段落 + 最后一行 5 个 tag。

### Step 4 · 机检（不许跳）

`terminal(command="python3 <skill_dir>/scripts/xhs_check.py /tmp/draft.md --title \"<标题>\"", timeout=60)`

FAIL 的处理顺序：

1. 字数超 → 回灌 Kimi「压到 880 字以内，优先砍细节不砍事实」。
2. 命中 A 档句式 → 把具体句 + 改法回灌 Kimi 重写整段；**不要手动删两个字凑数**（会写出断句）。
3. tag / 标题不合规 → 直接改，这两项不需要模型判断。

**完成判据**：退出码 0，输出 `→ PASS`。

### Step 5 · `dbs-ai-check` + `dbs-content-risk-check` 复检

- `dbs-ai-check`：按文本顺序逐处看报告，重点看脚本抓不到的两项——**段段收金句**、**整段可删而信息不减**。
- `dbs-content-risk-check`：正文不能有外链（出处放评论区置顶）、无医疗功效表述、无绝对化词、无导流。医学科研选题的 tag 避开 `#医学科普` `#健康科普` 与病名科室词。

**完成判据**：两份报告无未处理项，或已写明为什么保留。

### Step 6 · 事实核对表

正文说法 ↔ 原文出处，一行一条，放交付文件末尾。

**完成判据**：不存在「正文有、原文无」的行。

### Step 7 · 落盘 +（可选）写回飞书

- 本地成稿：`~/Documents/Hermes/小红书成稿/YYYY-MM-DD_<短标题>.md`，含标题候选（带公式溯源）、正文、事实核对表、评论区置顶出处。交付时用 `MEDIA:<绝对路径>`。
- 写回飞书：按 `references/feishu-writeback.md`，写完必须 `+fetch` 回读验证。

## 写作铁律

1. **新闻口吻**：主语写全（机构 + 认定 + 姓名 + 内容）；先事实后背景；外文机构名首现「中文全称（ABBR）」；引号只给机构原话；语气克制，不评价不感叹。
2. **收尾落在事实上**：最新进展 / 下一步动作 / 当事机构反应。不总结、不升华、不提问、不祝福、不派活给读者。
3. **三档黑名单**见 `references/ai-slop-blacklist.md`：硬造动词、`真正…的是`、`比…多一…`、`不是…而是…` 高密度、套话、读者指令。
4. **术语按受众给**：真行话给半句白话（PubPeer、掠夺性期刊）；科研常识不解释（自引、通讯作者），解释了就是废话。
5. **tag 五档配比**：热点大词 / 精准核心词 / 受众词 / 垂类词 / 品牌词，末位固定 `#刀客轻研`；同义大词不同时打。
6. **字数**按「含标点、含空格、不含换行」的实测值报给用户，不许估。

## Pitfalls

- **Kimi k3 系列是思考模型**：不关 thinking 会把 token 全烧在 reasoning 上，`content` 返回空字符串。`kimi_write.py` 默认带 `thinking={"type":"disabled"}`。
- **`kimi-k3` 只接受 temperature=1**，传 0.85 直接 400。脚本默认不传 temperature。
- **`kimi-code` CLI 的 OAuth 会失效**（`The provided authorization grant is invalid`），别修，直接用 Moonshot API Key。
- **空格算字**：正文里「2026 年 9 月」的空格平台也计数，别用去掉空格的 len 低估。
- **`block_replace` 会让被替换块的批注失效**：用户标注意见时，先本地存稿、把批注逐条落实，再整体替换。
- **别用 `docs +update --command overwrite`**：会清空文档里的配图与评论。
- **别把写稿路由给 `dbs-content`**，也别指望 `dbs-xhs-title` 写正文。

## Verification

- [ ] `xhs_check.py` 退出码 0（`→ PASS`）
- [ ] 标题 ≤20 字、贴主题；tag 恰好 5 个、末位 `#刀客轻研`
- [ ] 事实核对表无「正文有、原文无」
- [ ] 出处链接在评论区置顶文案里，不在正文
- [ ] 写回飞书后 `+fetch` 回读到新内容
