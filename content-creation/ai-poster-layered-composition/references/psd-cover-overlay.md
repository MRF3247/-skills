# PSD 封面模板叠加：把插画嵌进设计师给的 PSD

适用：用户给一个 PSD 封面模板（常见 1080×1440），要求「把这版插画叠上去出一张图」。PSD 里的装饰层（顶部白/灰渐变、底部蓝渐变、品牌 logo）必须原样保留，只替换底图。

## 0. 取 PSD（飞书链接时）

```bash
# 1) 读文档拿 file_token：<source name="xxx.psd" token="..." .../>
lark-cli docs +fetch --doc "<飞书URL>#share-<anchor>" --doc-format markdown --as user
# 2) 下载
lark-cli docs +media-download --token <file_token> --output ./cover.psd --overwrite
file cover.psd   # 确认 Adobe Photoshop Image, W x H, RGBA
```

## 1. 装 psd-tools

```bash
python3 -m pip install psd-tools -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60
```

官方源在国内常 `ReadTimeoutError` 卡 5 分钟，直接上清华镜像。装完的 `attr.s`/`scipy` 依赖一并带走，不要再单独装。

## 2. 摸结构：图层 + 蒙版，不要只看 topil()

```python
from psd_tools import PSDImage
psd = PSDImage.open("cover.psd")
print(psd.size, psd.color_mode)
for i, l in enumerate(psd):
    print(i, repr(l.name), l.kind, "visible", l.visible, "bbox", l.bbox)
    print("   mask:", l.mask)          # 有没有蒙版，决定了这一层的真实形状
```

**核心认知**：`layer.topil()` 返回的是**裸像素，不含图层蒙版和图层样式**。设计师常用的做法是「整块纯色填充 + 渐变蒙版」，于是：

- 纯蓝层 topil() 出来是一整片 #0073B7（看起来毫无用处）
- 纯白层 topil() 出来是一整片白（更看不出用处）
- 而合成预览里它们分别是「底部蓝渐变」和「顶部白渐变」

蒙版才是形状。读它：

```python
mask = l.mask.topil().convert("L")
print("mask mean", np.asarray(mask).mean())
print("rows:", [int(np.asarray(mask)[y:y+100].mean()) for y in range(0, H, 100)])
```

行均值从 0 递增 → 该层在**底部**渐显；从高递减到 0 → 在**顶部**渐隐。255=显示，0=隐藏。

同时确认哪一层是「旧底图」：`visible=False` 的 smartobject（名字常是 `ChatGPT Image …`）就是它，位置由它让出给新插画。

## 3. 直接拿 composite() 当覆盖层（关键技巧）

底图隐藏时，`psd.composite()` 产出的就是**纯覆盖层**：中部 alpha=0 全透明，顶部/底部渐变带、logo 都在，且已按图层样式正确渲染。

```python
comp = psd.composite()   # RGBA
# 校验：中部应透明、顶部和底部应有 alpha
rows = [int(np.asarray(comp)[y:y+100, :, 3].mean()) for y in range(0, H, 100)]
```

若 composite 中部透明、上下有渐变 alpha，就不用自己逐层重建蒙版，直接叠：

```python
art = Image.open("插画.png").convert("RGB").resize(psd.size, Image.LANCZOS)
out = art.convert("RGBA")
out.alpha_composite(comp)
out.convert("RGB").save("封面成品.png")
```

插画比例（3:4）与画布（1080×1440）一致时直接 resize；不一致时先等比放大到**覆盖**画布再居中裁切，别拉伸。

**不要**用 `sips -s format png cover.psd` 的结果当图层依据：它渲染的是另一套（可能含被 psd-tools 忽略的样式），只能当「设计意图预览」看，不能当蒙版数据源。

## 4. 验收（交付前过一遍）

视觉模型问四件事，别只问「好不好看」：

1. 顶部品牌 logo 是否清晰、有没有被白雾或飞散元素盖住、离上边缘是否太近（平台裁切风险）
2. 底部渐变是否吃掉主体下半身（同色系前景 + 底部蓝渐变最容易糊成一片）
3. 前景主体是否完整可见、没被纸片/元素遮挡
4. 除 logo 外有无多余文字、乱码

交付时把这三处主动列成「可调项」：底部渐变浓度、logo 大小与上边距、顶部白雾压淡插画的程度。用户对成品的挑刺基本都落在这三处。

## 5. 副作用说明

- 顶部白渐变会把插画最上面那排元素压淡——这是封面设计本身的效果，要主动说，不要让用户以为画丢了。
- PSD 一动不改就交付：只在内存里合成，原始 `.psd` 保持原样，用户后续自己还能在 PS 里改。
