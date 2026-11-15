#!/usr/bin/env python3
"""小红书表情包帖收藏：curl带cookie抓详情 → 解析 → 下载到素材/表情包/<组>/
用法: python3 xhs_emoji_collect.py <noteId> <xsec_token> <组文件夹名>
2026-08-12 实测：匿名 curl 对登录墙笔记返回 -510001，带 cookie（-b）可拿全量。
已内置防坑：noteDetailMap 上下文取作者（首个 nickname 是推荐流干扰项）、
图片正则 [^\\s"\\\\] 防跨行合并、去重只留 !nd_dft_ 原图。
批量跑时每条之间 sleep ≥60s（用户纪律），不要并行。
"""
import re, os, sys, json, subprocess, datetime, time

COOKIE = "/Users/Jin/Documents/Hermes/APIs/www.xiaohongshu.com_cookies.txt"
BASE = "/Users/Jin/Documents/素材/表情包"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

def fetch(note_id, token):
    url = f"https://www.xiaohongshu.com/discovery/item/{note_id}?source=webshare&xhsshare=pc_web&xsec_token={token}&xsec_source=pc_share"
    subprocess.run(["curl", "-sL", "--max-time", "40", "-b", COOKIE, "-A", UA, url, "-o", "/tmp/xhs_emoji.html"],
                   capture_output=True)
    html = open("/tmp/xhs_emoji.html", encoding="utf-8", errors="ignore").read()
    return html

def parse(html, note_id):
    info = {}
    m = re.search(r"<title>(.*?)</title>", html)
    info["title"] = m.group(1).replace(" - 小红书", "").strip() if m else "N/A"
    if note_id not in html:
        info["error"] = "页面不含该笔记（可能风控/未登录）"
        return info
    # 作者：限定在 noteDetailMap 上下文（页面首个 nickname 是推荐流干扰项）
    m = re.search(r'"noteDetailMap":\{"%s".*?"nickname":"([^"]*)"' % note_id, html, re.S)
    if not m:  # 兜底：取页面第一个昵称
        m = re.search(r'"nickname":"([^"]*)"', html)
    info["author"] = m.group(1) if m else "N/A"
    # 正文 desc：找带话题标签的那条（跳过博主简介）
    descs = re.findall(r'"desc":"((?:[^"\\]|\\.)*)"', html)
    info["desc"] = ""
    for d in descs:
        d_clean = d.encode().decode("unicode_escape", errors="ignore") if "\\u" in d else d
        if "欢迎来到" in d_clean or "记录" in d_clean and "简介" not in d_clean:
            continue
        if "话题" in d_clean or len(d_clean) > 10:
            info["desc"] = d_clean[:200]
            break
    for k in ["likedCount", "collectedCount", "commentCount", "shareCount"]:
        m3 = re.search(r'"%s":"([^"]*)"' % k, html)
        if m3:
            info[k] = m3.group(1)
    m4 = re.search(r'"time":(\d{13})', html)
    if m4:
        info["time"] = datetime.datetime.fromtimestamp(int(m4.group(1)) / 1000).strftime("%Y-%m-%d")
    # 图片：排除所有空白防跨行合并，去重，只留原图 !nd_dft_（跳过 !nd_prv_ 封面预览）
    imgs = re.findall(r"(sns-webpic[^\s\"\\]{10,220})", html)
    urls = []
    for u in imgs:
        if "!nd_dft_" in u and u not in urls:
            urls.append(u)
    info["image_count"] = len(urls)
    info["urls"] = urls
    return info

def download(urls, dest):
    os.makedirs(dest, exist_ok=True)
    ok, fail = 0, []
    for i, u in enumerate(urls, 1):
        out = f"{dest}/{i:02d}.jpg"
        subprocess.run(["curl", "-sL", "--max-time", "30", "-A",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                        "https://" + u, "-o", out], capture_output=True)
        sz = os.path.getsize(out) if os.path.exists(out) else 0
        if sz > 5000:
            ok += 1
        else:
            fail.append((i, sz))
            if os.path.exists(out):
                os.remove(out)
        time.sleep(0.5)
    return ok, fail

if __name__ == "__main__":
    note_id, token, group = sys.argv[1], sys.argv[2], sys.argv[3]
    html = fetch(note_id, token)
    info = parse(html, note_id)
    print(json.dumps({k: v for k, v in info.items() if k != "urls"}, ensure_ascii=False, indent=1))
    if info.get("error"):
        sys.exit(1)
    dest = os.path.join(BASE, group)
    ok, fail = download(info["urls"], dest)
    print(f"\n下载 {ok}/{info['image_count']} 张 → {dest}")
    if fail:
        print("失败:", fail)
        sys.exit(1)
    print("OK")
