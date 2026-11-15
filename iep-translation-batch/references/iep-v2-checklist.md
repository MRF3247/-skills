# 拆段 v2：spec / parent-inserts 组装清单

## spec-N.json 结构
```json
{"source": "词条绝对路径", "eol": "CRLF|LF",
 "start_line": N, "end_line": M,   // 1-based，含端点；按 ## 标题边界切，每段 40–90 行
 "out": "sec-N.json 绝对路径",
 "headings_fixed": {"行号": "译名（English）"},   // parent 预先定死，agent 照抄
 "notes": "该段专属细则"}
```
- 超长无小节的节按空行对半再切；参考文献节+作者块单独一段（翻译负载极轻）
- 作者块的中文行（姓名音译（英文）/邮箱/大学/国家）直接写在最后一段 notes 里让 agent 照抄，parent 不再补翻

## notes 必写三条
1. 参考文献条目**含散文描述的也整条不译**（不写明 agent 会把「条目」理解窄而译出描述）
2. 作者标题行若无 # 前缀（裸写 Author Information），notes 特判：仍按标题插「**译**：作者信息（Author Information）」
3. 告知 agent 不必为切片之外首现的术语补括注——术语一致性由 parent 术语表保证

## parent-inserts.json 组成（锚点=1-based 行号）
- frontmatter：after = 结束 `---` 的前一行的行号 → translator / translation_date / translation_format 三行
- 第一个 H1 行后：译注 callout 6 行（[!info] 标题 / 说明 / GLM 署名 / 术语对照 / 人名对照 / 其他对照）
- 正题 H1（第二个 H1）行后：「**译**：中文标题（English）」
- 各导言段行后：parent 自己翻的导言译文
- TOC 末项行后：「> **译**（目录）：」+ 每项「> - 中文名（English）」——与 headings_fixed 同源，锚点=目录末项实际行号（脚本算，别猜）

## TOC↔标题配对校验（写 parent-inserts 前必做）
TOC 条目剥编号前缀（`^\d+\. ` / `^[a-f]\. ` / `^[ivx]+\. `）+ 归一空白后与标题英文部分逐项比较；TOC 条目数 = 标题数（不含 TOC 标题行与作者行）。配对全对齐才写入。

## 组装前全局校验（每个 sec-N.json）
JSON 可解析｜anchor 全在区间内｜标题译行与 headings_fixed 逐字一致｜无「干跑/占位」残留｜无重复 (after,text)｜裸「**译**：」行是作者块规定标记不算错