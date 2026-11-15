# 新闻速读卡 · 案例存档（青霉素去标签，2026-11-05）

跑通并交付的一例，改版时拿它对回归：**4 页、无溢出、底部留白 112–116px**。

## 输入 JSON（实际用的）

```json
{
  "source": "Pediatrics · 2026-11-04 · DOI 10.1542/peds.2026-077964",
  "title_cn": "儿童青霉素过敏的去标签化",
  "title_en": "Penicillin Allergy Delabeling in Children",
  "tag": "新闻速读",
  "cover": "file:///tmp/news_card/cand/7653119.jpg",
  "cover_hint": "右滑阅读全文",
  "lead": "全球近 10% 的人被贴上青霉素过敏标签，其中约 95% 并非真正过敏；而在儿童身上，这类错误标签几乎都是童年贴上的。",
  "credit": "图片：Pexels",
  "blocks": [
    {"cn": "全球近 10% 的人，病历上挂着「青霉素过敏」这条标签……"},
    {"cn": "这组数字来自 11 月 4 日美国儿科学会（AAP）旗下期刊《Pediatrics》的一篇综述……"}
  ]
}
```

配图：Pexels `photo 7653119`（医生 / 母亲 / 女孩面对面沟通，3:2），CDN：
`images.pexels.com/photos/7653119/pexels-photo-7653119.jpeg?auto=compress&cs=tinysrgb&w=1800`

## 验收数字（2x 图实测，逻辑 px）

| 页 | 墨迹顶部 | 墨迹底部 | 底部留白 |
|---|---|---|---|
| P1 封面 | 34 | 1313 | 56（封面自然） |
| P2 正文 | 38 | 1253 | 116 |
| P3 正文 | 38 | 1258 | 112 |
| P4 正文（尾） | 38 | 1115 | 254 |

自检脚本（不要用 `check_bottom_gap.py` 的默认判定，它会按 5% 卡）：

```python
from PIL import Image; import numpy as np
im = np.array(Image.open(f).convert('RGB')).astype(int)
blue = ((im[:,:,2]>100)&(im[:,:,0]<60)&(im[:,:,1]<110)).mean(axis=1)
foot = np.argmax(blue > 0.9)                       # 蓝条上沿（2x）
dark = (im.sum(axis=2) < 420).mean(axis=1)
ink  = np.where(dark[:foot] > 0.002)[0]           # 文字墨迹行
print(foot/2, ink[0]/2, ink[-1]/2, (foot-ink[-1])/2)
```

## 跨页位置（当时的结果）

- P3 尾：`…在监护下按体重吃一次阿莫西`
- P4 头：`林 45 mg/kg、单次不超过 1000 mg，观察 60 分钟。…`
（写满整行的必然代价：词被拆开。用户已接受，别为语义完整浪费半行。）

## 落飞书结果

文档 `<wiki 节点>` 开头插了 1 行 grid × 4 栏（`width-ratio=0.25`），文件名：
`01_封面.png` / `02_正文1.png` / `03_正文2.png` / `04_正文3.png`，每张 `960×1280`（比例 0.75）。
本地同名备份：`~/Downloads/青霉素过敏_图文/`。
