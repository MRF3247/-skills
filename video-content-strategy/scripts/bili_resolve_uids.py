#!/usr/bin/env python3
"""B站账号名→UID 解析（对标账号研究用）。

对每个账号名：
  1) 移动端搜索页 https://m.bilibili.com/search?keyword=<名> 取视频结果里 owner 的 exact 匹配
  2) relation/stat 验证粉丝数（可选 --expect-fans 交叉校验，拦截同名账号）
  3) 输出：账号名<TAB>UID<TAB>粉丝数

用法:
  python3 bili_resolve_uids.py "郑老师讲统计" "生信技能树-jimmy"
  python3 bili_resolve_uids.py --expect-fans 39845,161531 "郑老师讲统计" "生信技能树-jimmy"
  python3 bili_resolve_uids.py < names.txt          # 每行一个账号名

依赖：curl（macOS/Linux 自带）。无需 B站 登录、无需 wbi 签名。
实测：2026-08 批量解析 60+ 账号，移动端搜索 exact 匹配命中率最高；
      同名混淆（ai科研 vs Ai科研绘图 等）靠 --expect-fans 校验拦截。
详情与其它接口（wbi 搜索、web_search 反查、视频页提取）见 references/bilibili-account-uid-lookup.md。
"""
import json, re, sys, time, subprocess, urllib.parse

UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
UA_DESKTOP = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def sh(cmd, timeout=25):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout
    except Exception:
        return ""


def mobile_owners(name):
    """移动端搜索页：返回 [(mid, owner_name), ...]，来自视频结果内嵌 JSON。"""
    q = urllib.parse.quote(name)
    html = sh(f'curl -s -m 15 -A "{UA_MOBILE}" "https://m.bilibili.com/search?keyword={q}"')
    return re.findall(r'"owner":\{"mid":(\d+),"name":"((?:[^"\\]|\\.)*)"\}', html)


def fans_of(mid):
    """relation/stat 免登录查粉丝数（-1 表示查询失败）。"""
    out = sh(f'curl -s -m 15 -A "{UA_DESKTOP}" "https://api.bilibili.com/x/relation/stat?vmid={mid}"')
    try:
        d = json.loads(out)
        return d["data"]["follower"] if d.get("code") == 0 else -1
    except Exception:
        return -1


def resolve(name, expect=None):
    """先 exact 匹配 owner.name == 账号名；有 expect 时再用粉丝数过滤同名号。
    未 exact 命中且给了 expect 时，退回模糊匹配 + 粉丝校验。"""
    for mid, oname in mobile_owners(name):
        if oname != name:
            continue
        fans = fans_of(mid)
        if expect is not None and fans > 0 and abs(fans - expect) / max(expect, 1) > 0.05:
            continue  # 同名不同人
        return mid, oname, fans
    if expect is not None:
        for mid, oname in mobile_owners(name):
            fans = fans_of(mid)
            if fans > 0 and abs(fans - expect) / max(expect, 1) < 0.05:
                return mid, oname, fans
    return None, None, None


def main():
    args = sys.argv[1:]
    expects = None
    if args and args[0].startswith("--expect-fans"):
        expects = [int(x) for x in args[1].split(",")]
        args = args[2:]
    names = args or [l.strip() for l in sys.stdin if l.strip()]
    if not names:
        print(__doc__)
        return
    for i, name in enumerate(names):
        exp = expects[i] if expects else None
        mid, oname, fans = resolve(name, exp)
        if mid:
            print(f"{name}\t{mid}\t{fans}" + (f"\towner={oname}" if oname != name else ""))
        else:
            print(f"{name}\tNOT_FOUND" + (f"\texpected={exp}" if exp else ""))
        time.sleep(0.5)


if __name__ == "__main__":
    main()
