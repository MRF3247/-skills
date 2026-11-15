# 文字卡版式常量（3:4 长文分段卡）

## 1. 配色（纸底学术风）

```css
:root{
  --paper:#FCFBF8;   /* 纸底：微暖白，别用纯白，纯白在手机上刺眼 */
  --ink:#1B2027;     /* 正文：近黑，不用 #000 */
  --ink2:#39424F;
  --muted:#939CAB;   /* 页眉标签/页码/版式小字 */
  --blue:#17558F;    /* 深蓝：品牌、章节名、封面主色 */
  --blueL:#2563EB;   /* 亮蓝：马克笔、章节号、强调 */
  --rule:#E6E3DA;    /* 分隔线：偏暖的浅灰，别用冷灰 */
}
```
一只强调色走到底。正文保持 `--ink` 中性色，蓝色只用于马克笔+章节号+封面——花哨就变营销图了。

## 2. 字体：思源宋体在 macOS 的字族与字重映射

本用户对文字卡的指定：**全文思源宋体，标题 900 字重，正文 500 字重**（衬线学理感，且重字重区分足够明显）。

macOS 上思源宋体各字重是独立 OTF，注册的**字族名是中文「思源宋体」**：

| 文件 | Family | Style | CSS font-weight |
|---|---|---|---|
| SourceHanSerifSC-ExtraLight | 思源宋体 | ExtraLight | 200 |
| SourceHanSerifSC-Light | 思源宋体 | Light | 300 |
| SourceHanSerifSC-Regular | 思源宋体 | Regular | 400 |
| SourceHanSerifSC-Medium | 思源宋体 | Medium | **500（正文）** |
| SourceHanSerifSC-SemiBold | 思源宋体 | SemiBold | 600 |
| SourceHanSerifSC-Bold | 思源宋体 | Bold | 700 |
| SourceHanSerifSC-Heavy | 思源宋体 | Heavy | **900（标题）** |

**先查再写**（换机器/字重没生效时重跑）：
```bash
system_profiler SPFontsDataType > /tmp/fonts.txt
# 再按 SourceHanSerifSC 切块，读 Family / Style 两行
```

CSS 写法（双保险，防止 `Source Han Serif SC` 这个英文名没命中）：
```css
@font-face{font-family:'SHSerifSC';font-weight:900;src:local('思源宋体 Heavy'),local('Source Han Serif SC Heavy')}
@font-face{font-family:'SHSerifSC';font-weight:500;src:local('思源宋体 Medium'),local('Source Han Serif SC Medium')}
@font-face{font-family:'SHSerifSC';font-weight:400;src:local('思源宋体 Regular'),local('Source Han Serif SC Regular')}
body{font-family:'SHSerifSC','思源宋体','Source Han Serif SC',serif;
     -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
```
不要用 `src:url('file:///…otf')` 引字体文件——页面本身也是 `file://`，Chrome 会拦。

## 3. 正文与引用

```css
p.p{font-weight:500;font-size:40px;line-height:1.88;color:var(--ink);
    letter-spacing:.015em;text-align:justify;text-justify:inter-ideograph}
p.cite{font-weight:400;font-size:22px;line-height:1.66;color:#7B8595;letter-spacing:.012em;
       padding-left:18px;border-left:3px solid rgba(37,99,235,.30);margin-top:-10px;
       text-align:left;word-break:break-word}
p.cite b{font-weight:700;color:#5B6473}   /* DOI 加粗，仍浅于正文 #0E2A49 */
```
- `text-align:justify` + `text-justify:inter-ideograph` 让中文块面整齐（印刷感），代价是可能出现字距松动——行宽别太窄。
- 引用（论文出处 + DOI）**跟随正文缩放**：`0.55 × 正文字号`，不低于 19px。用户要「很小的字」指的是层级，不是不可读。
- 引用用「左蓝竖线 + 缩进 + 灰」三重区分，否则和正文混在一起。
- **摘出引用块时去掉最外层全角括号**，让它以作者名开头；颜色 `#7B8595`，**DOI 加粗**（`#5B6473`）。用户口径是「颜色稍微深一点点，但不要比正文深」——深是相对上一版，任何时候都不能深过正文。

## 4. 蓝色马克笔（强调关键术语）

```css
mark{background:linear-gradient(180deg,
       rgba(37,99,235,0) 52%, rgba(37,99,235,.26) 52%,
       rgba(37,99,235,.26) 96%, rgba(37,99,235,0) 96%);
     color:#0E2A49;padding:0 .07em;border-radius:1px}
/* 长句专用：压薄一半，避免跨行后连成实心蓝带 */
mark.soft{background:linear-gradient(180deg,
       rgba(37,99,235,0) 50%, rgba(37,99,235,.14) 50%,
       rgba(37,99,235,.14) 97%, rgba(37,99,235,0) 97%);
     color:#12304F}
```
- 渐变把色带压在文字**下半部** → 像马克笔划过，字仍全黑清晰。整块实色背景会让人觉得字被糊住。
- **每段最多 3 处**。一段挂 5 个高亮会糊成一块蓝色，重点全部失效。做法：给术语候选排优先级，到 3 处即停。
- **两档笔触，按跨度选**：术语（≤ ~14 字）用 `.26`；用户点名要「整句高亮」的长句用 `.soft`（`.14`）。整句高亮不要拒绝——用户会亲自要求——但原浓度下 35 字跨 3 行就是一块实心蓝带，比不标还糟。生成器里按 `len(term) > 14` 自动选档。
- 想确认到底哪一档渲染上了，直接采样高亮带的像素色（纸底 `#FCFBF8` 上）：`.26 ≈ rgb(196,212,245)`，`.14 ≈ rgb(222,230,246)`。这比看图判断可靠。

## 5. 结构骨架

```css
.page{width:1242px;height:1656px;background:var(--paper);padding:84px 96px 64px;
      display:flex;flex-direction:column;overflow:hidden;position:relative}
.stack{flex:1 1 auto;display:flex;flex-direction:column;justify-content:flex-start;min-height:0}
.body{flex:0 0 auto;display:flex;flex-direction:column;gap:30px;margin-top:46px}
.foot{margin-top:auto;padding-top:26px;display:flex;border-top:1px solid var(--rule);flex:0 0 auto}
```
- **`.stack` 顶端对齐（`flex-start`），不要居中**。字号全篇统一后各页行数不同，居中会让每页正文起始高度都不一样，翻页时视线上下跳，用户会判成「莫名其妙地居中了」。顶端对齐后起始高度一致；无标题的续页正文自然上移，正好接住上一页。
- 页脚 `margin-top:auto` 钉底；正文与页脚横线之间保留安全距离（`scripts/verify_cards.py` 会量化检查）。

章节头：大号蓝色数字（900 / 74px）+ 章节名（900 / 52px）+ 向右延伸的浅灰细线。
封面/序卡才允许更大的节拍字号（日期 104px、结语正文 56px）。

## 6. 封面：自己画，不用现成图

版权红线：官方机构素材（如诺奖官网）禁止商业/营销用途，带推广的账号不能直接搬；期刊图也多有 NC 限制。**封面装饰自己用 SVG 画**：
- 光束：从上方中心向下的低透明度扇形细线（`stroke-opacity .07-.10`）+ 末端圆点（`fill-opacity .13`）。透明度再高就会干扰标题。
- 时间轴：一条水平实线 + N 个等距圆点（大小/透明度做节奏变化），两端标注起止年份。这是封面唯一的数字钩子。
- 主标题第一行可用「超大数字 + 中等字号单位词」组合（如 `8`(160px) + 篇论文(110px)）——两者字号落差别拉太大（150 vs 86 就散了）。

## 7. 分卡规则

- 正文 **300-420 字/卡**；卡数先按字数算再落版。
- **段落不跨卡拆断**；章节头优先做卡片锚点。
- 章节内容超一卡时拆页并标「（续）」——这是分页，不是改用户的章节划分；**用户定好的分章结构不要动**。
- 卡片序列通常有三个非正文节拍：封面 / 序（日期+目录）/ 结语。**但本用户的定案是砍掉封面与序、结语并入最后一页**（首张正文卡即第 1 页，页码从它起算）。要新增这类节拍卡先问，别默认加——他删过一次就会一直删。
- **结语并入最后一页**时先实测高度：两段一起会溢出（实测 1327px vs 可用 1257px），如实报数让他决定舍哪段，不要靠压字号硬塞。

## 8. 版式新增内容清单（交付时必须逐条报备）

这些是你加的、原稿里没有的东西，必须在交付信息里单独列出并给出删改选项：

| 项 | 说明 |
|---|---|
| 封面副标题 | 若原稿没有，需自己拟或直接留空 |
| 封面时间轴 / 目录 | 年份须全部出自原稿 |
| 页码、页眉标签、品牌栏 | 版式件 |
| 「（续）」、章节号被拆成「数字 + 标题」 | 标点层面的改动，说明并给恢复办法 |
| 引用小字块 | 把段末括号引用挪出正文，属排版重排 |

交付前跑 `python3 scripts/verify_cards.py --text <原稿> <pages> --layout <你加的每一项>`，残差为空才算报备完整。

## 9. 四个可直接抄的片段

**① 剥出段末引用（含 DOI 的括号）——文字核对与摘小字块共用**
```python
CIT = re.compile(r'（(?=[^（）]*DOI:)[^（）]*）\s*$')
m = CIT.search(line)
body = CIT.sub('', line).strip() if m else line
cite = m.group(0).strip('（） \t') if m else None   # 已去掉最外层全角括号
```
拿整行原文去渲染结果里做子串匹配会**必然误报丢字**（引用已被摘走），务必先剥再比。

**② DOI 加粗**
```python
def bold_doi(c):
    return re.sub(r'(DOI:\s*)(\S+)', r'\1<b>\2</b>', c) if c else c
```

**③ 只测量、不改字号的适配脚本**（全篇统一字号下用来一次找出「溢出页」与「太空页」）
```js
(function(){
  var body=document.querySelector('.body'), stack=document.querySelector('.stack');
  if(!body||!stack) return;
  function outerH(el){var r=el.getBoundingClientRect(), cs=getComputedStyle(el);
    return r.height + parseFloat(cs.marginTop||0) + parseFloat(cs.marginBottom||0);}
  var above=0, el=body.previousElementSibling;      // 累加 body 之上所有兄弟节点
  while(el){ above+=outerH(el); el=el.previousElementSibling; }
  var avail=stack.clientHeight - above - 120;       // 120px 安全余量
  var h=0,k=0;
  Array.prototype.forEach.call(body.children,function(ch){h+=ch.getBoundingClientRect().height;k++;});
  var gap=parseFloat(getComputedStyle(body).rowGap||30)||30;
  var used=h+(k-1)*gap;
  document.title='used='+Math.round(used)+' avail='+Math.round(avail)
                 +' fill='+Math.round(used/avail*100)+'%'+(used>avail?' OVERFLOW':'');
})();
```
渲染后逐页回读 `document.title`，一次拿到全册的溢出页与空页清单。

**④ 页脚横线定位**（像素校验用）：只扫页面底部 15%，且要求该行**行内填充率 > 0.9**（横线几乎整行有墨）。不设这两个条件，正文的密排行会被误判成页脚线。
