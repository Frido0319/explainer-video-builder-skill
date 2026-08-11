#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""画面卡片生成（白底学术风模板）。
用法：改下方 CONFIG 里的文案，运行 `python3 make_cards.py`，输出到 CONFIG.OUT_DIR。
验证过的版本参考：智信2026 演示视频（片头/背景/痛点/方案/预告/结束 6 张卡全部用它生成）。
"""
import os
from PIL import Image, ImageDraw, ImageFont

# ================= 可编辑配置区 =================
OUT_DIR = "cards"                      # 输出目录
W, H = 1920, 1080                      # 画布
FONT_DIR = "/usr/share/fonts/opentype/noto"

# 叙事文本（每张卡一条，按需增删）
TITLE = "项目名称"
TITLE_SUB = "一句话副题"
TITLE_GROUP = "课题组 / 团队"

BG_TITLE = "应用场景 · 标题"
BG_ITEMS = [                            # (图片路径, 名称, 描述)
    ("bg_images/bg_1.jpg", "场景一", "场景描述"),
    ("bg_images/bg_2.jpg", "场景二", "场景描述"),
    ("bg_images/bg_3.jpg", "场景三", "场景描述"),
]
BG_TRANS = "过渡句：而在该场景下，面临严峻挑战："

PAIN_TITLE = "核心问题 · 标题"
PAIN_LEAD = "问题引入一句话："
PAIN_ITEMS = [                          # (要点名, 描述)
    ("问题一", "问题描述"),
    ("问题二", "问题描述"),
    ("问题三", "问题描述"),
]
PAIN_FOOT1 = "补充一句，"
PAIN_FOOT2 = "再补一句，强调需要解决。"

SCHEME_TITLE = "核心方案 · 标题"
SCHEME_LEAD = "方案原理一句话："
SCHEME_ITEMS = [
    ("要点一", "要点描述"),
    ("要点二", "要点描述"),
    ("要点三", "要点描述"),
]
SCHEME_FOOT1 = "方案优势一句，"
SCHEME_FOOT2 = "方案优势二句。"

PREVIEW_BIG = "实测效果展示"
PREVIEW_SUB = "副标题一句"
PREVIEW_LINE1 = 320               # 上装饰线 y（与大字顶部 ≥40px）
PREVIEW_LINE2 = 660               # 下装饰线 y（与副字底部 ≥40px）
PREVIEW_BIGY = 465                # 大字中心 y（100px 字 → 415~515）
PREVIEW_SUBY = 578                # 副字中心 y（42px 字 → 557~599）

END_BIG = "课题组 / 团队名"
END_SUB = "项目名 · 一句话说明"
# ==============================================

# 配色
WHITE = (255, 255, 255)
BLACK = (20, 20, 25)
DARKG = (60, 60, 70)
BLUE  = (0, 90, 200)
RED   = (200, 40, 40)
GREEN = (0, 140, 90)
BANNER = (0, 63, 124)
PREVIEW_LINE_C = (0, 150, 90)


def font(size, variant="Regular"):
    return ImageFont.truetype(f"{FONT_DIR}/NotoSansCJK-{variant}.ttc", size)


def wrap_text(draw, text, fnt, max_w):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=fnt) <= max_w:
            cur += ch
        else:
            lines.append(cur)
            cur = ch
    if cur:
        lines.append(cur)
    return lines


def make_title_card(path):
    """片头：白底 + 深蓝横幅 + 白字（无校徽，可加 logo）。"""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 300, W, 820], fill=BANNER)
    d.text((W / 2, 440), TITLE, font=font(120, "Black"), fill=WHITE, anchor="ma")
    d.text((W / 2, 590), TITLE_SUB, font=font(54, "Bold"), fill=WHITE, anchor="ma")
    d.text((W / 2, 730), TITLE_GROUP, font=font(44, "Regular"), fill=WHITE, anchor="ma")
    img.save(path)


def img_cover(im, tw, th):
    """等比缩放后居中裁剪到 (tw,th)，不拉伸。"""
    im = im.convert("RGB")
    w, h = im.size
    s = max(tw / w, th / h)
    im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    nw, nh = im.size
    x = (nw - tw) // 2
    y = (nh - th) // 2
    return im.crop((x, y, x + tw, y + th))


def _heading(d, title, color, lead=None):
    fnt_h = font(56, "Bold")
    d.text((140, 110), title, font=fnt_h, fill=BLACK)
    d.line([(145, 200), (145 + d.textlength(title, font=fnt_h), 200)], fill=color, width=5)
    if lead:
        d.text((140, 290), lead, font=font(40, "Regular"), fill=BLACK)


def _bullets(d, items, dot_color, y0=420, step=120, x_name=230, x_desc=500):
    for name, desc in items:
        d.ellipse([160, y0 + 12, 190, y0 + 42], fill=dot_color)
        d.text((x_name, y0), name, font=font(42, "Bold"), fill=BLACK)
        d.text((x_desc, y0 + 4), desc, font=font(40, "Regular"), fill=DARKG)
        y0 += step


def make_bg_card(path):
    """背景：应用场景（三列实拍图 + 名称描述）。"""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _heading(d, BG_TITLE, BLUE)
    CW, CH, GAP, Y0 = 480, 280, 40, 260
    X0 = (W - (CW * 3 + GAP * 2)) // 2
    for i, (imf, name, desc) in enumerate(BG_ITEMS):
        x = X0 + i * (CW + GAP)
        try:
            img.paste(img_cover(Image.open(imf), CW, CH), (x, Y0))
        except Exception as e:
            print("  图片加载失败", imf, e)
        d.text((x + CW / 2, Y0 + CH + 62), name, font=font(42, "Bold"), fill=BLACK, anchor="ma")
        d.text((x + CW / 2, Y0 + CH + 122), desc, font=font(38, "Regular"), fill=DARKG, anchor="ma")
    d.text((W / 2, 940), BG_TRANS, font=font(44, "Bold"), fill=BLACK, anchor="ma")
    img.save(path)


def make_pain_card(path):
    """痛点：白底 + 红点要点。"""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _heading(d, PAIN_TITLE, RED, lead=PAIN_LEAD)
    _bullets(d, PAIN_ITEMS, RED)
    d.text((140, 820), PAIN_FOOT1, font=font(40, "Regular"), fill=BLACK)
    d.text((140, 880), PAIN_FOOT2, font=font(40, "Regular"), fill=BLACK)
    img.save(path)


def make_scheme_card(path):
    """方案：白底 + 蓝点要点。"""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    _heading(d, SCHEME_TITLE, BLUE, lead=SCHEME_LEAD)
    _bullets(d, SCHEME_ITEMS, BLUE)
    d.text((140, 820), SCHEME_FOOT1, font=font(40, "Regular"), fill=BLACK)
    d.text((140, 880), SCHEME_FOOT2, font=font(40, "Regular"), fill=BLACK)
    img.save(path)


def make_preview_card(path):
    """实测预告卡：深色渐变底 + 大字 + 上下装饰线（字线间距 ≥40px）。"""
    img = Image.new("RGB", (W, H), (27, 27, 47))
    d = ImageDraw.Draw(img)
    for x in range(W):
        dist = abs(x / (W - 1) - 0.5) * 2
        col = tuple(round(a + (b - a) * (1 - dist)) for a, b in
                    zip((14, 14, 22), (48, 48, 66)))
        d.line([(x, 0), (x, H)], fill=col)
    d.rectangle([690, PREVIEW_LINE1, 1230, PREVIEW_LINE1 + 2], fill=PREVIEW_LINE_C)
    d.rectangle([690, PREVIEW_LINE2, 1230, PREVIEW_LINE2 + 2], fill=PREVIEW_LINE_C)
    d.text((W / 2, PREVIEW_BIGY), PREVIEW_BIG, font=font(100, "Black"),
           fill=WHITE, anchor="mm")
    d.text((W / 2, PREVIEW_SUBY), PREVIEW_SUB, font=font(42, "Regular"),
           fill=(205, 205, 218), anchor="mm")
    img.save(path)


def make_demo_bg(path):
    """实测段背景：左右对称深色渐变（中间浅、两侧深），非模糊。"""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for x in range(W):
        dist = abs(x / (W - 1) - 0.5) * 2
        col = tuple(round(a + (b - a) * (1 - dist)) for a, b in
                    zip((16, 16, 24), (58, 58, 80)))
        d.line([(x, 0), (x, H)], fill=col)
    img.save(path)


def make_end_card(path):
    """结束页：白底居中大字 + 下方小字。"""
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    d.text((W / 2, H / 2 - 80), END_BIG, font=font(96, "Black"), fill=BLACK, anchor="ma")
    d.text((W / 2, H / 2 + 120), END_SUB, font=font(40, "Regular"), fill=DARKG, anchor="ma")
    img.save(path)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    jobs = [
        ("01_title.png", make_title_card),
        ("02_background.png", make_bg_card),
        ("03_pain.png", make_pain_card),
        ("04_scheme.png", make_scheme_card),
        ("07_preview.png", make_preview_card),
        ("demo_bg.png", make_demo_bg),
        ("09_end.png", make_end_card),
    ]
    for name, fn in jobs:
        fn(os.path.join(OUT_DIR, name))
        print("生成", name)
