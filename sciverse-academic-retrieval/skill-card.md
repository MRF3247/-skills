## Description: <br>
Sciverse academic retrieval helps agents search academic paper metadata, retrieve semantic chunks for RAG, and read byte-range paper content for citation-focused literature workflows. <br>

This skill is ready for commercial/non-commercial use. <br>

## Publisher: <br>
[sciverse](https://clawhub.ai/user/sciverse) <br>

### License/Terms of Use: <br>
Apache-2.0 <br>


## Use Case: <br>
Developers and agent builders use this skill to ground literature workflows in Sciverse paper search results, semantic chunks, original text ranges, citation and reference lists, and figure or table resources. <br>

### Deployment Geography for Use: <br>
Global <br>

## Known Risks and Mitigations: <br>
Risk: Agents send academic search queries and document identifiers to Sciverse. <br>
Mitigation: Use the skill only for workflows where sending those queries and identifiers to Sciverse is acceptable. <br>
Risk: A Sciverse API token is required for searches, content reads, and resource retrieval. <br>
Mitigation: Provide the token through SCIVERSE_API_TOKEN and keep the API base URL on sciverse.space domains. <br>
Risk: Retrieved paper excerpts and relation counts can be partial because full text access, byte ranges, and relation pagination depend on available corpus data and authorization. <br>
Mitigation: Check accessibility flags and pagination results, then verify important citations against source papers before relying on them. <br>


## Reference(s): <br>
- [ClawHub skill page](https://clawhub.ai/sciverse/skills/academic-retrieval) <br>
- [Sciverse homepage](https://sciverse.space) <br>
- [Sciverse publisher profile](https://clawhub.ai/user/sciverse) <br>


## Skill Output: <br>
**Output Type(s):** [Text, Markdown, Configuration, Guidance] <br>
**Output Format:** [JSON responses containing paper metadata, text or Markdown excerpts, citation and reference records, and optional base64 image resources] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Requires SCIVERSE_API_TOKEN; optional SCIVERSE_BASE_URL is constrained to sciverse.space domains.] <br>

## Skill Version(s): <br>
0.11.0 (source: server release evidence, SKILL.md frontmatter, manifest.json) <br>

## Ethical Considerations: <br>
Users should evaluate whether this skill is appropriate for their environment, review any generated or modified files before relying on them, and apply their organization's safety, security, and compliance requirements before deployment. <br>
