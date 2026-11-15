#!/usr/bin/env python3
"""生成78张塔罗占位图：深紫夜空底 + 金框 + 牌名竖排文字 + 花色炼金符号
用法：改头部 SRC/DEST 两个路径后 python3 gen_placeholders.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = "/Users/Jin/Documents/书籍/玄学/塔罗与占星/韦特塔罗全书/assets/cards"      # 原版图目录（枚举78个文件名用）
DEST = "/Users/Jin/Documents/书籍/玄学/塔罗与占星/韦特塔罗全书-占位版/assets/cards"  # 占位图输出目录（须已存在）

# 中文牌名映射
MAJORS = {
    "00": "愚者", "01": "魔术师", "02": "女祭司", "03": "女皇", "04": "皇帝",
    "05": "教皇", "06": "恋人", "07": "战车", "08": "力量", "09": "隐士",
    "10": "命运之轮", "11": "正义", "12": "悬吊者", "13": "死神", "14": "节制",
    "15": "恶魔", "16": "高塔", "17": "星星", "18": "月亮", "19": "太阳",
    "20": "审判", "21": "世界",
}
SUITS = {"wands": ("权杖", "🜂"), "cups": ("圣杯", "🜄"), "swords": ("宝剑", "🜁"), "pentacles": ("星币", "🜃")}
RANKS = {"1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六", "7": "七",
         "8": "八", "9": "九", "10": "十", "page": "侍者", "knight": "骑士", "queen": "王后", "king": "国王"}

# 找系统里能显示中文的字体
FONT_CANDS = [
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
]
font_path = next((p for p in FONT_CANDS if os.path.exists(p)), None)
assert font_path, "找不到中文字体"

W, H = 400, 680  # 竖版塔罗比例
files = sorted(os.listdir(SRC))
count = 0
for fn in files:
    if not fn.endswith(".jpg"):
        continue
    stem = fn[:-4]
    # 解析牌名：大牌=编号-slug，小牌=花色-数字/宫廷
    if "-" in stem and stem.split("-")[0].isdigit():
        num, slug = stem.split("-", 1)
        name = MAJORS.get(num, slug)
        sym = "✦"
    else:
        suit, rank = stem.split("-", 1)
        sname, sym = SUITS[suit]
        name = f"{sname}{RANKS.get(rank, rank)}"

    img = Image.new("RGB", (W, H), (18, 14, 38))          # 深紫夜空底
    d = ImageDraw.Draw(img)
    # 细微纵向渐变
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(18+10*t), int(14+8*t), int(38+16*t)))
    # 双层金框
    d.rectangle([10, 10, W-11, H-11], outline=(201, 162, 39), width=3)
    d.rectangle([20, 20, W-21, H-21], outline=(140, 110, 40), width=1)
    # 角落星点
    for cx, cy in [(40, 40), (W-40, 40), (40, H-40), (W-40, H-40)]:
        d.ellipse([cx-3, cy-3, cx+3, cy+3], fill=(230, 200, 122))

    # 中央竖排牌名
    f_big = ImageFont.truetype(font_path, 52)
    f_sym = ImageFont.truetype(font_path, 64)
    ch_h = 60
    y0 = H//2 - (len(name)*ch_h)//2 - 20
    for i, ch in enumerate(name):
        bb = d.textbbox((0, 0), ch, font=f_big)
        d.text(((W-(bb[2]-bb[0]))//2, y0 + i*ch_h), ch, font=f_big, fill=(230, 200, 122))
    # 下方花色符号
    bb = d.textbbox((0, 0), sym, font=f_sym)
    d.text(((W-(bb[2]-bb[0]))//2, y0 + len(name)*ch_h + 26), sym, font=f_sym, fill=(160, 130, 60))

    img.save(os.path.join(DEST, fn), quality=88)
    count += 1

print(f"生成 {count} 张占位图")
