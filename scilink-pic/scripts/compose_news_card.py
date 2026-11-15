#!/usr/bin/env python3
"""compose_news_card.py — 新闻双语图文（3:4 多页，文章多长排多长）

输入 JSON（utf-8）：
{
  "source": "Retraction Watch · 2026-11-04",
  "title_cn": "中文标题",
  "title_en": "English Title",
  "tag": "新闻速览",                    // 可选，天头胶囊；默认「新闻速览」
  "footer_left": "刀客轻研 · 新闻速览",  // 可选
  "blocks": [ {"en": "英文段", "cn": "中文段"}, ... ]
}

用法：
  python3 compose_news_card.py news.json --out-dir /tmp/news
  python3 compose_news_card.py news.json --out-dir /tmp/news --name penicillin

输出：<out-dir>/<name>-01.png ... -NN.png（逻辑 1080×1440，2x 实际 2160×2880）
stdout: JSON {pages, files[], overflow_blocks, html}
"""
import argparse
import json
import os
import re
import subprocess
import sys

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL, "templates", "news_bilingual.html")
PAGE_W, PAGE_H = 1080, 1440


def build_html(data, out_html):
    tpl = open(TEMPLATE, encoding="utf-8").read()
    html = tpl.replace("__DATA__", json.dumps(data, ensure_ascii=False))
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html)


def chrome(args, timeout=180):
    return subprocess.run([CHROME, "--headless=new", "--disable-gpu"] + args,
                          capture_output=True, text=True, timeout=timeout)


def measure(html_path):
    """第一趟：dump-dom 读 JS 排完版写进 DOM 的页数/溢出数。"""
    # 必须和截图同一缩放（2x）：1x 量的字宽/换行与 2x 渲染不同，会算少了行、内容压到页脚
    r = chrome(["--hide-scrollbars", "--force-device-scale-factor=2",
                "--window-size=1080,1440",
                "--virtual-time-budget=8000", "--dump-dom", "file://" + html_path])
    m = re.search(r'data-pages="(\d+)"', r.stdout or "")
    o = re.search(r'data-overflow="(\d+)"', r.stdout or "")
    if not m:
        sys.stderr.write((r.stderr or "")[-2000:])
        raise SystemExit("未取到页数：Chrome 没执行 JS 或模板损坏")
    return int(m.group(1)), (int(o.group(1)) if o else 0)


def screenshot(html_path, n, shot_path):
    h = PAGE_H * n
    r = chrome(["--hide-scrollbars", "--force-device-scale-factor=2",
                f"--window-size={PAGE_W},{h}", "--virtual-time-budget=8000",
                f"--screenshot={shot_path}", "file://" + html_path])
    if not os.path.exists(shot_path):
        sys.stderr.write((r.stderr or "")[-2000:])
        raise SystemExit("截图失败")


def crop_pages(shot_path, n, out_dir, name):
    from PIL import Image
    img = Image.open(shot_path)
    files, step = [], PAGE_H * 2
    for i in range(n):
        p = os.path.join(out_dir, f"{name}-{i+1:02d}.png")
        img.crop((0, i * step, PAGE_W * 2, (i + 1) * step)).save(p)
        files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--out-dir", default="/tmp/news_card")
    ap.add_argument("--name", default="news")
    a = ap.parse_args()

    data = json.load(open(a.json_file, encoding="utf-8"))
    if not data.get("blocks"):
        raise SystemExit("blocks 为空")
    os.makedirs(a.out_dir, exist_ok=True)
    # 文件名带内容哈希：Chrome 会缓存同路径 file://，同名重跑会截到旧版
    import hashlib
    seed = json.dumps(data, ensure_ascii=False, sort_keys=True) + str(os.path.getmtime(TEMPLATE))
    tag = hashlib.md5(seed.encode()).hexdigest()[:8]
    html_path = os.path.join(a.out_dir, f"{a.name}-{tag}.html")
    build_html(data, html_path)

    n, overflow = measure(html_path)
    shot = os.path.join(a.out_dir, f"{a.name}-full.png")
    screenshot(html_path, n, shot)
    files = crop_pages(shot, n, a.out_dir, a.name)
    os.remove(shot)

    print(json.dumps({"pages": n, "files": files,
                      "overflow_blocks": overflow, "html": html_path},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
