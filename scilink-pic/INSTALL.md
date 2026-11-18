# 装好它：scilink-pic（刀客轻研视觉物料）

这套 skill 能出 7 种版式，最常用的三种是：

| 想做什么 | 入口 |
|---|---|
| **论文速读卡**（一篇论文摘要做成 2 页 3:4 卡） | `templates/paper_read_card.html` → `scripts/compose_paper_card.py` |
| **新闻速读卡**（一条新闻原文译成中文做成 N 页 3:4 卡） | `templates/news_bilingual.html` → `scripts/compose_news_card.py` |
| **医学插画海报 / 插画封面**（AI 生图 + 压字） | libtv「豆包 Seedream 5.0 Pro」出图 → `scripts/warm_grain.py` / `finalize_cover.py` / `add_cover_text.py` |

其余四种：政策速读（`policy_shot.html`）、P2/P3 来源页截图（`shot_p2p3.py` + `crop_highlight.py`）、引流二维码卡（`lead_qr_card*.html`）、单图长海报。

## 1. 依赖

```bash
# 出图/排版都要
pip install pillow numpy matplotlib
# 截图类版式（P2/P3、HTML → PNG）
pip install playwright && playwright install chromium
# 只想用 Chrome 截图的话，本机装了 Chrome 即可，脚本走 --headless 调它
```

`lark-cli` 仅在需要把图写回飞书文档时才要；不写飞书可忽略。

## 2. 字体（关键，不装会掉字）

模板与脚本默认读 macOS 本地字体目录 `~/Library/Fonts/`：

| 用途 | 字体文件 |
|---|---|
| 新闻速读卡正文/标题 | `SourceHanSerifSC-Regular/Medium/SemiBold/Bold/Heavy.otf`（思源宋体 SC） |
| 论文卡、压字、长海报 | `MiSans-Regular/Medium/Demibold/Bold/Heavy.ttf` |
| 拼图、部分脚本 | `SourceHanSansSC-Heavy.otf`、`AlibabaPuHuiTi-3-115-Black.otf` |

- 字体装到 `~/Library/Fonts/` 后即可直接用（模板里写的是这个绝对路径）。
- 装在别处或换字体：批量改路径即可 ——
  ```bash
  grep -rl "Library/Fonts" templates scripts | xargs sed -i '' 's|/Users/你的用户名/Library/Fonts|/你的字体目录|g'
  ```
- CSS 里已经写了 `'MiSans', -apple-system, sans-serif` 与 `'SourceSerif', 'PingFang SC', serif` 兜底：没装自定义字体时不出乱码，但**字重和气质会变**，正式出图请装字体。

## 3. 品牌资产

- `assets/logo.png` 已随仓库提供，模板里用相对路径 `../assets/logo.png` 引用，克隆下来直接可用。
- 未随仓库提供（属于品牌私有素材，请换成自己的）：`assets/cover-template.psd`（封面 PSD 模板）、`assets/ref-set/`（5 张风格参考图，供 AI 生图当参考）、引流卡里的客服二维码照片。
- 生图引擎默认是 libtv + 豆包 Seedream 5.0 Pro。没有 libtv 时可换成任何文生图（Midjourney / SD / 即梦），只要出 3:4、2K 上下，后续压字与后处理脚本不依赖具体引擎。

## 4. 快速跑一张

```bash
mkdir -p out      # --out 是文件路径（多页时自动变成 out/paper-1.png、-2.png…），目录要先建好
# 论文速读卡（2 页起）：内容通过参数传，--block 可重复，写法是 英文||中文
python3 scripts/compose_paper_card.py \
  --out out/paper.png \
  --paper-title "中文标题" --paper-title-en "English Title" \
  --section "Abstract" --section-cn "摘要" \
  --block "Background 原文句||背景 中文译句" \
  --block "Result 原文句||结果 中文译句" \
  --source "来源：期刊名 · 2026" --page-tags "关键词1|关键词2|关键词3"

# 新闻速读卡（N 页，JSON 驱动；段落间可插通栏图 {"img": "file:///…png", "figcap": "图注"}）
python3 scripts/compose_news_card.py data.json --out-dir out/ --name news

# 底部留白体检（每页内容底到页脚蓝条应 ≤5%，尾页 ≤10%）
python3 scripts/check_bottom_gap.py out/news-01.png
```

## 5. 三条硬规则（别踩）

1. **页脚蓝条绝对固定**：`y=1370`、高 `70px`，任何页面都不许移。内容放不下时先缩字号、再删修饰语、最后把整块推到下一页。
2. **新闻速读卡的卡面正文＝新闻原文逐段中文译文**，不要拿自己写好的公众号稿/云文档正文顶替。
3. **文字里穿插图表**：同一页出现 3 组及以上对比数字才插一张通栏小图，图块不拆页；1–2 个数字直接写正文。
