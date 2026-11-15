# 视觉审核模型选型（2026-08-06 实测）

海报审核（vision_analyze 走 hermes 的 `auxiliary.vision` 配置）可选模型与实测结论。

## 背景：审核 ≠ 生图，审核模型和生图引擎是两码事

生图引擎选型见 ai-fullposter-direct.md（Seedream 5.0 Pro 中文最强 / MiniMax image-01 中文必乱码）。
这里是**审核/打分**用的视觉模型——MiniMax-M3 一直是默认（`auxiliary.vision: provider=custom, model=MiniMax-M3, base_url=api.minimaxi.com, api_key_env=MINIMAX_CN_API_KEY`）。

## Kimi 视觉实测（2026-08-06，key 已配好 KIMI_API_KEY）

| 模型 | thinking | 视觉实测 | 结论 |
|---|---|---|---|
| kimi-k3 | always on（关不掉） | 300~2000 token 全被思考吃掉，finish_reason=length，内容出不来 | 审核太慢太贵，勿用 |
| kimi-k2.6 | 默认开（关不掉？） | 1000 token 全被 reasoning 吃掉 | 同上 |
| **kimi-k2.5** | **可关**（`"thinking":{"type":"disabled"}`） | **秒回，reasoning_tokens=1，识别准确**（还能指出伪汉字乱码、认出印章署名） | **推荐做第二审/交叉验证** |

### 端点选择（2026-08-06 后半段实测补充）

- **kimicode 专用端点**：`https://api.kimi.com/coding/v1`，key 在 `/Users/Jin/Documents/Hermes/APIs/kimicode API.rtf`（textutil 读取，72 字符 sk-kimi 开头）。该端点模型列表含 `k3` / **`k3-256k`（首选）** / `kimi-for-coding`(K2.7 Coding) / `kimi-for-coding-highspeed`，**全部 supports_image_in=True**
- **批量深度分析模型首选 `k3-256k`**（用户 2026-08-06 拍板）：官方文档确认「256k 上下文内效果与 k3 相同，k3(1M) 消耗约为 k3-256k 两倍」。单张参考分析用不到 1M 上下文，选 256k 省一半消耗、质量无损。**审图/抽卡仍用 kimi-k2.5（thinking disabled）**，k3 系只做深度倒推
- **kimicode 上的 k3 = moonshot 的 kimi-k3 同模型**，但计费走 kimicode 套餐（用户 2026-08-06 明确：批量分析消耗 kimicode 的 token，不用 KIMI_API_KEY）
- **kimi-for-coding 做参考分析/提示词倒推质量接近 k3**（同图对比实测：风格溯源稍浅——只到「Hokusai/Hiroshige/nishiki-e」，抓不到「36.0°=B型DNA旋转角」这类科学细节；但产出提示词直接可用，含中英+负面词）→ 批量分析选型：kimicode k3（深度优先）/ kimi-for-coding（够用且便宜）
- 余额查询：`GET https://api.moonshot.cn/v1/users/me/balance`（Bearer key）→ `data.cash_balance` 是真实现金余额；**官网进度条显示的是套餐额度池，与现金余额两套账**，进度条 0% 不代表没消耗

调用：OpenAI 兼容，`base_url=https://api.moonshot.cn/v1`，模型名 `kimi-k2.5`，请求体带
`"thinking":{"type":"disabled"}`（否则默认开思考，任务简单也烧几千 token）。

curl 实测模板（本地图 base64 直传）：
```
curl -s https://api.moonshot.cn/v1/chat/completions \
  -H "Authorization: Bearer $KIMI_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"kimi-k2.5","thinking":{"type":"disabled"},
       "messages":[{"role":"user","content":[
         {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,..."}},
         {"type":"text","text":"这张图里有哪些中文文字？逐个读出。"}]}],
       "max_tokens":1000}'
```

## 口径一致性规则（重要）

- **同一批打分任务内不要混用审核模型**：MiniMax-M3 的 8.5 分和 Kimi 的 8.5 分不是同一个「8.5」。10 套风格对比这种任务全程用一个模型，中途切换会让前后分数不可比。
- **选版说明/评分表必须标注审核模型**（如「审核：MiniMax-M3」），用户复看时知道分数口径。
- 切换配置：`hermes config set auxiliary.vision.model <模型>`（+ provider/base_url/api_key_env），模型/base_url 改动对 vision_analyze 立即生效，调用代码零改动。
- **key 生效有个大坑（2026-08-06 实测 401）**：hermes 的 custom provider 从**进程环境变量**读 key（启动时 `load_hermes_dotenv` 注入 .env）——**向 .env 新增 key 后必须重启 hermes 会话**，当前会话内 vision_analyze 直接 401。auxiliary_client 的 key 解析链：`api_key_env` → `_scoped_key_env` → `get_secret` → `os.getenv`，读不到就是空 key。另外 custom provider 的 base_url 与主模型（deepseek）不同 host 时**不会**继承主模型 key（防跨 host 泄露），所以不能指望同 host 借用。
- 建议分工：MiniMax-M3 主审核（历史分可对比）+ Kimi-k2.5 第二审交叉验证（同一批图两模型都看，取共识）。

## k3 的另一种用途：深度参考分析 / 提示词倒推（2026-08-06 实测）

k3 做**逐张审核**慢且贵（勿用），但它做**「看图→倒推可执行提示词」是三方最强**（> kimi-k2.5 >> MiniMax-M3）：

| 能力 | kimi-k3 | kimi-k2.5 | MiniMax-M3 |
|---|---|---|---|
| 风格溯源 | 认出「致敬歌川广重《名所江户百景》」、Didone 高对比衬线、bokashi 晕染 | 认出「葛饰北斋式」泛层 | 泛泛「北斋遗韵」 |
| 可执行规则 | 字号比例口诀（主标题:副标:正文:元信息≈10:3:1.5:1）、「等距就死了错落才活」、「黄字永远压在深色区」、可商用字体替代方案 | 结构完整但略简 | 模板化建议（采样步数 30-50 通用参数） |
| 幻觉风险 | 低（会说「疑似伪汉字」） | 低 | **高**（把乱码脑补成通顺词、编出不存在的「删除线」） |
| 耗时 | 200-300s/张（thinking 全开） | ~15s | ~10s |

**结论**：倒推提示词需要的不是「看图说话」而是「视觉语言解构」——认流派、技法、构图逻辑、色彩关系，翻译成生图引擎听得懂的词。k3 两档都懂「画面为什么好看」，MiniMax 只懂「画面有什么」。分工：**k3 做风格家谱/参考图的提示词倒推（一次性深度投资）**；**k2.5 做日常审核抽卡**；MiniMax-M3 退居二线或交叉验证。

批量管线（41 任务断点续传 + 回写 Obsidian）见 references/prompt-reverse-engineering.md。
