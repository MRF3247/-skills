"""
解螺旋 账号密码自动登录 → 抓 Bearer Token（camofox 通道）
==========================================================
凭证不进对话：脚本自己读 login.txt（第1行账号，第2行密码），
只打印「已填表 / 登录结果 / token 长度」，绝不打印密码。

用法：
  .venv/bin/python jlx_login.py

成功则把 token 写进同目录 token.txt，download_course.py 会自动读取。
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "http://localhost:9377"
UID = "jlxdl"
HERE = os.path.dirname(os.path.abspath(__file__))
LOGIN_TXT = os.path.join(HERE, "login.txt")
TOKEN_TXT = os.path.join(HERE, "token.txt")
LOGIN_URL = "https://passport.helixlife.cn/login?cb_url=https%3A%2F%2Fwww.helixlife.cn%2F"
SEL_ACC = "input[placeholder='请输入手机号或邮箱']"
SEL_PWD = "input[type=password]"
SEL_BTN = "button.login-btn:not([disabled]):not(.disabledBtn)"


def post(path, payload, timeout=60):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read())
        except Exception:
            return {"httpError": e.code}


def ev(tab, expr):
    return post(f"/tabs/{tab}/evaluate", {"userId": UID, "expression": expr}).get("result")


def new_tab(session="jlxlogin"):
    r = post("/tabs", {"userId": UID, "sessionKey": session})
    return r.get("tabId") or r.get("tab", {}).get("id")


def nav(url, tab=None):
    tab = tab or new_tab()
    last = None
    for _ in range(3):
        r = post(f"/tabs/{tab}/navigate", {"userId": UID, "url": url}, timeout=45)
        if r.get("ok"):
            return tab
        last = r
        time.sleep(3)
        tab = new_tab() or tab
    raise RuntimeError(f"navigate 失败: {last}")


def read_creds():
    if not os.path.exists(LOGIN_TXT):
        sys.exit(f"缺凭证文件：{LOGIN_TXT}\n两行：手机号/邮箱、密码")
    lines = [x.strip() for x in open(LOGIN_TXT, encoding="utf-8").read().splitlines()]
    lines = [x for x in lines if x and not x.startswith("#")]
    if len(lines) < 2:
        sys.exit("login.txt 需要两行有效内容：账号 / 密码（# 开头视为注释）")
    return lines[0], lines[1]


AGREE_JS = r"""(()=>{const b=[...document.querySelectorAll('button,.el-button')]
  .find(e=>(e.innerText||'').trim()==='同意并继续');
  if(b){b.click();return 'agreed';}
  // 没有弹窗就勾底部协议
  let done='none';
  document.querySelectorAll('.el-checkbox__original,input[type=checkbox],.el-radio__original').forEach(i=>{
    const l=(i.closest('.el-checkbox,.el-radio,label')||{}).innerText||'';
    if(/服务协议|隐私|条款/.test(l)&&!i.checked){i.click();done='checked';}
  });
  return done;})()"""

HOOK_JS = r"""(()=>{
  if(document.getElementById('__cap')) return 'exists';
  const box=document.createElement('div'); box.id='__cap'; box.style.display='none';
  box.textContent='[]'; document.documentElement.appendChild(box);
  const add=o=>{const a=JSON.parse(box.textContent);a.push(o);box.textContent=JSON.stringify(a);};
  const of=window.fetch;
  window.fetch=function(...args){
    const url=(typeof args[0]==='string')?args[0]:(args[0]&&args[0].url);
    let hdr={}; try{ hdr=(args[1]&&args[1].headers)||{}; }catch(e){}
    const p=of.apply(this,args);
    p.then(r=>add({t:'fetch',url:url,status:r.status,auth:hdr&&(hdr.authorization||hdr.Authorization)||null})).catch(()=>{});
    return p;};
  const oo=XMLHttpRequest.prototype.open, os=XMLHttpRequest.prototype.send, osh=XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return oo.apply(this,arguments);};
  XMLHttpRequest.prototype.setRequestHeader=function(k,v){(this.__h=this.__h||{})[k]=v;return osh.apply(this,arguments);};
  XMLHttpRequest.prototype.send=function(){this.addEventListener('load',()=>{
    try{add({t:'xhr',url:this.__u,status:this.status,auth:(this.__h||{}).authorization||(this.__h||{}).Authorization||null});}catch(e){} });
    return os.apply(this,arguments);};
  return 'hooked';})()"""

READ_STORES_JS = r"""(()=>{
  const o={cookie:document.cookie,ls:{},ss:{}};
  try{for(const k of Object.keys(localStorage)){const v=localStorage.getItem(k)||'';const full=/token|login_info|user/i.test(k);o.ls[k]=full?v.slice(0,8000):v.slice(0,400);}}catch(e){}
  try{for(const k of Object.keys(sessionStorage)){const v=sessionStorage.getItem(k)||'';const full=/token|login_info|user/i.test(k);o.ss[k]=full?v.slice(0,8000):v.slice(0,400);}}catch(e){}
  return JSON.stringify(o);})()"""


def pick_token(blob, caps):
    ck = blob.get("cookie", "")
    m = re.search(r"(?:^|;\s*)token=([^;]+)", ck)
    if m:
        return urllib.parse.unquote(m.group(1))
    for c in caps or []:
        a = (c.get("auth") or "").replace("Bearer ", "").strip()
        if a:
            return a
    for store in ("ls", "ss"):
        for k, v in (blob.get(store) or {}).items():
            if "token" in k.lower():
                try:
                    j = json.loads(v)
                    if isinstance(j, dict):
                        for kk in ("token", "access_token", "accessToken"):
                            if j.get(kk):
                                return j[kk]
                        # localStorage.token 形如 {"data":"3969271|gsZ..."}
                        dv = j.get("data")
                        if isinstance(dv, str) and re.match(r"^\d+\|", dv.strip()):
                            return dv.strip()
                except Exception:
                    pass
                if re.match(r"^\d+\|", v.strip().strip('"')):
                    return v.strip().strip('"')
    m = re.search(r'"(\d+\|[A-Za-z0-9]{20,})"', json.dumps(blob))
    return m.group(1) if m else None


def main():
    acc, pwd = read_creds()
    print("凭证已读取（不显示）")
    tab = nav(LOGIN_URL)
    time.sleep(4)
    print("登录页:", ev(tab, "location.href"))
    ev(tab, HOOK_JS)

    # 1) 处理协议弹窗 / 勾选
    for _ in range(2):
        print("  协议:", ev(tab, AGREE_JS))
        time.sleep(1.5)

    # 2) 填表（真实输入事件）
    r1 = post(f"/tabs/{tab}/type", {"userId": UID, "selector": SEL_ACC, "text": acc, "mode": "fill"})
    r2 = post(f"/tabs/{tab}/type", {"userId": UID, "selector": SEL_PWD, "text": pwd, "mode": "fill"})
    print("填表:", r1.get("ok"), r2.get("ok"))
    time.sleep(1)

    # 3) 登录
    print("点击登录:", post(f"/tabs/{tab}/click", {"userId": UID, "selector": SEL_BTN}).get("ok"))

    err = ""
    for i in range(12):
        time.sleep(3)
        url = ev(tab, "location.href") or ""
        # 可能又弹协议提示，补点一次
        if i in (1, 3):
            ev(tab, AGREE_JS)
        if "passport" not in url:
            print(f"  ✅ 已跳出登录页 → {url}")
            break
        err = ev(tab, """(()=>{const t=[...document.querySelectorAll('div,span')].map(e=>(e.innerText||'').trim())
            .filter(x=>x&&x.length<40&&/密码错误|账号或密码|不存在|验证码|锁定|次数太多/.test(x));
            return [...new Set(t)][0]||'';})()""") or ""
        if err:
            print(f"  服务端提示: {err}")
            break
    time.sleep(2)

    # 登录后 cookie 里的 token 是"有课程权限"的那个；localStorage 里的可能是旧会话（对课无权限）。
    # 且 cookie 写入有延迟，要轮询等。
    tok = None
    for _ in range(8):
        time.sleep(2)
        ck = ev(tab, "document.cookie") or ""
        m = re.search(r"(?:^|;\s*)token=([^;]+)", ck)
        if m:
            tok = urllib.parse.unquote(m.group(1))
            break

    blob = json.loads(ev(tab, READ_STORES_JS) or "{}")
    caps = []
    raw = ev(tab, "document.getElementById('__cap')?document.getElementById('__cap').textContent:'[]'") or "[]"
    try:
        caps = json.loads(raw)
    except Exception:
        pass

    if not tok:
        tok = pick_token(blob, caps)
    if tok:
        with open(TOKEN_TXT, "w", encoding="utf-8") as f:
            f.write(tok.strip())
        print(f"✅ Token 已写入 token.txt（长度 {len(tok)}，不外显）")
    else:
        rt = ev(tab, "(localStorage.getItem('token')||'')") or ""
        print(f"  ls.token 长度={len(rt)} 前20字符={rt[:20]!r}")
        ri = ev(tab, "(localStorage.getItem('login_info')||'')") or ""
        print(f"  ls.login_info 长度={len(ri)} 前120字符={ri[:120]!r}")
        print("⚠️ 登录后没找到 token。诊断信息：")
        print("  cookie 名:", [c.split("=")[0] for c in blob.get("cookie", "").split("; ") if c])
        print("  localStorage:", list((blob.get("ls") or {}).keys()))
        print("  sessionStorage:", list((blob.get("ss") or {}).keys()))
        print("  捕获请求:", json.dumps(caps, ensure_ascii=False)[:800])
        print("  ⚠️ 若 cookie 里没有 token，说明是 httpOnly —— 告诉我，我改走浏览器内直连 API 的路子")
    print("TAB", tab)


if __name__ == "__main__":
    main()
