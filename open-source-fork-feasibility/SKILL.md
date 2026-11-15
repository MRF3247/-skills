---
name: open-source-fork-feasibility
description: "Use when 判断一个 GitHub 仓库能否改造/换领域（fork 可行性），或用户问某仓库是干什么的。"
---

# 开源项目 fork 可行性评估

## 触发
用户丢一个 GitHub 仓库，问「这是干什么的」或「我想 clone 下来基于它换成别的（换模型 / 换领域 / 换数据），可行性高吗」。用户要的是**可下结论的评估**，不是功能复述；读完代码就答「大概可以」等于没答。

## 流程

### 0. 先判仓库类型，别把 prompt 库当项目审
看 `size`（KB）+ 文件数 + 提交数就能分流，**内容型仓库不需要 clone 和实测**：
- `size` 个位数 KB、根目录 1-3 个文件、`created_at` 与 `pushed_at` 相差几分钟（建库当天推完就停）→ **内容型**：prompt 合集 / awesome 清单 / 模板集 / 单篇文档。给的是「这份内容写了什么 + 值不值得用」，不是 fork 可行性。
- 有源码目录、几十个文件、多次提交 → 代码型，往下走完整流程。

一次拿全：

```bash
curl -s https://api.github.com/repos/<o>/<r> | python3 -c "import json,sys;d=json.load(sys.stdin);print({k:d.get(k) for k in ['description','created_at','pushed_at','size','language','stargazers_count','forks_count','license']})"
curl -s "https://api.github.com/repos/<o>/<r>/contents/<dir>" | python3 -c "import json,sys;[print(x['type'],x['size'],x['name']) for x in json.load(sys.stdin)]"
curl -s "https://api.github.com/repos/<o>/<r>/commits?per_page=10" | python3 -c "import json,sys;[print(c['commit']['author']['date'], c['commit']['message'][:80]) for c in json.load(sys.stdin)]"
```

**读文件正文别直连 raw.githubusercontent.com**：它常挂到超时（一次 curl 卡满 180s）。用 `web_extract` 直接喂 raw URL，或走 jsDelivr 镜像 `https://cdn.jsdelivr.net/gh/<o>/<r>@<branch>/<path>`。注意 `web_extract` 吐的是转换后 markdown，会残留 `\*\*` 转义和 `- \` 这类空悬续行——看到悬空 bullet 就是**原文本身残缺**（多半从别处复制时被截断），要在结论里点出「原文不完整，模型只能脑补」，不要当成抓取失败。

### 1. 先看元数据，别先读 README
`curl -s https://api.github.com/repos/<owner>/<repo>` 取 `description / language / stargazers_count / forks_count / license / created_at / pushed_at / homepage`。
- ⚠️ **README 可能是没改的脚手架模板**（starter 原文），照抄会把仓库介绍成另一个东西。README 与 `package.json`、目录结构矛盾时以代码为准（本次实例：README 是 vinext-starter 模板，真实项目是 3D 解剖浏览器）。
- `license: null` = 保留所有权利，改造后能否商用无授权 → 必须主动提示。
- 线上 demo 可能已下线（homepage 打开是 deployment paused）→ 结论里说明「只能看代码，跑起来要自己 clone」。

### 2. 看结构与规模
`https://api.github.com/repos/<o>/<r>/git/trees/<branch>?recursive=1` 一次拿全量文件树：统计目录分布、按 size 排最大的若干文件（判资产体积、定位核心代码层）。

### 3. 判耦合度——决定改造成本的真正指标
在核心代码里 grep 业务实体名（领域名词、实体 id），看它们出现在哪一层：
- 核心渲染 / 业务层**不含**实体名 → 数据驱动，换领域 ≈ 改数据文件，成本低。
- 硬编码集中在入口 / UI 组件 → 记下具体位置与条数，写进工作量表。

### 4. 实测——决定性证据，不靠读代码下结论
clone 到 `/tmp` → 装依赖 → 构建 → **替换 1 个数据 / 资产** → 起服务 → 浏览器实际看渲染结果（必要时截图给用户看）。
- 换一个**毫不相干的**资产最能证明解耦：换掉后照常渲染 = 强证据（本次实例：把解剖模型换成科幻头盔，页面照渲、坐标自动吸附）。
- **构建链绕道**：`package.json` 的 scripts 里有标准框架脚本（`build:next` 这类）时，直接用 `npx next dev` 起，绕开项目自带的小众构建 / 云平台依赖——实测更省事，也让用户以后不被平台绑住。
- 起后台 dev server 后**务必 kill 并确认端口释放**（`lsof -ti:<port>`），别把进程留在用户机器上。

### 5. 出结论（用户要的形态）
可行性判断（高 / 中 / 低）→ 实测证据（做了什么、结果如何）→ **要改的清单表（按工作量排）** → 坑清单 → 最小验证路径（先砍到最小范围跑通，再决定铺不铺全量）。保留实验副本并告知路径，主动问是否要挪到工作目录或做成「精简起手版」。

## 通用坑（评估时必查）
- **内容型仓库不要硬走实测**：对 prompt 合集 / 清单类仓库做 clone + 装依赖 + 起服务是纯浪费，用户问「帮我看看这个项目」时他要的是一页判断：它是什么、写了什么、质量如何、对眼下活儿有没有用。
- **强类型字典会放大工作量**：`Record<EntityId, Content>` + 联合类型 id 这类结构意味着增删一个实体要同步**所有**语言 / 主题文件，缺一个就编译报错——这通常是最大成本项，必须单独列出来，并给出「先砍到单一语言 / 单一主题」的降本路径。
- **资产自动归一化 ≠ 语义也自动化**：模型 / 图片被自动缩放居中、热点坐标自动吸附到表面，只能说明资产层解耦；语义标注（热点、标签、文案）仍要人工重做。别把「能渲出来」说成「改造成本低」。
- **内嵌资源体积**：几十 MB 的资产会顶到打包 / 首屏体积，顺手给一句压缩建议（项目已内置解码器就直接利用）。
- 结论要落到「值不值得改」：解耦好但无授权、资产要重做、文案要全量重写——把这几条摆出来让用户自己拍板。
