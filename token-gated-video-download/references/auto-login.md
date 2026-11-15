# camofox 代填表登录 → 抓 Bearer Token

适用：课程站/知识付费站要登录态才能拿播放地址，但登录方式是**账号密码**。目标是让用户只交账号密码（写进本地文件），剩下自动完成，不用教他开 F12 复制 token。

## 0. 先决条件：先探登录方式，别先写代码

navigate 到登录页（多数站是 `passport.<域名>/login?cb_url=...`，也可从首页点登录入口拿跳转 URL），然后 evaluate：

```js
(()=>{const out=[];document.querySelectorAll('input').forEach(i=>out.push({ph:i.placeholder,type:i.type}));
const tabs=[...document.querySelectorAll('div,span,a')].map(e=>(e.innerText||'').trim())
  .filter(t=>t&&t.length<12&&/密码|验证码|扫码|微信|手机/.test(t));
return JSON.stringify({inputs:out.slice(0,15),labels:[...new Set(tabs)].slice(0,20)});})()
```

- 有 `type=password` 的输入框 = 支持账号密码登录 → 本 recipe 可用。
- 页面文案只有「验证码登录/微信扫码」或出现滑块容器 → 放弃自动登录，让用户给 token。**别硬刚验证码**。
- 顺手截图 `GET /tabs/{id}/screenshot?userId=<uid>` + vision 核一眼：`placeholder` 能看出有密码框，但看不到「有没有滑块」和「协议弹窗」这两种拦路虎。

## 1. 表单交互一律用 camofox 的 `/type` `/click`，不要用 JS 赋值

`POST /tabs/{id}/type  {userId, selector, text, mode:"fill"}`
`POST /tabs/{id}/click {userId, selector}`

```json
{"userId":"jlxdl","selector":"input[placeholder='请输入手机号或邮箱']","text":"...","mode":"fill"}
{"userId":"jlxdl","selector":"input[type=password]","text":"...","mode":"fill"}
```

为什么不用 `Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value')` + `dispatchEvent(input)`：Vue/Element UI 的 v-model 有时吃不到合成事件，表面填进去了、点登录却校验失败或值被清空，排查成本极高。Playwright 级输入一次就对。

## 2. selector 必须唯一 —— 否则 422

`/click` 走 Playwright locator，**一个 selector 命中多个元素直接 422**，报 `strict mode violation: ... resolved to N elements`。

典型陷阱：登录页同时渲染「账号登录 / 验证码登录」两套表单（tab 切换但 DOM 都在），于是页面上有 2-3 个文字为「登录」的按钮，其中一个还是 `disabled`。做法是先 evaluate 把候选列出来看 class/disabled，再用收窄的 selector：

```js
[...document.querySelectorAll('button')].filter(x=>(x.innerText||'').trim()==='登录')
  .map(x=>({dis:x.disabled, cls:x.className}))
```

```
selector: button.login-btn:not([disabled]):not(.disabledBtn)
```

## 3. 协议弹窗会静默吞掉你的点击

国产站常把「同意《用户服务协议》…」做成点击登录后弹出的「温馨提示」+「同意并继续」。**只勾 DOM 里的 checkbox 不一定生效**，表现是点了登录毫无反应、页面地址不变、也没有报错。

标准写法：点登录前后各补一次「同意」，两段都写：

```js
(()=>{const b=[...document.querySelectorAll('button,.el-button')].find(e=>(e.innerText||'').trim()==='同意并继续');
 if(b){b.click();return 'agreed';}
 let done='none';
document.querySelectorAll('.el-checkbox__original,input[type=checkbox],.el-radio__original').forEach(i=>{
  const l=(i.closest('.el-checkbox,.el-radio,label')||{}).innerText||'';
  if(/服务协议|隐私|条款/.test(l)&&!i.checked){i.click();done='checked';}});
 return done;})()
```

注意别按「记住密码」那个 checkbox 判定成功 —— 它默认是勾上的，容易误以为协议已同意。

## 4. 用假凭证验链路，别拿真凭证调试

填 **00000000000 / testpass123** 点登录，出现「账号或密码错误」= 填表→点击→提交→服务端校验整条链路通，可以交付。这一步不需要真凭证，也不会污染账号（失败计数风险极低但别反复刷）。

把这三件事分次验证，出问题时能立刻定位：① 值进没进框（evaluate 读 `input.value`）；② 按钮可不可点、点没点上；③ 服务端怎么回的（读页面提示文案，如 `.el-message`/`账号或密码错误`）。

## 5. token 落点探测顺序

登录成功后按这个顺序找：

1. `document.cookie` 里的 `token=`（原作者的脚本说明常直接写「cookie 的 token 字段」）→ 有就直接用，还要 `urllib.parse.unquote`。
2. `localStorage` / `sessionStorage` 里 key 含 `token` 的项（值可能是 JSON，取 `token`/`access_token`/`accessToken`）。
3. 都为空 → 大概率 httpOnly cookie。此时注入 hook 抓 `authorization` 头：

```js
// 注入后触发一次站内 API 调用（SPA 内导航/点个链接，别整页刷新，刷新会丢 hook）
const of=window.fetch; window.fetch=function(...a){const p=of.apply(this,a);
  p.then(r=>add({url:a[0],status:r.status,auth:(a[1]&&a[1].headers||{}).authorization}));return p;};
const oo=XMLHttpRequest.prototype.open,os=XMLHttpRequest.prototype.send,osh=XMLHttpRequest.prototype.setRequestHeader;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return oo.apply(this,arguments);};
XMLHttpRequest.prototype.setRequestHeader=function(k,v){(this.__h=this.__h||{})[k]=v;return osh.apply(this,arguments);};
XMLHttpRequest.prototype.send=function(){this.addEventListener('load',()=>add({url:this.__u,auth:(this.__h||{}).authorization}));return os.apply(this,arguments);};
```

- 捕获结果**写到 DOM 节点**（如 `document.getElementById('__cap').textContent`），不要存 `window.__x`：camofox 的 evaluate 之间不保证保留 window 变量，写到 DOM 才能跨次读。
- camofox **没有** `/cookies` `/storage` `/network` 端点（`/tabs` 系列只有 navigate/evaluate/type/click/press/scroll/select/upload/snapshot/extract/images/links/wait/screenshot/stats/back/forward/refresh/downloads/open）。所以 httpOnly 场景只能靠 hook，或者改走「页面内直接 fetch API」让浏览器自己带 cookie。

## 6. 凭证纪律

- 账号密码落 `login.txt`（第一行账号、第二行密码），脚本自己读；**日志只打印「已读取 / 填表 ok / 服务端提示」，绝不打印密码或 token 明文**。
- 提供一个 `login.txt.example` 模板，用户复制改名填值，比让他自己新建文件少出错。**模板里的 `#` 注释行是陷阱**：用户会连注释一起复制，脚本把注释当账号/密码，登录失败却看起来像密码错。取凭证时过滤 `not x.startswith("#")`，模板本身也只留两行纯值。
- 成功拿到 token 后写 `token.txt`（脚本的 `resolve_token()` 优先读它），并提示「token 有效期几天，过期重跑登录脚本即可」。
- 用完删掉测试 tab：`DELETE /tabs/{id}?userId=<uid>`。

## 7. 已验证到哪一步（诚实标注）

解螺旋 passport 页实测（真凭证）：登录方式探测 ✓、真实输入 ✓、协议弹窗处理 ✓、点击提交 ✓、**登录成功跳回主页 ✓**、**token 抓取 ✓**。

- token 落点：`document.cookie` 里**非 httpOnly** 的 `token=` 字段，56 字符，形如 `数字|长串`，`urllib.parse.unquote` 后即 Bearer token。第 5 节的 hook 拦截在这条站上没抓到东西（登录请求不是页面上下文发的），不要因为它空而判定失败——先读 cookie。
- 协议弹窗的真实时序（照这个顺序写，少踩两轮）：勾 checkbox → 点登录 → **弹出「温馨提示」** → 点「同意并继续」→ 登录自动提交并跳转（不用再点一次登录）。只勾 checkbox 不点这个弹窗，登录请求根本不会发出。
- 下次接手若 `token.txt` 为空：先看第 5 节诊断输出里的 cookie 名列表，再决定走 hook 还是页面内直连 API。
