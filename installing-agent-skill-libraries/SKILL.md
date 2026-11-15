---
name: installing-agent-skill-libraries
description: 装外部 GitHub agent-skill 库：小库用 npx skills add 全量装、大库 tap+精装核心；含断链排查清理。
---

# 安装大型外部 agent-skill 库进 Hermes

## 触发条件
用户给一个 GitHub 仓库名（通常是**几百个 skill 的大型 agent-skill 库**，如 K-Dense-AI/scientific-agent-skills、jaechang-hits/SciAgent-Skills、ClawBio/ClawBio、aipoch/medical-research-skills），要求"装这几个"或"帮我装这个 skill 库"。

## 核心原则（最重要）
**不要全量平铺装进 `~/.hermes/skills/`**。一个 160~400 个 skill 的库全铺开，会让 Hermes 每轮 system prompt 的 `available_skills` 索引暴涨 —— 实测**每个 skill 条目约 55 tokens**（482 个 = 93,344 字符 ≈ 26,670 tokens/轮，与聊什么无关，固定成本），另有稳定性风险。正确做法是"**登记为源 + 完整库留存本地 + 精装核心**"三步。

## 装之前先判断值不值得装

用户发来一个仓库问「好不好用 / 有没有同类」时，别只读 README 就下结论：

- **先看规模与维护**：stars、最近提交、`skills/` 下目录数——判断这是官方主推还是很久没动的小摊。
- **找第三方横评**：同一任务被多个技能做对比的榜单（如视频类 skill 用同一个 brief 比耗时与成片）比 README 可信得多；同类清单站（awesome-* / agentskillshub 类）用来列「有哪几家」，别拿它的星级当质量结论。
- **实测最小用例**：装完跑一个最小可验证动作（渲染一帧 / 调一个只读接口），把真实输出与耗时报给用户。没跑通的「好用」不算结论。
- **分清两层价值**：官方技能普遍解决「做得对、跑得稳」，不解决「做得好看」——同类横评里官方件往往跟「不装技能直接做」的自研差不多，要的是自己的设计方向。交付时把这两层说开，别把「跑通」讲成「做得好」。

## 先按库大小选装法
- **小库（≲50 个 skill，如 dontbesilent2025/dbskill 的 33 个）**：官方 CLI 一条命令全量装，它会落到 `~/.agents/skills/` 并自动在 `~/.hermes/skills/` 建软链，不用手动 cp。
- **大库（上百~几百个）**：走下面的"三步装法"（tap 登记 + clone + 精装核心），避免系统提示膨胀。

## 小库快速装（优先）
```bash
npx -y skills add <owner>/<repo> -g --all
```
- 装完验证（会解析软链，确认每个 skill 真有 SKILL.md）：
```bash
cd ~/.hermes/skills && for f in <前缀>*; do [ -e "$f/SKILL.md" ] || echo "BAD: $f"; done
```
- 输出里的 `✗ <skill> → Eve/PromptScript: does not support global skill installation` 是**噪音**（这两种 agent 不支持全局装），不代表 Hermes 装失败，别据此判失败或重装。
- 想让用户以后能自助更新（多数库自带 `/dbs-update` 类入口），保持官方 CLI 装法，别改成手动 cp 副本。

### clone 失败时：用 codeload tarball 本地装（别在 `npx skills add owner/repo` 上重试）
`Failed to clone … Error in the HTTP2 framing layer` 或 `Couldn't connect to server`（443 超时）＝ GitHub 直连不通，重跑同一条命令只会再等一遍超时。改走 codeload（它通常仍可达）取同一份代码再本地装：
```bash
curl -sL --max-time 120 -o /tmp/lib.tar.gz \
  "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main"
tar xzf /tmp/lib.tar.gz -C /tmp
npx -y skills add /tmp/<repo>-main -g -y          # 结果与远端装完全一致
```
- 分支不是 main 就换 `refs/heads/master`；先 `curl -s -o /dev/null -w '%{http_code}'` 探一下 `codeload.github.com` 再下。
- 本地目录装完同样落在 `~/.agents/skills/<name>` 并自动在 `~/.hermes/skills/` 建软链，`skill_view(name)` 当场可读，不用重启。

### 更新已装的库到上游最新（含补齐缺失技能）
本地装过的库会落后上游，而且上游常有**新增**技能（新文件夹，只有逐个覆盖才会补上）。更新前先比对版本，别盲覆盖：
```bash
curl -sL --max-time 120 -o /tmp/lib.tar.gz "https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main"
tar xzf /tmp/lib.tar.gz -C /tmp
for d in /tmp/<repo>-main/skills/*/; do echo "$(basename $d) $(grep -m1 '^version:' $d/SKILL.md)"; done   # 与本地同名 SKILL.md 对比
```
确认要更新后：先整包备份，再逐个覆盖，缺的会顺带补齐：
```bash
tar czf ~/.hermes/backup/<repo>-$(date +%Y%m%d).tgz -C ~/.hermes/skills/<category> $(ls /tmp/<repo>-main/skills)
for n in $(ls /tmp/<repo>-main/skills); do rm -rf ~/.hermes/skills/<category>/$n; cp -R /tmp/<repo>-main/skills/$n ~/.hermes/skills/<category>/$n; done
```
- 用 `rm -rf` + `cp -R`，不要直接 `cp -R` 覆盖：上游删掉的文件会留在旧目录，新旧混杂。
- 上游没有、本地有的（自建或被上游裁掉的）不在循环里，不会被误删——别为了“干净”把整个 category 清空。
- 覆盖后 `skills_list` 确认新技能进了索引；实测新建目录当场可 `skill_view`，不用重启。

### 装完要配 API key 的技能
有些 skill 只是接口包装（微信读书、第三方 API），装完不带凭据等于不能用。装完立刻做完这三步，别等用户来问「为什么没反应」：
1. 从用户给的凭据文件取 key（RTF / txt 先 `textutil -convert txt -stdout` 或 `read_file`），**只打印脱敏前缀确认取到了，不打印明文**。
2. 幂等写进 `~/.hermes/.env`（已有则替换，没有则追加）：`re.sub` 定位 `KEY=.*` 改值，或用 Python 读改写，别用 `echo >>` 堆重复行。
3. 立刻发**一个只读的真实请求**验证（搜索/列表类接口），回 `errcode` 与条数即证明 key 与身份都通；测不通再说，别把「装好了」当结论交付。
- ⚠️ `~/.hermes/.env` 是 Hermes **启动时**注入的：当前会话的 terminal 里 `echo $KEY` 仍为空，必须重启后才自动带上。交付时给用户一行兜底：`export KEY=$(grep KEY ~/.hermes/.env | cut -d= -f2)`。

## 断链排查与清理（软链失效）
`~/.hermes/skills/` 的条目可能是指向 `~/.agents/skills/<name>` 的**软链**。源头被删/迁移后，技能名下仍挂着目录但内容为空 → 该技能**实际不可用**（`skill_view` 失败，系统提示索引里也看不到它），用户以为"装了"。
- ⚠️ **`find` 默认不跟进软链**：`find dbs* -name SKILL.md` 返回 0 条，**不代表没装**。判有效性要用 `[ -e "$f/SKILL.md" ]`（解析软链）或 `ls -dL`。
- 先清点并留档（删了可照单重装）：
```bash
cd ~/.hermes/skills && mkdir -p ~/.hermes/backup && out=~/.hermes/backup/broken-symlinks-$(date +%Y%m%d).txt
for f in *; do [ -L "$f" ] && [ ! -e "$f" ] && echo "$f|$(readlink "$f")"; done > "$out"; cat "$out"
```
- 删除：同一条循环把 `echo ...` 换成 `rm "$f"`；删完再跑一次应剩 0 条。
- 用户说"清理死链"就是清**全部**断链，不只他这次点到的那个前缀（往往一次能翻出几十条跨库断链）——一并清掉，并在交付时说明各自来源（如 lark-* 源自 lark-cli 技能包），需要时可重装。

## `skill_view` 报 not found 的另一半病因：技能被「归档」（最容易被误判成没装）
症状：用户问"我是不是装了 X"，`~/.hermes/skills/` 下**能看到目录名**，但 `skill_view(X)` 返回 `Skill 'X' not found`，磁盘文件却完整。
机制：技能被移进 `~/.hermes/skills/.archive/` —— **隐藏目录，Hermes 扫描时直接跳过**。而 system prompt 的 `available_skills` 清单可能仍列着它（清单与磁盘不同步），所以**"清单里有"不等于"能加载"**；两者要分开验。
诊断（先看它落在哪，别急着重装）：
```bash
find ~/.hermes/skills -maxdepth 2 -iname "*<name>*"     # 命中 .archive/ 就是这个病
ls -d ~/.hermes/skills/<name> ~/.hermes/skills/*/<name> 2>&1
```
修复：**不要去 GitHub 重装**（归档件往往和上游逐字节一致，重装只是白费等下载）。复制回活动树即可：
```bash
cp -R ~/.hermes/skills/.archive/<name> ~/.hermes/skills/<category>/<name>
sleep 1   # 复制完当场 skill_view 验证；实测无需重启会话，索引是实时扫盘的
```
分类取 frontmatter 的 `metadata.hermes.category`；没有就按 system prompt 清单里的分组归位；都没有再平铺到 `~/.hermes/skills/` 根。

### 批量恢复的规矩
- 用户只点名一个就恢复一个；说"全部恢复"才全量，**先把数量和清单报给他确认**再动（恢复会把之前有意清掉的旧技能请回来）。
- 用 `cp` 不用 `mv`：归档副本先留着，等用户确认后再谈清理。
- 恢复后抽查验证：`skills_list(category='<某小分类>')` 看数量是否增加，比逐个 `skill_view` 省 token。
- 清 `.archive` 前必须打包留档，再删：
```bash
tar -czf ~/.hermes/backup/skills-archive-$(date +%Y%m%d).tar.gz -C ~/.hermes/skills .archive
rm -rf ~/.hermes/skills/.archive
```

## 同步到自有技能仓库 / 来源归因
用户问「要不要把这些技能同步到我的 GitHub 技能仓库」时，先做**来源归因**（自带 / 托管安装 / 第三方大库 / 自建），再挑着推，绝不全量镜像。归因脚本、A/B/C 三档策略、sparse-checkout 仓库的 `git add --sparse` 坑与推送后核验命令，见 [技能库盘点与同步](references/skill-library-inventory-and-sync.md)。

## 技能库体检与瘦身（断链 / 归档 / 重复）
用户问"技能库是不是有问题"或要瘦身时，跑三条检查 + 一次成本核算，脚本已备好：
```bash
bash ~/.hermes/skills/devops/installing-agent-skill-libraries/scripts/skill_library_health_check.sh
```
它会一次性输出：① 断链条目（软链失效 = 没装）② `.archive` 归档数（= 不可用）③ 技能数 / 索引字符 / tokens·轮 ④ 疑似重复族（同前缀 ≥3 个）。

- 重复族的识别信号：`bilibili-*`、`douyin-*`、`feishu-*`、`html-*`、`pdf-*`、`medical-*` 这种**同前缀成串**的，通常是**多轮会话各写了一次**，不是一个人有意分档。
- **不要擅自删或合并**。给用户一张"主题 / 现有 / 建议保留 / 省多少"的表让他挑；合并时先把两份内容的差异并进保留项，再删另一个。
- 报告要带上成本账（删 N 个 ≈ 省 N×55 tokens/轮），用户才好判断值不值。
- ⚠️ 技能数和 token 开销要报**实测值**（脚本算出来的），别估。

## 三步装法

### 1. tap 登记为 skill 源（轻量，不占用系统提示）
```bash
hermes skills tap add <owner/repo>      # 登记为一个源，写进 config
hermes skills tap list                  # 验证 PATH 指向各库的 skills/
```
⚠️ **tap 的 `hermes skills search --source github <词>` 对几百 skill 的仓库极慢/不稳定**（逐库 fetch，常常超时/返回空）。所以 tap 只是"登记源"，别依赖它的 search 装 skill。

### 2. git clone 完整库到本地归集目录
```bash
mkdir -p ~/.hermes/skill-libs && cd ~/.hermes/skill-libs
git clone --depth 1 --quiet "https://github.com/<owner>/<repo>.git" <name>
```
⚠️ 这些库往往自带大量资产/文档/基准图（可占几百 MB~1GB+），clone 后注意空间。可后续用 sparse-checkout 只留 `skills/` 瘦身。

### 3. 精装核心 skill（真正进 `~/.hermes/skills/`，可被调用）
从 clone 的库里挑出**最对口的那几个**，**整目录**复制进 skills 树：
```bash
cp -r ~/.hermes/skill-libs/<repo>/skills/<skill-name> ~/.hermes/skills/<category>/
```
- ⚠️ **必须 `cp -r` 整个 skill 目录**（含 SKILL.md + references/ + assets/ + scripts/），只拷 SKILL.md 会缺引用文件。skill 内部往往引用相对路径的 references/assets/scripts。
- category 用现有分类（如 `research`/`devops`），沿用 `~/.hermes/skills/<category>/<skill>/` 结构。
- 用 `skills_list` 验证 Hermes 扫到了（frontmatter 必须有 name/description）。

## 关键坑
- **Windows 打包的 zip 中文文件名**：`unzip` 报 `Illegal byte sequence`（非 UTF-8 文件名被按 cp437 解码）。用 Python zipfile 还原：对 `flag_bits & 0x800 == 0` 的条目，`info.filename.encode('cp437')` 先试 `decode('utf-8')` 失败再 `decode('gbk')`，逐条落盘。不要用 `ditto -x`（同样乱码）。
- **库间同名冲突**：多个库有同名 skill（如 K-Dense 和 aipoch 都有 `hypothesis-generation`），各装一个同 name 会重复/互相覆盖 → 每个 skill 名只装一个代表，别都装。
- **执行型 skill 需要运行时**：生信/统计库的 skill 常依赖其 Python CLI（`clawbio`）、R/Bioconductor、statsmodels/pymc 等。装进去只是"方法/框架"层，真要跑分析得再装对应工具环境。
- **验证装成功**：`skills_list` / `skill_view(name)` 能看到即生效——实测 `npx skills add` 装完**当前会话就能 `skill_view` 到新技能，不用重启**（文件已在 `~/.hermes/skills/`）；只有索引明显没刷新时才让用户重启会话。

## 交付时向用户交代
- 列出**装了多少核心 skill + 各自用途**；顺带报告清理了 N 个断链及其备份清单路径，标明完整库在 `~/.hermes/skill-libs/`、可随时补装单个。
- 说明为什么不全量塞（系统提示膨胀），以及哪些是执行型需补运行时。
- 主动提空间占用（skill-libs 可达 1GB+），问要不要瘦身。
- 技能库体检/瘦身类请求：把实测成本账（技能数 × ≈55 tokens/轮）和重复族清单一起给出，让用户按表挑，别替他决定删哪个。
