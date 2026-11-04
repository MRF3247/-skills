#!/usr/bin/env python3
"""论文速读卡 v3（三线表 + 论文标题 + 自动分页）：每章可多页，中英对照。

版式（1080×1440，白底）：
  天头：logo 居中 + 关键词一行居中
  论文标题：中文大字 + 英文原标题小字（仅首页）
  三线表：顶粗线 → 「Abstract 摘要」→ 栏目细线 → 子标题（Methods · 方法）→ 英文 → 中文 → 底粗线
  地脚：品牌蓝（#006EBB）粗条，白色出处 + 页码
装不下就自动分页：out-1.png / out-2.png …，续页标题带「（续）」。

用法：
  python3 compose_paper_card.py --out card.png --section Abstract --section-cn 摘要 \
      --paper-title "中文标题" --paper-title-en "English title…" \
      --block "Methods · 方法|EN|中文" --source "PubMed · …"
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1440
X0, X1 = 52, 1028
BRAND = (0, 110, 187)
INK = (28, 33, 40)
RULE = (32, 38, 46)
CN_INK = (30, 44, 66)
MUTED = (122, 132, 146)
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
FONTS = [("/Users/Jin/Library/Fonts/MiSans-Medium.ttf", 0),
         ("/Users/Jin/Library/Fonts/MiSans-Regular.ttf", 0),
         ("/System/Library/Fonts/Hiragino Sans GB.ttc", 0)]
FONT_HEAVY = [("/Users/Jin/Library/Fonts/MiSans-Heavy.ttf", 0),
              ("/Users/Jin/Library/Fonts/MiSans-Bold.ttf", 0)] + FONTS

FOOT_BAR = 66


def font(size, heavy=False):
    for p, i in (FONT_HEAVY if heavy else FONTS):
        try:
            return ImageFont.truetype(p, size, index=i)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap(text, f, max_w, d):
    if " " in text and sum(c.isascii() for c in text) > len(text) * 0.5:
        lines, cur = [], ""
        for w in text.split():
            trial = (cur + " " + w).strip()
            if d.textlength(trial, font=f) > max_w and cur:
                lines.append(cur); cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=f) > max_w and cur:
            # 不要把一个英文/数字词从中间拆开（如 dMMR → dM / MR）
            if ch.isascii() and ch.isalnum() and cur[-1:].isascii() and cur[-1:].isalnum():
                j = len(cur)
                while j > 0 and cur[j - 1].isascii() and cur[j - 1].isalnum():
                    j -= 1
                if j > 0 and j < len(cur):
                    lines.append(cur[:j].rstrip()); cur = cur[j:] + ch
                    continue
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


class Card:
    def __init__(self, en=19, cn=22, t_en=30, t_cn=42, sec=44, fig_w=300):
        self.fs_en, self.fs_cn = en, cn
        self.fig_w = fig_w
        self.fs_t_en, self.fs_t_cn, self.fs_sec = t_en, t_cn, sec
        self.canvas = Image.new("RGB", (W, H), "white")
        self.d = ImageDraw.Draw(self.canvas)

    def header(self, title_en="", title_cn="", first=True, keywords="医学前沿 · 科研动态 · 医务生活"):
        """P1 天头：第一行 中文标题（左）+ logo（右）；第二行整行英文标题。
        后续页：只保留右上角 logo。"""
        top = 40
        logo = Image.open(os.path.join(ASSETS, "logo.png")).convert("RGBA")
        lh = 34
        lw = int(logo.width * lh / logo.height)
        logo_small = logo.resize((lw, lh), Image.LANCZOS)
        self.canvas.paste(logo_small, (X1 - lw, top), logo_small)

        if not first:
            if keywords:
                fk = font(16)
                self.d.text((X1 - self.d.textlength(keywords, font=fk), top + lh + 8), keywords, font=fk, fill=MUTED)
                return top + lh + 8 + 26
            return top + lh + 22

        fk = font(16)
        if keywords:
            self.d.text((X1 - self.d.textlength(keywords, font=fk), top + lh + 8), keywords, font=fk, fill=MUTED)

        # 第一行：中文标题（左），与右侧 logo 同一行
        left_w = X1 - X0 - lw - 40
        y = top
        if title_cn:
            f = font(self.fs_t_cn, heavy=True)
            for ln in wrap(title_cn, f, left_w, self.d):
                self.d.text((X0, y), ln, font=f, fill=BRAND)
                y += int(self.fs_t_cn * 1.3)

        # 第二行：整行英文标题（小字）
        y = max(y, top + lh + 8 + 20) + 10
        if title_en:
            f = font(self.fs_t_en, heavy=True)
            for ln in wrap(title_en, f, X1 - X0, self.d):
                self.d.text((X0, y), ln, font=f, fill=(70, 80, 94))
                y += int(self.fs_t_en * 1.4)
        return y + 22

    def section_head(self, title, title_cn, y):
        self.d.rectangle([X0, y, X1, y + 5], fill=RULE)   # 顶粗线
        y += 5 + 34
        f = font(self.fs_sec, heavy=True)
        self.d.text((X0, y), title, font=f, fill=INK)
        if title_cn:
            w = self.d.textlength(title, font=f)
            fc = font(32, heavy=True)
            self.d.text((X0 + w + 24, y + 10), title_cn, font=fc, fill=BRAND)
        y += self.fs_sec + 20
        self.d.rectangle([X0, y, X0 + int((X1 - X0) * 0.42), y + 1], fill=(170, 178, 188))  # 细线：比顶线细、且比顶线短
        return y + 2 + 26

    def block_height(self, b):
        sub, en, cn, img = (b + ("",))[:4]
        h = 0
        if sub:
            h += int(self.fs_cn * 1.7)
        if en:
            h += len(wrap(en, font(self.fs_en), X1 - X0, self.d)) * int(self.fs_en * 1.46) + 10
        if cn:
            h += len(wrap(cn, font(self.fs_cn), X1 - X0 - 22, self.d)) * int(self.fs_cn * 1.5) + 8
        if img:
            try:
                im = Image.open(img)
                iw = min(self.fig_w, im.width)
                ih = int(im.height * iw / im.width)
                h = max(h, ih + 10)
            except Exception:
                pass
        return h

    def draw_block(self, b, y):
        sub, en, cn, img = (b + ("",))[:4]
        img_obj = None
        text_w = X1 - X0
        if img:
            try:
                img_obj = Image.open(img).convert("RGB")
                iw = min(self.fig_w, img_obj.width)
                ih = int(img_obj.height * iw / img_obj.width)
                img_obj = img_obj.resize((iw, ih), Image.LANCZOS)
                text_w = X1 - X0 - iw - 28
            except Exception:
                img_obj = None
        if sub:
            f = font(self.fs_cn - 2, heavy=True)
            self.d.text((X0, y), sub, font=f, fill=BRAND)
            y += int(self.fs_cn * 1.7)
        y_text_start = y
        if en:
            f = font(self.fs_en)
            for ln in wrap(en, f, text_w, self.d):
                self.d.text((X0, y), ln, font=f, fill=INK)
                y += int(self.fs_en * 1.46)
            y += 10
        if cn:
            f = font(self.fs_cn)
            lines = wrap(cn, f, text_w - 22, self.d)
            h = len(lines) * int(self.fs_cn * 1.5)
            self.d.rectangle([X0, y + 3, X0 + 4, y + 3 + h - 8], fill=BRAND)
            for ln in lines:
                self.d.text((X0 + 20, y), ln, font=f, fill=CN_INK)
                y += int(self.fs_cn * 1.5)
        if img_obj is not None:
            self.canvas.paste(img_obj, (X1 - img_obj.width, y_text_start))
            y = max(y, y_text_start + img_obj.height + 6)
        return y

    def footer(self, y_last, source, page, total):
        # 用户 2026-11：底部不要再画粗黑线，直接蓝条
        self.d.rectangle([0, H - FOOT_BAR, W, H], fill=BRAND)
        f = font(19)
        if source:
            self.d.text((X0, H - FOOT_BAR + (FOOT_BAR - 19) / 2 - 2), source, font=f, fill=(255, 255, 255))
        if total > 1:
            tag = f"{page}/{total}"
            self.d.text((X1 - self.d.textlength(tag, font=f), H - FOOT_BAR + (FOOT_BAR - 19) / 2 - 2),
                        tag, font=f, fill=(255, 255, 255))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--section", required=True)
    ap.add_argument("--section-cn", default="")
    ap.add_argument("--paper-title", default="")
    ap.add_argument("--paper-title-en", default="")
    ap.add_argument("--block", action="append", default=[])
    ap.add_argument("--source", default="")
    ap.add_argument("--page-tags", default="", help="每页右上角小标签，用 | 分隔")
    ap.add_argument("--fs-en", type=int, default=19)
    ap.add_argument("--fs-cn", type=int, default=22)
    ap.add_argument("--fs-t-en", type=int, default=28, help="英文标题字号")
    ap.add_argument("--fs-t-cn", type=int, default=40, help="中文标题字号")
    ap.add_argument("--fs-sec", type=int, default=42, help="章节标题字号（如 Abstract）")
    a = ap.parse_args()

    blocks = []
    for b in a.block:
        parts = [x.strip() for x in b.split("|")]
        if len(parts) >= 3:
            blocks.append((parts[0], parts[1], parts[2], parts[3] if len(parts) >= 4 else ""))
        else:
            while len(parts) < 2:
                parts.append("")
            blocks.append(("", parts[0], parts[1], ""))

    # 先试默认字号装一页；装不下就分页（不缩字号）
    probe = Card(a.fs_en, a.fs_cn, a.fs_t_en, a.fs_t_cn, a.fs_sec)
    y0 = probe.header(a.paper_title_en, a.paper_title, first=True)
    y_start = probe.section_head(a.section, a.section_cn, y0)
    avail = (H - FOOT_BAR - 40) - y_start

    # 分页：先按“尽量均分”而不是“填满再换页”，避免末页只剩一小段
    heights = [probe.block_height(b) + 14 for b in blocks]
    total_h = sum(heights)
    import math
    n_pages = max(1, math.ceil(total_h / (avail * 0.96)))
    while True:
        target = total_h / n_pages
        pages, cur, hsum = [], [], 0
        for b, bh in zip(blocks, heights):
            if b[0].strip().upper() == "PAGEBREAK":
                if cur:
                    pages.append(cur); cur, hsum = [], 0
                continue
            if cur and (hsum + bh > avail or hsum + bh > target * 1.06):
                pages.append(cur); cur, hsum = [], 0
            cur.append(b); hsum += bh
        if cur:
            pages.append(cur)
        if all(sum(heights[blocks.index(b)] for b in pg) <= avail for pg in pages):
            break
        n_pages += 1

    total = len(pages)
    for i, chunk in enumerate(pages, 1):
        card = Card(a.fs_en, a.fs_cn, a.fs_t_en, a.fs_t_cn, a.fs_sec)
        y = card.header(a.paper_title_en, a.paper_title, first=(i == 1))
        if i == 1:
            y = card.section_head(a.section, a.section_cn, y)
        tags = [t.strip() for t in a.page_tags.split("|")] if a.page_tags else []
        if i - 1 < len(tags) and tags[i - 1]:
            ft = font(18)
            card.d.text((X1 - card.d.textlength(tags[i - 1], font=ft), y + 6), tags[i - 1], font=ft, fill=(140, 150, 165))
        used = sum(card.block_height(b) + 14 for b in chunk)
        page_avail = (H - FOOT_BAR - 40) - y        # 每页可用高度按本页实际表头算（续页表头更矮）
        leftover = max(0, page_avail - used)
        extra = min(150, int(leftover / max(1, len(chunk)))) if leftover > 40 else 0
        # 剩余空间再竖向居中，避免半页空白压在底部
        rest = leftover - extra * len(chunk)
        if rest > 60:
            y += rest // 2
        for b in chunk:
            y = card.draw_block(b, y) + 14 + extra
        card.footer(y - 14, a.source, i, total)
        out = a.out if total == 1 else a.out.replace(".png", f"-{i}.png")
        card.canvas.save(out)
        print(f"saved {out}  page {i}/{total}  y_end={y}")


if __name__ == "__main__":
    main()
