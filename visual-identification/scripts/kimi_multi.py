#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多图时间轴识图：一条消息塞多张图，让模型按时间顺序讲清动作。

用法:
    python3 kimi_multi.py "<问题>" <img1> <img2> ...

必须用带 PIL 的解释器跑（本机默认 python3 没有 PIL）:
    /Users/Jin/Documents/Hermes/venvs/huashu/bin/python3 kimi_multi.py ...

端点 api.kimi.com/coding；key 从 ~/Documents/Hermes/APIs/kimicode API.rtf 读（rtf 需 textutil 转纯文本）。
"""
import base64
import io
import json
import subprocess
import sys
import urllib.request

from PIL import Image

KEY_RTF = "/Users/Jin/Documents/Hermes/APIs/kimicode API.rtf"
API = "https://api.kimi.com/coding/v1/chat/completions"
MODEL = "k3-256k"


def load_key():
    r = subprocess.run(["/usr/bin/textutil", "-convert", "txt", KEY_RTF, "-stdout"],
                       capture_output=True, text=True)
    return r.stdout.strip().replace("\n", "").replace(" ", "")


def img_to_b64(path, max_side=1200):
    im = Image.open(path).convert("RGB")
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def ask(question, paths, max_tokens=900, timeout=240):
    content = []
    for p in paths:
        content.append({"type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_to_b64(p)}"}})
    content.append({"type": "text", "text": question})
    payload = {"model": MODEL, "messages": [{"role": "user", "content": content}],
               "max_tokens": max_tokens}
    req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {load_key()}",
                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        d = json.load(r)
    return d["choices"][0]["message"].get("content", "(空)")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    print(ask(sys.argv[1], sys.argv[2:]))
