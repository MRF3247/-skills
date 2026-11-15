# B站 账号名 → UID 查询与账号数据采集（对标账号研究）

做对标账号清单、查 UP 主主页、验证粉丝数、批量采集账号数据时的方法（2026-08 两轮大规模批量实测，60+ 账号验证通过）。

## 接口清单（按可靠性排序）

### 1. relation/stat — 粉丝数验证（免登录、免签名、最稳）
```bash
curl -s "https://api.bilibili.com/x/relation/stat?vmid=<mid>"
```
`data.follower` = 粉丝数。两个用途：(a) 验证用户提供的账号数据（本会话 15 个账号全部吻合）；(b) 反查 UID 后交叉验证身份。轻量使用无风控，可循环批量（本会话 15 连发无问题）。

### 2. 移动端搜索页 — 账号名→UID 首选（免 wbi 签名、实测无风控）
```bash
curl -s -A "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1" \
  "https://m.bilibili.com/search?keyword=<urlencoded 账号名>"
```
返回视频搜索结果，HTML 内嵌 JSON：`"owner":{"mid":<UID>,"name":"<UP主名>"}`，正则提取即可。
- 按账号**全名**搜索时，`owner.name == 账号名` 的 exact 匹配即命中（本会话命中率最高、最可靠）。
- type 参数不生效，始终返回视频结果；`<em>` 高亮标签只出现在 title 里，owner.name 是干净的。
- 可复用于拉 UP 主代表性视频标题（提炼内容方向/选题）。

### 3. wbi 搜索接口 — 按关键词批量找账号（需签名 + 必须防风控）
```python
# 1) GET /x/web-interface/nav → data.wbi_img.img_url / sub_url
#    取 URL 文件名去掉扩展名 → img_key / sub_key（注意 nav 可能返回 -101 未登录，data.wbi_img 仍在）
# 2) raw = img_key + sub_key；mixin_key = "".join(raw[i] for i in 固定64位置换序)[:32]
#    置换序: [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]
# 3) 参数排序 + 加 wts=时间戳 → w_rid = md5(urlencode(sorted_params) + mixin_key)
```
响应 `data.result[]` 每项含 `uname/mid/fans/videos/usign`；支持 `search_type=bili_user&order=fans`（按粉丝排序）+ 分页。适合「按关键词枚举赛道账号」。
完整实现见 `scripts/bili_collect_users.py` 同目录方案（本会话脚本：/Users/Jin/Documents/Hermes/bili_collect_users.py）。

### 4. web_search 工具反查 — 兜底（同名混淆/移动端搜不到时）
`web_search("哔哩哔哩 {账号名} 空间")` → 结果里找 `space.bilibili.com/<mid>` 链接；或搜到视频链接 BV 号 → curl 视频页 → 正则 `"owner":{"mid":N,"name":"..."}` 提取。
**任何反查结果都必须用 relation/stat 验证粉丝数与预期一致**，否则可能是同名账号。

## 坑（全部实测踩过）

1. **风控是最大杀手**：wbi 搜索接口连续 ~30+ 请求后触发风控，症状是 **`code:0` 但 `result` 为空数组**（与不带 Referer 同症状！）或 -412/HTML 错误页。缓解：先 curl https://www.bilibili.com/ 存 buvid3 cookie（`-c /tmp/bili_cookies.txt`，请求带 `-b`）、请求间隔 2.5-4s、失败重试 3-4 次退避。**空结果先怀疑风控，不要以为账号不存在。** 上一版 reference 写「批量无需 sleep」是错的——会触发风控。
2. **旧接口 `x/web-interface/search/type` 返回 HTML「出错啦!」错误页**，必须用 `wbi/search/type`。
3. **同名账号极多**：`ai科研` vs `Ai科研绘图`（粉丝数 5.7万 vs 3.9万）、`小白在学统计` 反查两次命中错误 UID（81万粉/156万粉的无关号）、`Panda科研绘图` 命中无关号。**任何来源的 UID 都必须用 relation/stat 粉丝数与已知预期比对（容差 ±5%），不匹配就换下一个候选，绝不取第一个。** 同名混淆时给账号名加限定词再搜（如「ai科研 研究生科研工具」）。
4. **execute_code 有 50 次工具调用上限**：批量循环（每账号 2-3 次 curl）会被静默截断。超过 ~20 个账号的批量任务写成 .py 脚本文件用 terminal 跑（本会话 30+ 账号循环被截断两次后才改脚本）。
5. 查不到的「账号」可能是：榜单视频作者名（非独立 UP 主）、品牌名（实际是旗下子号）、已改名/注销。清单里明确标注原因，不硬凑 UID。
6. 脚本放 /Users/Jin/Documents/Hermes/（用户工作目录，用户期望可复用刷新数据）；本技能 scripts/bili_resolve_uids.py 是通用版。

## 输出规范（用户明确纠正过，铁律）

- 交付清单**禁止「等N个」式省略**——每个账号完整列出（账号名 + UID），一个都不能漏，不许「等8个」「其余类似」收尾。
- 数据标注快照时间（如「2026-08-04 实时查询」），粉丝数会漂移，账号形态/打法/UID 稳定。
- 未解析的 UID 明确标注原因（同名混淆/疑似改名），不硬凑。
