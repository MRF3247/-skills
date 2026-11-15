## Description: <br>
Assists with Chinese undergraduate, master's, and course papers, proposals, and standalone literature reviews by drafting outlines, revising text, reviewing arguments and evidence, and auditing citation or consistency issues within explicit academic-integrity boundaries. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[gongyu0918-debug](https://clawhub.ai/user/gongyu0918-debug) <br>

### License/Terms of Use: <br>
MIT-0 <br>


## Use Case: <br>
Students, researchers, and academic writing assistants use this skill to plan, draft, revise, and review Chinese academic manuscripts from provided materials, institutional templates, or explicitly authorized source lookup. It is designed to preserve evidence boundaries, citation mapping, long-form consistency, and academic-integrity limits rather than replace the author's own scholarly contribution. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Long-document workflows may require reading full drafts or multiple files and may create .academic-writing state files. <br>
Mitigation: Review the materials before use and ask the skill not to persist state when local working files are not appropriate. <br>
Risk: Authorized source lookup can expose search terms derived from research materials. <br>
Mitigation: Authorize lookup only for material you are comfortable using as search terms, and do not upload unpublished full text, personal information, or sensitive research materials. <br>
Risk: Academic drafting can overstate claims, mis-map citations, or imply unsupported research progress when source material is thin. <br>
Mitigation: Use the skill's material gates, source-status checks, citation audits, and author review before relying on draft text. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/gongyu0918-debug/skills/chinese-academic-writing-assistant) <br>
- [普通中文论文专项叶](references/academic-writing.md) <br>
- [中文论文开题报告专项叶](references/academic-proposal.md) <br>
- [中文论文独立文献综述专项叶](references/academic-literature-review.md) <br>
- [学术来源检索与引用覆盖](references/citation-research.md) <br>
- [中文论文长稿稳定与全文一致性](references/long-form-consistency.md) <br>
- [论文 ANTI-AI 语义复核](references/anti-ai-writing.md) <br>


## Skill Output: <br>
**Output Type(s):** [text, markdown, shell commands, guidance] <br>
**Output Format:** [Plain text or Markdown, with optional shell commands and JSON reports from read-only audit scripts] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [May propose local read-only citation, manuscript, or prose audits; web or source lookup is gated on explicit user authorization.] <br>

## Skill Version(s): <br>
0.0.7 (source: server release evidence) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
