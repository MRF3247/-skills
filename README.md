# Prompts & Skills

自己整理的 prompt 和技能，全部公开。每个技能一个目录，`SKILL.md` 是入口，`scripts/` `templates/` `references/` 是它自带的工具与资料。

## 技能

| 技能 | 干什么 | 版本 |
|---|---|---|
| [scilink-xhs-writing](scilink-xhs-writing/SKILL.md) | 小红书图文成稿：dbs 定结构和标题 → Kimi 写成稿 → 脚本机检字数/tag/AI 句式 → 事实核对 → 落盘（可选写回飞书） | 1.0.0 |
| [scilink-ref-style-poster](scilink-ref-style-poster/SKILL.md) | 刀客轻研标准 3:4 小红书封面出图：内置参考图、PSD 模板、色板校验脚本 | 2.1.0 |
| [scilink-medical-topic-scout](scilink-medical-topic-scout/SKILL.md) | 医学选题挖掘：多源直抓 → 选题判定 → 链接/日期/DOI 三核 → 入飞书物料库 | 1.0.0 |

## prompt

- [MinerU_OCR流程Prompt.md](MinerU_OCR流程Prompt.md)
- [课程逐字稿整理成知识库-交接提示词.md](课程逐字稿整理成知识库-交接提示词.md)
- [豆瓣新书速递_定时任务Prompt.md](豆瓣新书速递_定时任务Prompt.md)

## 怎么用

**只读内容**：直接点上面的链接。

**装进 Hermes**（本机技能目录）：

```bash
git clone https://github.com/MRF3247/-skills.git /tmp/skills
cp -r /tmp/skills/scilink-xhs-writing ~/.hermes/skills/
```

**给别的 AI 读**（Claude Code / Codex / Kimi 都行）：把 raw 链接直接丢过去，例如

```
https://raw.githubusercontent.com/MRF3247/-skills/main/scilink-xhs-writing/SKILL.md
```

**单独跑脚本**（不必装技能）：

```bash
python3 scilink-xhs-writing/scripts/xhs_check.py draft.md --title "标题"
```

## 依赖

`scilink-xhs-writing` 的完整流程依赖 dbs 系技能（`dbs`、`dbs-content`、`dbs-xhs-title`、`dbs-ai-check`、`dbs-content-risk-check`）和 `KIMI_API_KEY`；两个脚本（字数/tag/黑名单机检、Kimi 写稿）可以脱离技能单独使用。具体依赖写在各自 SKILL.md 的「前置」一节。
