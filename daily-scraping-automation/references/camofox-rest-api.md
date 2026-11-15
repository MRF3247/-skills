# Camofox 浏览器 REST API（localhost:9377）

反检测浏览器（C++ 级指纹伪装，可过 Cloudflare）。REST API，OpenAPI 在 `/openapi.json`。项目在 `~/Documents/GitProgram/camofox-browser`（`npm start` 后台启动）。

## 端点速查
| 端点 | 用途 |
|---|---|
| `GET /health` | 状态；`browserRunning` 可能 false（惰性启动） |
| `POST /tabs` body `{"userId","sessionKey"}` | 创建 tab → **返回字段是 `tabId`**（不是 tab_id） |
| `POST /tabs/{tabId}/navigate` body `{"userId","url"}` | 导航（等待加载，返回 `refsAvailable`） |
| `POST /tabs/{tabId}/evaluate` body `{"userId","expression"}` | JS 求值，`result` 字段拿返回值 |
| `POST /navigate`（OpenClaw 格式） | 实测 404，用 /tabs 系列更稳 |

## 核心用法（Python urllib）
```python
def _call(method, path, body=None, timeout=90):
    req = urllib.request.Request(BASE+path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())

# 建 tab → 导航 → 拿原始 HTML
r = _call("POST", "/tabs", {"userId": "mednews", "sessionKey": "daily"})
tab = r["tabId"]
_call("POST", f"/tabs/{tab}/navigate", {"userId": "mednews", "url": url})
time.sleep(5)  # 等 JS 渲染
html = _call("POST", f"/tabs/{tab}/evaluate",
    {"userId": "mednews", "expression": "document.documentElement.outerHTML"})["result"]
```

## 坑（全部实测）
1. **唤醒竞态 500**：浏览器 idle 关闭后第一次 navigate 常 500（`Internal Server Error`）。**失败重试一次**（3s 后），或 tab 失效时 `self.tab = None` 重建。第二次必成功。
2. **拿 HTML 用 outerHTML**：`document.documentElement.outerHTML`。普通 HTML 页面直接可用（正则解析照旧）。
3. **RSS/XML 可抓**：navigate 到 XML/RSS URL，`outerHTML` 返回**原始 XML 文本**（ScienceDaily RSS 60 个 `<item>` 完整）。注意 NEJM 的 etoc feed 是 **RDF 格式**（`<rdf:RDF>` + 命名空间 item）——`html.count("<item>") == 0` 不代表抓取失败，用 XML 解析器按 local name 匹配。
4. **等加载**：navigate 返回后页面可能未完成。轮询 `evaluate("document.readyState")` == "complete"（1.5s 间隔），再额外 sleep 2-3s 等 JS 渲染（SPA 必须）。
5. **节流**：每次 navigate 间隔 ≥3s（浏览器也礼貌）。
6. **JSON API URL**：navigate 到 JSON 接口 URL 会渲染成 JSON 文本，outerHTML 拿 `<pre>` 包裹——解析麻烦，API 接口直接 urllib 更简单（本 skill 主 SKILL.md 的通道选择）。
7. **B站搜索页**（无 cookie 方案）：navigate `https://search.bilibili.com/all?keyword=xx&order=pubdate`，evaluate 提取：
```js
(() => { const out=[]; document.querySelectorAll('.bili-video-card').forEach(c=>{
  const a=c.querySelector('a[href*="/video/BV"]');
  const t=c.querySelector('.bili-video-card__info--tit');
  const u=c.querySelector('.bili-video-card__info--author');
  const p=c.querySelector('.bili-video-card__stats--item span');
  if(a&&t) out.push({url:a.href,title:t.textContent.trim(),up:u?u.textContent.trim():'',play:p?p.textContent.trim():''});
}); return JSON.stringify(out); })()
```
   播放量文本是 `"5"`/`"1.2万"` 格式 → 解析时 `万`×10000。搜索页**不显示发布时间**——新稿件用 B站 view 接口补 pubdate/播放量（免登录）。
8. **多 session 隔离**：不同任务用不同 `userId`/`sessionKey`（如 mednews / bili-daily），tab 互不干扰。

## 与 Hermes 内置 browser 工具的关系
camofox 是独立 REST 服务，脚本（cron no_agent）可以直接 HTTP 调——这是它与 Hermes browser 工具（会话内交互）的本质区别，也是每日任务能全自动走浏览器指纹的原因。
