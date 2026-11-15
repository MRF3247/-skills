# 登录与双 token

## 站点结构

- 主页：`https://www.helixlife.cn/`
- 课程页：`https://www.helixlife.cn/edu/courses/<UUID>`
- 登录形态：账号密码（`jlx_login.py` 用 camofox 自动填表）

## 两个 token（核心坑）

同一个页面里存在两份 token，行为完全不同：

| 来源 | 出现时机 | 对新购课的表现 |
|---|---|---|
| `localStorage.token` | 立刻可读 | 经常报「该视频您无权限观看」 |
| `document.cookie` 的 `token=` | 登录后延迟写入 | 网页实际使用，权限完整 |

**代码要求**：

```python
# 登录后轮询等 cookie
tok = None
for _ in range(8):
    cookies = driver.get_cookies()
    for c in cookies:
        if c['name'] == 'token' and c['value']:
            tok = c['value']
            break
    if tok:
        break
    time.sleep(2)
```

不要 `or localStorage` 回退——回退就会拿到错的那份。

## 重登顶号

再次登录会把旧 token 作废，接口报：

```
{"code":400002,"msg":"请先进行登录！"}
```

这个报错**不是**「没权限」。抓到可用 token 后就不要再跑登录。

---

## 会话状态失效：报「无权限」但网页能看

### 现象

用户网页上能正常看整门课，但下载脚本报「无权限」或「请先进行登录」。

特征是**同一门课里部分节能过、部分节不过**，而且越往后失败率越高。逐节测新老 token 对比：

```
旧 token（隔夜）  8 节里 1 节 OK
新 token（刚登）  8 节里 8 节 OK
```

### 本质

token 能通过认证（不是 401），但它绑定的会话状态已失效，只能访问极少数内容。两种诱因都真实存在，表现完全一样，不要分辨：

- **老化**：隔夜或长时间未用
- **被顶号**：另一个进程/脚本刚登过，把这个 token 作废了

服务端返回文案也不固定：`400002 请先进行登录！` 和 `无权限` 都会出现。

**两种都要先怀疑会话状态，不是购买状态。**

### 另一个误导点

`download_course.py` 里的判断：

```python
if "无权限" in msg:
    raise RuntimeError("这节你没买/没权限（不是 token 问题）")
```

这个分支的名字是错的：实测「无权限」也可能就是会话状态失效。看到这条错误时先重登，不要信这个文案。


---

## 错误码只是线索，不是判决

| code | message | 能说明什么 | 不能说明什么 |
|---|---|---|---|
| `20000` | 成功 | 这一节当下可下 | — |
| `400001` | 参数错误 | video_id 传错了（例如传了 lesson.uuid） | — |
| `400002` | 请先进行登录！ | 手上这个 token 已失效/被顶掉 | **不能**说明课没买 |
| `400003` | 该视频您无权限观看！ | 当下这个 token 拿不到这一节 | **不能**说明课没买 |

### 血泪教训

`400003` 被当成「这门课只买了第 1 节」上报过一次，用户直接反驳「不可能，我所有的课都有权限」。用**同一个 token、同一节**重测，返回 `20000`。

即 `400003` 在同一会话里都会翻转，它反映的是**调用时刻的会话状态**，不是购买记录。

**规矩：永远不要用错误码对用户断言「你没买这门课」。** 先按下面的方法验证网页能不能播，再下结论。

### 排查顺序

```
报错
 → 确认没有并行/重复的登录在跑（最容易的元凶）
 → 重登一次，重测同一节
 → 还不过 → 开真实浏览器验证网页能不能播（见下）
 → 网页能播但 API 不过 → 才是接口层问题，记录现象，别猜购买状态
```

---

## 验证「网页到底能不能播」

用户说能看时，必须自己验一遍再答复。三个要点：

### 1. 播放页路径是 `/edu/study/courses/<UUID>`

不是 `/edu/courses/<UUID>`（那是详情页，没有播放器）。`/edu/lesson/<uuid>`、`/edu/courses/<uuid>/lessons/<uuid>` 都直接 404。

### 2. 小节元素是 `div.catalog-item`，且事件是框架绑定的

`dispatchEvent(new MouseEvent('click'))` **静默无效**——点了没反应，URL 不变，没有 video 元素。

必须用真实鼠标点击。做法是先打 id 再让 camofox 点：

```python
ev(tab, """(() => {const t=[...document.querySelectorAll('div.catalog-item')]
 .find(e=>e.innerText&&e.innerText.includes('小节标题关键词'));
 if(!t) return 'nf'; t.id='jlxtarget';
 t.scrollIntoView({block:'center'}); return 'ok';})()""")
post(f"/tabs/{tab}/click", {"userId": UID, "selector": "#jlxtarget"})
```

点成功后 URL 变成 `/edu/study/courses/<uuid>`，页面出现 `video` 元素（`readyState=4`），说明确实有观看权限。

### 3. 从 `play_auth` 请求反解真实 video_id

```python
# 网页播过之后
urls = ev(tab, "JSON.stringify(performance.getEntriesByType('resource')"
               ".map(r=>r.name).filter(n=>/play_auth/.test(n)))")
f = urls[0].split("play_auth?f=")[1]
print(urllib.parse.unquote(base64.b64decode(f).decode()))
# → {"video_id":"eb0ff2d4..."}
```

实测：网页用的 video_id 与 lessons 接口返回的 `lesson.path.path` **完全一致**。`path.path` 是对的，不需要换 lesson.uuid（那样会 `400001`）。

### 4. 补充：登录态怎么判断

未登录也能打开课程详情页、看到完整目录（目录是公开的），所以「能看到目录」不能证明有权限。要看 `document.cookie.includes('token=')` 和 `video` 元素。

---

## 批量下载期间不要跑任何会登录的脚本

这是本节最贵的一条。

每跑一次 `jlx_login.py` 都会生成新 token 并**作废前一个**。排查时连续跑了七八个诊断脚本（每个内部都登录一次），把正在下载的任务手里的 token 反复顶掉，表现就是「同一门课有的节能过、有的节不过，越往后越差」——看起来像权限问题，其实是自己把自己踢下线了。

规矩：

1. **下载前登一次，之后到任务结束不再登录。**
2. 需要抓网页验证时，先等下载任务停下，或者用**不登录**的方式（直接读现有 token 调 API）。
3. 报错先看有没有别的进程刚登过，别急着改代码。

扫课脚本的判据「前 3 个非免费节任一能换 PlayAuth 即算有权限」在部分购买的课上仍会高估。校验方法很简单：**下完后数文件，与 lessons 里 video 总数对比**，不等就是没下全——但先排除 token 因素再谈购买。

## 权限判定

只试一节课会误判：

- 只试首节：首节可能是免费的 → **高估**（扫出 89 门，真实 47 门）
- 只试末节：课是整体卖的，末节可能单独售卖 → **低估**（扫出 29 门）

正确判据：

```
取该课前 3 个 is_free == false 的节，
任一节能换到 PlayAuth → 有权限
```

## 凭证文件

`credentials/login.txt` 格式（两行）：

```
账号
密码
```

`credentials/token.txt`：只存 token 本体，无前缀。

脚本只打印「已填表」「结果」「token 长度」，**不打印密码与 token 明文**。
