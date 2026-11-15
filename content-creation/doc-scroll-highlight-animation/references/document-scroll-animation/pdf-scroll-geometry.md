# PDF 滚动浮出：坐标取法与几何算式

## 1. 词级取框 ＋ 自证

```python
import fitz  # PyMuPDF
page = fitz.open(pdf)[0]
words = page.get_text("words")          # (x0,y0,x1,y1,word,block,line,word_no)
# 目标短语：把词拼成连续串再定范围，勿按整行切——跨行会误涂
rect = fitz.Rect(x0, y0, x1, y1)
assert page.get_text(clip=rect).strip() == expected_text   # 反向自证：框内只有目标句
```

- **每个框都要 `get_text(clip=rect)` 回读自证**，这是唯一能证明「没夹带别的行」的手段；写进脚本，别只写检查思路。
- 跨行的短语（如 `… or Stage III colorectal cancer ("CRC")`）拆成逐行独立框，高亮才不会整行误涂。
- 坐标同时给两套：PDF pt（排版用）＋ 300dpi 像素（`px = pt × 300/72`，渲染裁切用）。JSON 里另存笔迹范围，供渲染侧直接用。

## 2. 页渲染与浮出卡片

```python
page.get_pixmap(dpi=300).save("page1_300dpi.png")             # 页面底图
page.get_pixmap(dpi=600, clip=rect).save("card_600dpi.png")    # 被标段落高分辨率裁切
```

浮出实现：原位盖一块白纸补片（与页面底色一致）→ 同一块原文放大抬起 ＋ 投影 → 背景压暗 45–52% ＋ 0.8px 轻模糊。进入 smoothstep ≈0.5s、回位 ≈0.4s，全程不切镜头。

## 3. 字号天花板（换算一次，省一次重渲）

```
px_per_pt_max = 画幅宽 / 栏宽(pt)        # 整行不折行的物理上限
8pt 正文 / 532pt 栏宽 / 1920 画幅 → 1920/532 = 3.61 px/pt ≈ 28.9px（扣 40px 边距 ≈ 28.3px）
```

- 想更大只有两条路：① 拆行重排（不再是「同一块原文」，权威性受损）；② 把被扫的**短语**用 600dpi 单独裁切做二级放大（如 143pt 短语 × 5.5 = 787px 放得下）。
- 短片里不建议加二级放大：多一次抬起＝多一次跳动，破坏一镜到底。

## 4. 留白与相机缩放

卡片左右留白要按**缩放后**的屏幕宽度算：

```
可用宽 = 画幅宽 / 相机终值        # 相机 1.000→1.035 时按 1.035 计
```

按 stage 坐标直接算会高估约 3.5%，实测留白比设计值少 ~30px（投影被挤出画幅，视觉读成「白带」）。卡片裁切只取正文栏宽本身、白边留 8px 左右，左右各留 ≈120px 才是「一张纸浮起来」。

## 5. 底稿源码结构（施工源放项目 `卡片生成/`）

```
卡片生成/<项目>_pdf_focus.html
卡片生成/pdf_focus_assets/{page1_300dpi.png, page2_300dpi.png, card1_600dpi.png, card2_600dpi.png, coords.json}
```

改时长/停留/高亮范围只改底稿里的 stops/cues 两张表；重渲前先按本文件第 3、4 节核算一次几何。
