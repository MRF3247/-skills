# 技能库盘点（来源归因）与同步到自有技能仓库

用户问「这些技能要不要同步到我的 GitHub 技能仓库」时用这份。先归因、再挑、最后推；**不要全量推**。

## 1. 来源归因（先分清哪些是「自己的」）

`~/.hermes/skills/` 是混装：自带的、托管安装的、第三方大库、自己沉淀的全在一起。用隐藏清单文件归因：

| 文件 | 含义 |
|---|---|
| `.bundled_manifest` | Hermes 自带的 skill（`name:hash` 逐行），跟版本走 |
| `.arkcli-managed-skills.json` | arkcli 托管的 skill，重装即得 |
| `.redskill-lock.json` | redskill 安装的条目（含 source/sha256） |
| `.hub/lock.json`、`.hub/taps.json` | skill hub / tap 安装记录 |
| `.curator_backups/` | 内部备份快照，**体积巨大且无备份价值，永远不要推** |
| `.archive/` | 已归档即不可加载，不要推也不要在统计里计入「可用」 |

一次算出四类计数：

```python
import json, os, glob, re
root = os.path.expanduser('~/.hermes/skills')
bundled = {l.split(':')[0] for l in open(f'{root}/.bundled_manifest') if ':' in l}
ark = set(json.load(open(f'{root}/.arkcli-managed-skills.json'))['skills'])
red = set(json.load(open(f'{root}/.redskill-lock.json'))['skills'])
names = []
for p in glob.glob(f'{root}/**/SKILL.md', recursive=True):
    if '/.archive/' in p or '/.curator_backups/' in p or '/.hub/' in p:
        continue
    txt = open(p, encoding='utf-8').read(600)
    m = re.search(r'^name:\s*(\S+)', txt, re.M)
    names.append(m.group(1).strip('"\'') if m else os.path.basename(os.path.dirname(p)))
print(len(names), sum(n in bundled for n in names), sum(n in ark for n in names), sum(n in red for n in names))
```

可用技能总数要排除隐藏目录，否则会被 `.curator_backups` 冲高：

```bash
find . -name SKILL.md -not -path './.archive/*' -not -path './.curator_backups/*' -not -path './.hub/*' | wc -l
```

体积归因用 `du -sh */ | sort -rh | head`，典型大头是第三方大库（如 `research/` 数百 MB）、带素材的自建技能（工作台类几十 MB）、`.curator_backups/`（几百 MB）。

## 2. 同步策略：挑着推，不是镜像

给用户三个档位（默认推荐 A），不要替他决定：

| 方案 | 内容 | 适用 |
|---|---|---|
| A | 只推自建/沉淀的（根目录直属 + 自建所属分类），剔除素材大文件，只留 SKILL.md / scripts / references / templates | 备份价值最高，clone 下来能直接用 |
| B | A + 自己改造过的第三方 skill | 确实改过别人的才选 |
| C | 全量 | 需 Git LFS，几 GB，不推荐 |

永远不推：`.curator_backups/`、第三方大库（`research/`、`creative/`、`lark-*`、`arkcli-*`、`dbs-*` 等可重装的）、运行期产物。

配套规矩：用户要求「别搞太多 skill、同类合并」时，把新技能并入已有 class-level 技能，保持名字前缀统一（如 `scilink-`），而不是新建平行的小技能。

## 3. 推送到自有技能仓库（含 sparse-checkout 坑）

仓库通常已克隆在本地（如 `~/Documents/GitProgram/<repo>`），推送前先确认远端与本地一致：

```bash
cd <repo> && git remote -v && git ls-remote --heads origin && git log --oneline -3
```

⚠️ **这类仓库常开了 sparse-checkout**：`git add <新目录>` 会被静默跳过，只打印 `matched paths that exist outside of your sparse-checkout definition`，然后 `git commit` 因无变更而失败（exit 1）。正确顺序：

```bash
cp -R ~/.hermes/skills/<cat>/<skill> ./<skill>
git add --sparse <skill>                                  # 必须带 --sparse
git -c user.name="Hermes Agent" commit -m "add: <skill>（一句话用途）"
git sparse-checkout add '<skill>/**'                      # 让以后 pull 能落盘
# 如果之前误加成了不带 /** 的裸目录，用 set --stdin 重写全量 pattern：
printf '/*.md\n<other>/**\n<skill>/**\n' | git sparse-checkout set --no-cone --stdin
git push origin main
```

推送后必须核验，不能只信 push 的返回码：

```bash
git ls-remote --heads origin           # 远端 HEAD 应等于本地 commit
git status -sb                          # 应为 ## main...origin/main（无 ahead/behind）
git show origin/main:<skill>/SKILL.md | head -5   # 远端真能读到内容
```

## 4. 交付时说清缺口

推完给一张「本地 vs 仓库」差异表：已同步 / 仓库名过期（本地改过名）/ 本地有仓库无（未归档）/ 仓库有本地无（遗留），并问要不要一次性对齐。改名或删除旧条目前先报清单，别自行清理。
