#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ESMO 2026 专题 · 封面底图程序化绘制（扁平矢量，品牌单色蓝）
三种场景：pocket（激酶口袋被小分子占据）、adc（受体 + 抗体偶联药物）、checkpoint（PD-1/PD-L1 被封堵）
器官轮廓：lung / bladder / stomach / uterus / bone / colon（简化扁平剪影，仅作氛围）
输出 1200x1600，底部 y>=1080 留白给文案。
"""
from PIL import Image, ImageDraw
import math, random, sys, json

S = 3
W, H = 1200, 1600
CREAM  = (253, 251, 241)
BLUE_D = (18, 80, 161)
BLUE_M = (36, 109, 180)
BLUE_B = (58, 136, 199)
BLUE_C = (108, 157, 202)
BLUE_L = (144, 189, 220)
BLUE_P = (191, 212, 226)
BLUE_Q = (222, 234, 242)


class Canvas:
    def __init__(self):
        self.img = Image.new("RGB", (W * S, H * S), CREAM)
        self.d = ImageDraw.Draw(self.img)

    def rr(self, xy, r, fill):
        self.d.rounded_rectangle([c * S for c in xy], radius=r * S, fill=fill)

    def circ(self, cx, cy, r, fill):
        self.d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=fill)

    def line(self, p0, p1, w, fill):
        self.d.line([p0[0] * S, p0[1] * S, p1[0] * S, p1[1] * S], fill=fill, width=int(w * S))

    def poly(self, pts, fill):
        self.d.polygon([(x * S, y * S) for x, y in pts], fill=fill)

    def save(self, path):
        self.img.resize((W, H), Image.LANCZOS).save(path)


def bg_deco(c):
    random.seed(7)
    pts = [(150, 250, 26), (1050, 210, 18), (120, 760, 16), (1085, 700, 30), (200, 1000, 20),
           (1010, 1020, 24), (300, 150, 12), (940, 420, 14), (620, 130, 10), (760, 250, 8)]
    for cx, cy, r in pts:
        c.circ(cx, cy, r, BLUE_Q)


# ---------------- 器官剪影（氛围层，半透明感用浅色平涂） ----------------
def organ(c, kind):
    if kind == "lung":
        c.poly([(600, 300), (520, 330), (430, 420), (390, 560), (400, 700), (450, 800),
                (540, 830), (585, 800), (585, 380)], BLUE_Q)
        c.poly([(600, 300), (680, 330), (770, 420), (810, 560), (800, 700), (750, 800),
                (660, 830), (615, 800), (615, 380)], BLUE_Q)
        c.rr([578, 250, 622, 420], 18, BLUE_Q)
    elif kind == "bladder":
        c.circ(600, 620, 190, BLUE_Q)
        c.rr([575, 380, 625, 450], 16, BLUE_Q)
    elif kind == "stomach":
        c.circ(560, 590, 165, BLUE_Q)
        c.circ(690, 700, 120, BLUE_Q)
        c.rr([520, 380, 566, 470], 18, BLUE_Q)
    elif kind == "uterus":
        c.poly([(600, 430), (700, 520), (660, 760), (540, 760), (500, 520)], BLUE_Q)
        c.circ(470, 480, 52, BLUE_Q)
        c.circ(730, 480, 52, BLUE_Q)
    elif kind == "bone":
        c.rr([560, 330, 640, 830], 40, BLUE_Q)
        c.circ(540, 360, 62, BLUE_Q)
        c.circ(660, 360, 62, BLUE_Q)
        c.circ(540, 800, 52, BLUE_Q)
        c.circ(660, 800, 52, BLUE_Q)
    else:  # 通用
        c.circ(600, 620, 200, BLUE_Q)


# ---------------- 场景 1：pocket（两个口袋，一个被小分子占住） ----------------
def scene_pocket(c):
    """一个放大的球形靶蛋白居中，侧上方切出一个六边形口袋，里面嵌着一颗小分子。"""
    cx, cy, r = 600, 600, 210
    c.circ(cx, cy, r, BLUE_L)                              # 靶蛋白（纯平涂，不放内部圆，避免像脸）
    # 口袋：贴着球体右上边缘的六边形凹腔（一半在球内、一半敞开）
    hx, hy, hr = cx + 150, cy - 130, 78
    c.poly([(hx + hr * math.cos(math.radians(a)), hy + hr * math.sin(math.radians(a))) for a in range(0, 360, 60)], CREAM)
    c.poly([(hx + (hr - 18) * math.cos(math.radians(a)), hy + (hr - 18) * math.sin(math.radians(a)))
            for a in range(0, 360, 60)], BLUE_C)           # 腔壁
    c.poly([(hx + (hr - 34) * math.cos(math.radians(a)), hy + (hr - 34) * math.sin(math.radians(a)))
            for a in range(0, 360, 60)], BLUE_Q)           # 空腔
    # 药物：深蓝六边形卡在腔里
    dhr = 32
    c.poly([(hx + dhr * math.cos(math.radians(a + 30)), hy + dhr * math.sin(math.radians(a + 30)))
            for a in range(0, 360, 60)], (10, 52, 110))


# ---------------- 场景 2：adc（膜 + 受体 + 抗体偶联药物） ----------------
def scene_adc(c):
    """脂双层膜 + 4 个跨膜受体；一个抗体用两条 Fab 臂夹住受体胞外球头，Fc 端挂 3 个细胞毒载荷。"""
    my = 700
    # 脂双层：两条浅蓝带，中间米白缝隙，缝里点几颗磷脂头
    c.rr([190, my - 30, 1010, my - 6], 12, BLUE_L)
    c.rr([190, my + 6, 1010, my + 30], 12, BLUE_L)
    for x in range(215, 1000, 46):
        c.circ(x, my - 18, 4, BLUE_P)
        c.circ(x, my + 18, 4, BLUE_P)
    for x in (330, 500, 670, 840):
        c.rr([x - 12, my - 120, x + 12, my + 120], 12, BLUE_C)      # 跨膜段
        c.circ(x, my - 148, 32, BLUE_B)                             # 胞外球头（靶点）
        c.rr([x - 20, my + 120, x + 20, my + 168], 8, BLUE_M)       # 胞内段
    # 抗体：两条 Fab 臂朝下夹住第 2 个受体的球头，Fc 段朝上
    tx, ty = 500, my - 300
    c.poly([(tx - 16, ty + 96), (tx - 74, ty + 6), (tx - 52, ty - 24), (tx - 4, ty + 62)], BLUE_D)
    c.poly([(tx + 16, ty + 96), (tx + 74, ty + 6), (tx + 52, ty - 24), (tx + 4, ty + 62)], BLUE_D)
    c.rr([tx - 17, ty - 96, tx + 17, ty - 6], 14, BLUE_D)            # Fc 段
    # 载荷：三颗深蓝圆点用短杆挂在 Fc 顶端（药物偶联的位置）
    c.line((tx, ty - 96), (tx, ty - 150), 8, BLUE_B)
    for dx, dy in ((-30, -186), (30, -186), (0, -206)):
        c.line((tx, ty - 150), (tx + dx, ty + dy + 22), 7, BLUE_B)
        c.circ(tx + dx, ty + dy, 20, (10, 52, 110))


# ---------------- 场景 3：checkpoint（PD-1/PD-L1 被抗体堵住） ----------------
def scene_checkpoint(c):
    # 上方 T 细胞、下方肿瘤细胞，中间是受体-配体对接面
    c.circ(600, 400, 150, BLUE_L)
    c.circ(560, 360, 70, BLUE_C)
    c.rr([575, 520, 625, 610], 14, BLUE_C)                       # PD-1 受体杆
    c.rr([559, 596, 641, 640], 20, BLUE_B)                        # PD-1 头部
    c.circ(600, 830, 165, BLUE_M)
    c.circ(645, 800, 74, BLUE_B)
    c.rr([575, 690, 625, 690 + 84], 14, BLUE_B)                   # PD-L1 杆
    c.rr([557, 686, 643, 730], 20, BLUE_D)                        # PD-L1 头部
    # 抗体：Fc 在右侧，两条 Fab 臂分别顶住上方 PD-1 与下方 PD-L1，把两者隔开
    c.rr([700, 618, 850, 672], 26, BLUE_D)                  # Fc 段（横向胶囊）
    c.line((712, 634), (624, 606), 26, BLUE_D)              # 上臂 → 顶住 PD-1 头部
    c.line((712, 656), (624, 712), 26, BLUE_D)              # 下臂 → 顶住 PD-L1 头部
    c.circ(624, 606, 15, BLUE_D)
    c.circ(624, 712, 15, BLUE_D)


SCENES = {"pocket": scene_pocket, "adc": scene_adc, "checkpoint": scene_checkpoint}


def build(scene, organ_kind, out):
    c = Canvas()
    bg_deco(c)
    organ(c, organ_kind)
    SCENES[scene](c)
    # 底部深蓝色块：承载白色主副文案（与已交付封面一致）
    c.rr([0, 980, W, H + 40], 0, BLUE_D)
    c.rr([0, 1010, W, H + 40], 0, BLUE_M)
    c.save(out)
    return out


if __name__ == "__main__":
    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    build(cfg.get("scene", "adc"), cfg.get("organ", "generic"), cfg["out"])
    print("ok", cfg["out"])
