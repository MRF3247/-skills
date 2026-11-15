# 公众号首图 · 横版插画版（2.35:1，AI 插画 + 思源宋体大字）

先用一句话定版式：**同一尺寸 1080×460 有两种做法，先看同系列旧封面用的是哪一种**。

| 版式 | 特征 | 在哪 |
|---|---|---|
| 书封样机版 | 左侧黑体、右侧白底圆角书封卡 | `SKILL.md` 的「公众号首图变体」节 |
| **插画版（本文）** | AI 插画占右半、左侧思源宋体 Heavy 大字压在米白底上 | 本文 |

## 0. 动手前先对系列

```bash
ls ~/Documents/素材/ | grep '刀客轻研公号封面'   # 同系列旧首图
```

拿旧图跑一次 `vision_analyze`，问「版式结构 / 字体 / 各级字号与颜色 / 右半是什么」。新版**沿用层级与留白逻辑**；用户点名换字体（例如「要思源宋体最粗」）或换插画时才改。同一账号的封面不成系列，用户会当成两家的。

## 1. 尺寸与生图比例

- 逻辑画布 **1080×460**，2x 出图 **2160×920**，比值 2.348 ≈ 微信 2.35:1（官方 900×383）。
- 固定高，`--window-size=1080,460` 直接截，**不用**像长海报那样开大再裁尾。
- Seedream 5.0 Pro `-s ratio=21:9 -s quality=2K` 实测出 **3120×1328（比值 2.349）**——与画布几乎同比例，等比缩到 2160×920 后基本零裁切。这是横版首图最好用的比例档。

## 2. 插画提示词（横版专用增量）

在 SKILL.md 的「模板 B」基础上**只改这两段**，其余（画风/配色/人物/不要）照抄：

```
【构图】画面右半部分集中主体：<谁，在做什么，抱着什么>；主体占据画面右侧约 45% 的宽度，
      从画面顶部到底部基本填满，人物面部位于画面垂直中段。
      画面左侧约一半宽度保持大面积干净的米白／乳白色空白，不放任何主体、不放任何装饰，
      只有极淡的浅蓝色光晕过渡，留给文字排版使用。
【文字】画面内不要出现任何文字、字母、数字、logo：书脊、屏幕、纸张内容一律用横线或色块占位。
```

出图后先量左侧留白到底有多宽，**不要相信提示词**：

```python
import numpy as np; from PIL import Image
a = np.array(Image.open('art.png').convert('RGB')).astype(np.int16)
bg = a[:, :6, :].mean(axis=(0, 1))
cols = (np.abs(a - bg).sum(2) > 18).sum(0)
for x in range(0, a.shape[1], 60):      # 每 60 原始 px 打一次
    print(round(x / a.shape[1] * 1080), cols[x:x+60].max())
```

`maxink` 从个位数跳到几百的那一列＝插画起点。实测要求「留白 50%」时真实干净区只有约 350 逻辑 px。

## 3. 文字区宽度 → 字号（先量后定，不许凭感觉）

**顺序是「定文字区宽 → PIL 量字宽反推字号 → 再写 CSS」**。反过来（先挑个「看着够大」的字号）必然折行，主标一折行就出孤字，是这版最常见的事故。

```python
from PIL import ImageFont
f = lambda s: ImageFont.truetype('/Users/Jin/Library/Fonts/SourceHanSerifSC-Heavy.otf', s)
w = f(size).getbbox(text)[2] + letter_spacing * (len(text) - 1)   # 必须加字距
assert w <= 文字区宽度
```

实测表（1080 宽画布、思源宋体 Heavy、`letter-spacing:3px` 处已折算）：

| 文案 | 字号 | 宽 |
|---|---|---|
| 医学科研教程（6 字） | 74 / 76 / 78 / 80px | 459 / 471 / 483 / 495px |
| 免费领（3 字） | 84 / 88 / 92px | 262 / 274 / 286px |
| 价值3000元 | 32 / 34px | 176 / 186px |
| 从查文献到投稿，四本一次领走 | 23px | 322px |

**交付档**：文字区 `width:520px`（`left:58px`）时 → 主标 78px、`免费领` 88px、原价 32px、副行 23px，四行全部单行。

**主标拆两行能把字号放大**：一行 6 字只能 78px（再大就断成「医学科研教／程」）；拆成「医学科研」＋「教程」后每行最多 4 字，同样版心里可以放到 **92px**。要拆就早早拆，别先按一行排完再返工。

## 4. 版式（定稿，自上而下）

| 元素 | 规格 |
|---|---|
| 胶囊标签 | 1.6px `#006EBB` 描边、23px、`letter-spacing:2.5px`、`border-radius:999px`、`padding:5px 18px 6px` |
| 主标 | 78px Heavy、`#1A222C`、`letter-spacing:3px`、`line-height:1.14` |
| 价格行 | `display:flex; align-items:baseline; gap:16px`：**`免费领` 88px `#006EBB` 在左，原价 32px 红色划掉在右**（顺序是用户定的，我第一版放反了被打回） |
| 副行 | 23px `#5A6675`、`letter-spacing:1.5px`（**用户可能直接要求删掉，见 §4b**） |
| 版心 | `top:62px; left:58px`；**上下墨迹余量做到 60–70px 对称**（62 / 69.5 是实测过的平衡值） |

**原价必须用促销红，不用灰**：`#D93A2B`（字与删除线同色）。灰字划掉在公众号信息流里几乎读不到「原价」这层意思，用户会直接要求「价值3000元以及删除线都要做成红色」。这是全图唯一的非蓝色元素，面积小、不破坏单色蓝体系。

底色用 `#FCFCFA`（贴近插画自带的米白），插画与本底的接缝才看不出来。

**原价删除线必须用伪元素画**——`text-decoration:line-through` 在灰字上是「几乎看不见的细浅线」，用户/审图都会判「原价没划掉」：

```css
.was{position:relative;color:#D93A2B;}
.was::after{content:'';position:absolute;left:-6px;right:-6px;top:55%;height:6px;background:#D93A2B;}
```

**用户要「从左上到右下对角划掉」时**，换成渐变画斜线（`inset` 稍微外扩，线才不会两端被切断）：

```css
.was{position:relative;display:inline-block;font-size:24px;color:#D93A2B;line-height:1;}
.was::after{content:'';position:absolute;inset:-3px -5px;
  background:linear-gradient(to top right,
    transparent calc(50% - 1.7px), #D93A2B calc(50% - 1.7px),
    #D93A2B calc(50% + 1.7px), transparent calc(50% + 1.7px));}
```

**`to top right` 才出「左上→右下」（\），`to bottom right` 出的是「左下→右上」（/）**——这两个极易写反，写反了用户会再退一次。**方向别问 vision**（它对斜线方向连续判错两轮）：用像素回归验——取红色像素后比较左侧 1/6 列与右侧 1/6 列的中位 y，右高于左才是 \：

```python
a = np.array(Image.open('out.png').convert('RGB'))
red = (a[:,:,0]>170)&(a[:,:,1]<90)&(a[:,:,2]<80)
ys, xs = np.where(red)
cols = {x: [] for x in xs}
for x, y in zip(xs, ys): cols[x].append(y)
ks = sorted(cols); n = len(ks)//6
print(np.median(cols[k] for k in ks[:n]), np.median(cols[k] for k in ks[-n:]))   # 右侧更大＝\
```

## 4b. 删块之后必须重测上下余量

封面的行数是活的：标签会改文案（「临床科研新手保姆级SOP」这类长标签要重新算胶囊内边距）、副行会被整行删掉、价格行会左右对调。**删一行就把 `top` 和各行 `margin-top` 重新分配，然后重跑 §6 的墨迹量测**，目标仍是上下对称。实测删掉副行后从 `top:62/余69.5` 调到 `top:76/余83.5` 就重新平衡；直接留着不调会变成上半空一大块。改文案只重跑 HTML 截图（零成本，不重生图）。

## 5. 插画与文字的交界：三种做法里只有一种不挨骂

| 做法 | 结果 |
|---|---|
| 整幅铺底 + 从左 0% 线性淡化到 70% | ❌ 被判「**半透明幽灵人物**／复印机没墨」。原因：被淡化的人轮廓仍然锐利，只是变淡，违反「远＝模糊」的直觉 |
| 裁一个硬边矩形插画块贴右侧 | ❌ 切点常落在人脸/眼镜上，被判「**素材没摆好被切掉**」 | ✅ **整幅铺底 + 羽化带窄、起点在文字区右界之外、羽化区同时上高斯模糊** |

定稿写法（`x0`/`x1` 为 2x 像素，`x0 = 文字区右界*2 + 60`，带子宽 240 2x px ＝ 120 逻辑 px）：

```python
from PIL import Image, ImageFilter
import numpy as np
im = Image.open('art_raw.png').convert('RGB').resize((2160, 920), Image.LANCZOS)
blur = im.filter(ImageFilter.GaussianBlur(20))
a, b = np.array(im).astype(np.float32), np.array(blur).astype(np.float32)
h, w = a.shape[:2]
x = np.arange(w, dtype=np.float32)
t = np.clip((x - x0) / (x1 - x0), 0, 1)
al = (0.5 - 0.5 * np.cos(np.pi * t)).astype(np.float32)      # smoothstep，没有硬边
A  = np.repeat(al[None, :], h, 0)[..., None]
bw = (1 - al)[None, :].repeat(h, 0)[..., None] * 1.0         # 模糊权重随 alpha 反向
mix = b * bw + a * (1 - bw)
bg = np.array([252, 252, 250], np.float32)
out = bg + (mix - bg) * A
Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save('bg_2x.png')
```

背景图做成一张 2160×920 的成品，HTML 里用 `background-image` 铺满（`background-size:1080px 460px`），文字另起绝对定位层。

## 6. 验收（程序 + vision 各一遍）

```python
# 文字区墨迹上下余量（x 取文字区右界*2 以内）
ink = np.array(Image.open('out.png').convert('L'))[:, :1180] < 190
rows = np.where(ink.any(1))[0]
print('上余', rows.min()/2, '下余', 460 - rows.max()/2)      # 目标 60–70 对称
```

vision 只问三件：① 主标 / 价格行 / 副行**是否各自单行、无孤字**（这版第一号事故）；② 删除线是否清楚；③ 文字有没有压到人物、有无出界。

## 7. 落盘与交付

- `~/Documents/素材/刀客轻研公号封面_<主题>_免费领.png`（2160×920）
- 插画原图另存 `刀客轻研公号封面_<主题>_插画原图.png`（用户常自己再排版；改文案也不用重生图）
- 交付必须点两条：① 微信**分享卡片/主页的 1:1 方图是从这张图里取 460×460，而裁切框在后台可拖动**——不要把文字搬去居中迁就它（会压到右侧插画，用户会追问「为什么标题跑到正中间」）；保持左文右图，交付时教用户把框拖到最左，并说明此时方图里只有文字、没有插画（要带图就得把文字右移约 130px、主标降到 76px）；② 「免费＋主题」若被拆成「主题」＋「免费领」两行（8 字一行放不下时），主动说明这是取舍，并给出「压到 70px 一行」的备选。
