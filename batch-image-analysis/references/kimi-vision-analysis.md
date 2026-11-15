# kimi code 批量视觉分析（k3-256k）— 2026-08-07 实测

视觉审核/风格分析/适配筛选的默认模型（替代 MiniMax-M3）。两批实测：150 张 Canva 模板「医学/论文/学术适配筛选」+ 19 张留白海报「留白技巧分析」。

## 端点与模型

- 端点：`https://api.kimi.com/coding/v1/chat/completions`（OpenAI 兼容）
- 模型：`k3-256k`（256K 上下文内效果同 k3、消耗减半、支持图片）
- key：`Hermes/APIs/kimicode API.rtf`，Python 里用 `textutil -convert txt <rtf> -stdout` 读取后 strip 换行空格
- 其他可用模型：kimi-for-coding（=K2.7 Coding，强制 thinking）、kimi-for-coding-highspeed、k3（1M，双倍消耗）

## 请求体（图片 + 文本）

```python
payload = {"model": "k3-256k",
           "messages": [{"role": "user", "content": [
               {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
               {"type": "text", "text": PROMPT}]}],
           "max_tokens": 1200}   # 800 会截断！实测 139 字缺提示词行
```

## 图片预处理

`Image.open(path).convert("RGB").thumbnail((1024, 1024))` → JPEG q80 → base64。压到 ~1MP 省 token；大图（2484×3312）base64 会超 shell 参数限制，必须脚本内缩小。

## Prompt 设计（用户硬性要求：只看视觉风格，不读文字）

用户原话纠正：「从视觉风格的角度来分析哈，不是说让你提取文字什么的」。

- 视觉风格分析开头写「【只看视觉风格，不读图里任何文字】」
- 适合性判断给双向视觉特征清单（示例——医学/论文/学术）：
  - 适合：医学插画/解剖图/细胞分子图形、DNA/基因/科研图标、科学图表/数据可视化、学术海报版式、复古医学图谱、实验室/手术/显微镜场景、专业科研摄影、极简专业排版、学术期刊封面气质
  - 不适合：纯风景/旅行、美食餐饮、美妆时尚、卡通萌宠、娱乐拼贴、婚礼庆典、运动健身、儿童涂鸦
  - 声明「通用但专业克制的风格也算适合」（避免误杀中性模板）
- 留白分析六维：留白位置与比例 / 主体与留白关系 / 留白区域性质（纯色/渐变/肌理）/ 排版如何利用留白 / 整体气质 / 可复用 AI 生图提示词（【提示词】开头单独一行）

## 输出解析

模型返回带杂讯，JSON 用正则提取，不要直接 json.loads 全文：

```python
m = re.search(r'\{[^{}]*"suitable"[^{}]*\}', content)
data = json.loads(m.group(0))
```

## 批量稳健性（详见 batch-pipeline-robustness）

- 结果 JSON 落盘，重跑跳过已有 key（断点续传）
- 空返回/解析失败**不落盘**，批尾统一补跑；空返回 ≠ 内容被拦（解剖/医学图重试多成功），一律重试 3 次（间隔 3-5s）
- 每批 ≤10-20 个（console 30s read timeout；20 个带间隔会超时）
- 偶发内容截断 → 提高 max_tokens 重跑该张（删除旧结果文件再跑）

## 批量筛选应用（Canva 模板医学适配案例）

kimi_canva_filter.py 模式：`适合/不适合 + 一句话视觉理由` → 不适合的移入 `_待删除/` 待用户确认（不直接删），生成 02_筛选清单.md 标注来源与理由。用户确认后才彻底删除。
