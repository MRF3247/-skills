# 把选题清单写进飞书「内容选题库」

用户说「整理到飞书，我再看着挑」时，交付形态是**可勾选的选题卡片文档**，不是聊天里再贴一遍。

## 步骤

```bash
# 1. 解析 wiki 节点（拿 obj_token / obj_type，确认是 docx）
lark-cli wiki +node-get --node-token '<wiki_url>' --as user --format json

# 2. 看现状（空文档只返回 <title>）
lark-cli docs +fetch --doc '<obj_token>' --as user --format json

# 3. 本地写好 XML，整段追加
lark-cli docs +update --doc '<obj_token>' --command append --content '@./topics.xml' --as user --format json

# 4. 回查结构（标题层级、分类是否落地）
lark-cli docs +fetch --doc '<obj_token>' --as user --scope outline --max-depth 2 --format json
```

- `--content '@./file.xml'` 可直接吃本地文件，避免超长 XML 在 shell 里转义出错；文件放 CWD 时用相对路径。
- 空文档用 `append` 即可，不要 `overwrite`（会丢评论）。

## XML 骨架

```xml
<callout emoji="📌" background-color="light-blue"><p><b>数据快照：YYYY-MM-DD</b>。筛选标准…</p><p>受众锚定：…</p></callout>

<h1>一、分类名（括号里写这类的特征）</h1>
<h2>A1. 题材标题</h2>
<ul>
<li><b>时间</b>：…</li>
<li><b>事件</b>：一句话</li>
<li><b>为什么戳</b>：落到受众自身处境</li>
<li><b>建议角度</b>：…</li>
<li><b>素材</b>：<a type="url-preview" href="URL">标题</a>（一句话简介）</li>
</ul>
<checkbox done="false">选这条</checkbox>

<h1>五、优先级建议</h1>
<table><colgroup><col width="100"/><col width="220"/><col width="200"/><col width="260"/></colgroup><thead><tr><th background-color="light-gray"><p>优先</p></th>…</tr></thead><tbody>…</tbody></table>
```

## 规则

- 每道题末尾一个 `<checkbox done="false">选这条</checkbox>`——用户的原话是「我再看着挑选」，勾选框就是他挑的动作。
- 链接一律 `<a type="url-preview" href="…">标题</a>`，标题写成「媒体/机构：这一条讲什么」，每条附一句话简介。
- 标题层级连续（h1 → h2，不跳级）；表头底色 `light-gray`，彩色只用于表达状态。
- 结尾单列一节「共同注意事项」：哪条要回查一手源、哪条政策有省份差异、哪条时效将过。
- 写完必须 `--scope outline` 回查，确认分类与题目全部落地再回复用户。

## 坑

- 微信公众号正文抓取会丢图片（`![]()` 空 alt）与页脚组件，选题文档的配图另找，不要指望原页。
- 用户后续会把这份文档当长期库用：新一批选题用 `append` 追加为新章节并更新导语里的快照日期，不要重建整篇。
