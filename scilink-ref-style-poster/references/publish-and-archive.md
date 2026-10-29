# 发布与归档：飞书分栏插图 + 网页截图马克笔存证

只在偶尔需要时读。封面生成本体在 SKILL.md。

## 一、把成品插进飞书文档指定位置

一套固定五步，**一次插多张也走同一套**：

```bash
DOC=<document_id>   # 可由 wiki URL 读回；docs +fetch 会回 document_id

# 1) 定位目标容器：拿 grid / column / 空段落的 block id
lark-cli docs +fetch --doc $DOC --doc-format xml --detail with-ids \
  --scope keyword --keyword "<锚点标题>" --context-after 2 --as user

# 2) 上传：每张一次（media-insert 一律落在文末），逐个拿 file_token
lark-cli docs +media-insert --doc $DOC --file "./a.png" --as user   # -> block_id + file_token
lark-cli docs +media-insert --doc $DOC --file "./b.png" --as user

# 3) 把 token ��回目标栏位（每个空段落一次 block_replace）
lark-cli docs +update --doc $DOC --as user --command block_replace \
  --block-id <第1栏的空段落id> --content '<img src="<tokenA>" width="1080" height="1440"/>'
lark-cli docs +update --doc $DOC --as user --command block_replace \
  --block-id <第2栏的空段落id> --content '<img src="<tokenB>" width="2448" height="3264"/>'

# 4) 删文末两张临时图（用第 2 步返回的 block_id）
lark-cli docs +update --doc $DOC --as user --command block_delete --block-id <临时图 block_id>

# 5) 回读 grid 结构 + 下载回来算 sha256 校验内容没串
lark-cli docs +fetch --doc $DOC --doc-format xml --detail with-ids \
  --scope keyword --keyword "<锚点标题>" --context-after 2 --as user
lark-cli docs +media-download --token <回读的 src> --output ./v.png --overwrite
shasum -a 256 本地图.png v.png
```

坑：

- **每步写操作后 block id 全变**，不要拿上一轮的 id 继续用；替换完重新 fetch 再删临时图。
- 回读的 `name` / `mime` 可能是 `test.jpg`、`image/jpeg`，**不代表串图**；只认 sha256 一致。
- 三栏 grid 每栏占 1/3 版宽，竖图会缩得很小；如果只是存档没关系，要读者看清就得换栏宽比或只放一栏。
- 一次只插一张就去删临时图，会导致后续 block id 失效、返工；先把所有图传完，再统一 replace，再一次删。

## 二、新闻原文截图 + 马克笔高亮

用途：给稿件存证「原文标题 + 关键段落」。

1. `browser_navigate` 打开原文 → `browser_console` 清 DOM：只保留 `article`，删 `aside/footer/nav/.sharedaddy/.jp-relatedposts/iframe/script/form`；`body` 设 `width:1000px;background:#fff`；`h1` 加大字号，`p` 设 19px/1.6 行高。
2. 在 `h1` 前插一条 masthead（站点名 + 域名 + 日期），否则截图上没有出处。
3. 截两版：`scrollTo(0,0)` 截「带标题」版；滚到关键段落截「带论点」版（`scrollTo` 到目标段落 top − 300）。
4. 高亮**不要用 CSS background**（出来是均匀色块，视觉上就是数字高亮）。正确姿势：
   - `Range.getClientRects()` 取每行 rect，同 y 的合并为 min-x / max-right，存成 `lines.json`
   - `python scripts/marker_highlight.py 截图.png lines.json 输出.png`（逐列随机游走画边、起收笔渐弱、重涂加深）
5. 浏览器视口很宽时，用 `crop((0,0,内容宽度, 全高))` 裁掉右侧空白；两张裁成同一尺寸，进文档才整齐。
6. 自己复核一遍：高亮是否完整覆盖目标段落、有无多盖到相邻段、文字是否仍清晰。

## 三、交付检查

- 飞书：目标栏位里有图、临时图已删、sha256 一致
- 截图：带标题那张有出处（站点名 + 日期）、带论点那张高亮完整

## 四、同步到 GitHub（用户自己的 skill 仓库）

仓库：`https://github.com/MRF3247/-skills`（公开仓库）。两个 skill 一起推：`scilink-ref-style-poster` 与 `scilink-xhs-writing`，它们指向同一份规范，只推一个会立刻不一致。

**本地目录名不要用 `-skills`**：仓库名以连字符开头，`git clone <url> -skills` 会把目标目录当成 flag 解析，卡死或报错。用 `mrf-skills` 这类普通名字。

**大二进制会拖死全量 clone**：仓库约 20MB（PSD 7.5MB + 6 张参考图），`git clone` 与 `codeload` tarball 都可能卡到超时，而 `git ls-remote` 和 `api.github.com` 是秒回。所以只把要改的文本拉进工作区：

```bash
cd ~/Documents/GitProgram
git clone --filter=blob:none --no-checkout --depth 1 https://github.com/MRF3247/-skills.git mrf-skills
cd mrf-skills
git sparse-checkout set --no-cone '/*.md' 'scilink-xhs-writing/**' \
  'scilink-ref-style-poster/**/*.md' 'scilink-ref-style-poster/**/*.py'
git checkout main
```

**推之前逐文件 diff，不要直接 rsync 覆盖**：仓库里的副本可能是另一台机器或另一个工作分支改过的（实测仓库里两个 `references/*.md` 还写着旧目录名 `ref-style-poster`，本地早已改成 `scilink-` 前缀）。覆盖前先 `diff 仓库文件 本地文件`，确认本地确实更新才盖；仓库侧有本地没有的修正时先合再推。

```bash
for sk in scilink-xhs-writing scilink-ref-style-poster; do
  rsync -a --exclude 'assets' --exclude '__pycache__' --exclude '.DS_Store' \
    ~/.hermes/skills/$sk/ $sk/
done
git add -A && git status --short      # 逐行核对：只应有该改的文件
# 版本号从 SKILL.md frontmatter 取；本机全局身份为空，必须 -c 现场传入
git -c user.name="MRF3247" -c user.email="maolpha@hotmail.com" \
  commit -m "update: <skill> v<版本>"
git push origin main
```

**验证以远端树为准**（push 打印成功不等于内容对）：

```bash
curl -s "https://api.github.com/repos/MRF3247/-skills/git/trees/main?recursive=1"
# 远端每个 blob 的 size 与本地 os.path.getsize 逐条比对；assets/ 跳过（sparse 未拉，两边字节数一致即未变）
```

坑：

- **别把 `rm -rf <工作区>` 写在 background 命令的开头**：后台命令会在调度晚得多的时候才真正执行，前面那次 clone 可能已经跑完，于是它把你正在用的工作区删掉了（后续所有命令都报 `No such file or directory`，因为 terminal 会话的 cwd 已不存在）。要重建就前台 `rm -rf`，或在每条命令里显式传 `workdir`。
- 本机 **没有 gh CLI**，不要用 `gh repo ...`。HTTPS push 凭据在 `~/.git-credentials`（helper=store），SSH key 在 `~/.ssh/id_ed25519`，两条路都能推。
- 全局 `git config user.name/email` 为空，commit 必须现场用 `-c` 传入，否则报身份未知；不要改用户全局配置。
- 仓库约 20MB，单文件都远低于 100MB，**不要为了瘦身去转码参考图**——那会连带改掉 SKILL.md 里的路径。
- `assets/` 本地与远端字节数通常完全一致，不需要重传；要更新参考图时单独把该文件拷进去再 `git add`。
