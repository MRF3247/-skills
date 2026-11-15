#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML/网页 → 完整高清长图（Playwright + 系统 Chrome）
用法：改 SRC / OUT 后 python3 html_to_image.py
要点：① 解除内部滚动容器（el-main 等）② overflowX 必须 clip（防离屏 canvas 撑宽）③ 2x 像素密度
"""
from playwright.sync_api import sync_playwright

SRC = "/path/to/page.html"           # 本地 HTML 绝对路径（file:// 加载）
OUT = "/path/to/output_长图.png"      # 输出 PNG

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        headless=True)  # 用系统 Chrome，避免 playwright install 版本不匹配
    page = browser.new_page(viewport={"width": 1280, "height": 900},
                            device_scale_factor=2)  # 2x 高清
    page.goto(f"file://{SRC}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(1500)  # 等字体/图片渲染
    # 解除内部滚动容器：overflowX=clip（可与 visible 共存且不撑宽）+ overflowY=visible
    page.evaluate("""() => {
        const els = [...document.querySelectorAll('*')].filter(e => {
            const s = getComputedStyle(e);
            return (s.overflowY === 'auto' || s.overflowY === 'scroll' || s.overflowY === 'hidden');
        });
        els.forEach(e => {
            e.style.overflowX = 'clip';
            e.style.overflowY = 'visible';
        });
        document.body.style.height = 'auto';
        document.documentElement.style.height = 'auto';
    }""")
    page.wait_for_timeout(500)
    w = page.evaluate("document.documentElement.scrollWidth")
    h = page.evaluate("document.documentElement.scrollHeight")
    print(f"页面尺寸: {w} x {h} CSS px (截图 2x → {w*2} x {h*2} px)")
    assert w <= 1280, f"页面被撑宽到 {w}px，检查离屏元素（overflowX 应为 clip）"
    page.screenshot(path=OUT, full_page=True)
    browser.close()

import os
print(f"已保存: {OUT} ({os.path.getsize(OUT)/1024/1024:.1f} MB)")
