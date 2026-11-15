#!/usr/bin/env python3
"""小红书笔记图片收藏（可指定任意目标文件夹）
用法: python3 xhs_note_collect.py <noteId> <xsec_token> <目标文件夹绝对路径>
与 xhs_emoji_collect.py 同源逻辑，仅把 BASE 换成显式参数，用于非表情包类图集
（如头像/杂图→ /Users/Jin/Documents/本地资源库/杂图/）。
带 cookie curl 抓详情；图片正则 [^\\s"\\\\] 防跨行合并；只留 !nd_dft_ 原图。
"""
import re, os, sys, json, subprocess, datetime, time

COOKIE = "/Users/Jin/Documents/Hermes/APIs/www.xiaohongshu.com_cookies.txt"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def fetch(note_id, token):
    url = (f"https://www.xiaohongshu.com/discovery/item/{note_id}"
           f"?source=webshare&xhsshare=pc_web&xsec_token={token}&xsec_source=pc_share")
    subprocess.run(["curl", "-sL", "--max-time", "40", "-b", COOKIE, "-A", UA, url,
                    "-o", "/tmp/xhs_note.html"], capture_output=True)
    return open("/tmp/xhs_note.html", encoding="utf-8", errors="ignore").read()


def parse(html, note_id):
    info = {}
    m = re.search(r"<title>(.*?)</title>", html)
    info["title"] = m.group(1).replace(" - 小红书", "").strip() if m else "N/A"
    if note_id not in html:
        info["error"] = "页面不含该笔记（可能风控/未登录）"
        return info
    m = re.search(r'"noteDetailMap":\{"%s".*?"nickname":"([^"]*)"' % note_id, html, re.S)
    if not m:
        m = re.search(r'"nickname":"([^"]*)"', html)
    info["author"] = m.group(1) if m else "N/A"
    for k in ["likedCount", "collectedCount", "commentCount", "shareCount"]:
        m3 = re.search(r'"%s":"([^"]*)"' % k, html)
        if m3:
            info[k] = m3.group(1)
    m4 = re.search(r'"time":(\d{13})', html)
    if m4:
        info["time"] = datetime.datetime.fromtimestamp(int(m4.group(1)) / 1000).strftime("%Y-%m-%d")
    imgs = re.findall(r'(sns-webpic[^\s"\\]{10,220})', html)
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
        subprocess.run(["curl", "-sL", "--max-time", "30", "-A", UA,
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
    note_id, token, dest = sys.argv[1], sys.argv[2], sys.argv[3]
    info = parse(fetch(note_id, token), note_id)
    print(json.dumps({k: v for k, v in info.items() if k != "urls"}, ensure_ascii=False, indent=1))
    if info.get("error"):
        sys.exit(1)
    ok, fail = download(info["urls"], dest)
    print(f"\n下载 {ok}/{info['image_count']} 张 → {dest}")
    if fail:
        print("失败:", fail)
        sys.exit(1)
    print("OK")
