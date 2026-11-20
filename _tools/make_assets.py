# -*- coding: utf-8 -*-
"""生成站点用到的图片资源（分享预览图与桌面图标）。

产物写进 src/assets/，构建时由 build.py 一并拷贝到 dist/assets/：
- src/assets/og.png        1200×630，社交平台分享预览图（程序绘制）
- src/assets/icon-180.png  180×180，apple-touch-icon（从根目录 icon.jpg 缩放）
- src/assets/favicon.ico   16/32/48 三档，浏览器标签页图标（同上）

用法：python _tools/make_assets.py
依赖：Pillow（缺失时提示安装后重试）；根目录需有 icon.jpg
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from console_utf8 import use_utf8_console

use_utf8_console()

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PILLOW = True
except ImportError:
    # 这里不能直接退出：build.py 会 import 本模块来画预览图，
    # 缺 Pillow 时应当让它回退到静态图，而不是把整个构建带崩。
    HAVE_PILLOW = False

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "src", "assets")

BG = (17, 17, 17)
CARD = (26, 26, 30)
ACCENT = (124, 108, 242)
TEXT = (245, 246, 248)
MUTED = (166, 170, 180)
# Windows 自带微软雅黑；非 Windows 环境改用 Pillow 默认字体
FONT_REG = r"C:\Windows\Fonts\msyh.ttc"
FONT_BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

# 字体候选：按顺序取第一个存在的。中文要靠 msyh 才能正常显示，
# 别的平台若没有中文字体，就退回 Pillow 自带字体（字形会不同，但不至于画不出来）。
FONT_CANDIDATES_REG = [FONT_REG, "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                       "/System/Library/Fonts/Helvetica.ttc"]
FONT_CANDIDATES_BOLD = [FONT_BOLD, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                        "/System/Library/Fonts/Helvetica.ttc"]


def font(path, size):
    """按候选列表找字体；都找不到就用 Pillow 默认字体。"""
    for cand in (path if isinstance(path, (list, tuple)) else [path]):
        if cand and os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except OSError:
                continue
    return ImageFont.load_default()


def rounded(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def spark(draw, cx, cy, r, color):
    """画一个四角星，与页面里的品牌标记同形。"""
    import math
    pts = []
    for i in range(8):
        ang = math.pi / 2 * (i / 2) - math.pi / 2
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=color)


def make_og(path, total=324, cats=33, sections=5):
    W, H = 1200, 630
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 背景上两层柔和光晕
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse((700, -260, 1360, 400), fill=(38, 33, 78))
    gd.ellipse((-260, 380, 380, 900), fill=(26, 30, 60))
    img = Image.blend(img, glow, 0.55)
    d = ImageDraw.Draw(img)

    # 品牌标记
    rounded(d, (80, 78, 176, 174), 28, ACCENT)
    spark(d, 128, 126, 34, (255, 255, 255))

    d.text((204, 96), "GUAN 提示词库", font=font(FONT_CANDIDATES_BOLD, 62), fill=TEXT)
    d.text((206, 176), "PROMPT LIBRARY", font=font(FONT_CANDIDATES_REG, 24), fill=MUTED)

    d.text((80, 268), "常用智能体提示词 · 分类检索 · 一键复制",
           font=font(FONT_CANDIDATES_REG, 38), fill=TEXT)
    d.text((80, 330), "从工程实现到学术写作，按场景归类整理；搜索即取、复制即用。",
           font=font(FONT_CANDIDATES_REG, 28), fill=MUTED)

    # 统计卡片
    stats = [("条提示词", str(total)), ("个分类", str(cats)), ("个场景", str(sections))]
    x = 80
    for label, value in stats:
        w = 250
        rounded(d, (x, 420, x + w, 520), 20, CARD)
        d.text((x + 26, 432), value, font=font(FONT_CANDIDATES_BOLD, 44), fill=TEXT)
        d.text((x + 26, 488), label, font=font(FONT_CANDIDATES_REG, 22), fill=MUTED)
        x += w + 24

    d.text((80, 556), "prompt.guanjihuan.com", font=font(FONT_CANDIDATES_REG, 24), fill=(140, 144, 156))
    img.save(path, "PNG", optimize=True)
    print("[assets] 生成 %s" % os.path.relpath(path, ROOT))


def make_icon(path_ico, path_180, source):
    """站点图标统一取自根目录 icon.jpg（西瓜图），整幅缩放不裁剪：ico 三档 + 180 触屏图标。"""
    src = Image.open(source).convert("RGB")
    src.resize((180, 180), Image.LANCZOS).save(path_180, format="PNG", optimize=True)
    src.resize((48, 48), Image.LANCZOS).save(
        path_ico, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    print("[assets] 生成 %s" % os.path.relpath(path_180, ROOT))
    print("[assets] 生成 %s" % os.path.relpath(path_ico, ROOT))


def library_counts():
    """读取当前库的真实统计（条数 / 分类数 / 分区数），用于预览图上的数字。"""
    import build as site_build
    errors = []
    categories, sections = site_build.collect(errors)
    total = sum(len(c["prompts"]) for c in categories)
    return total, len(categories), len(sections)


if __name__ == "__main__":
    if not HAVE_PILLOW:
        print("[assets] 需要 Pillow：pip install pillow")
        sys.exit(1)
    total, cats, secs = library_counts()
    make_og(os.path.join(ASSETS, "og.png"), total=total, cats=cats, sections=secs)
    icon_src = os.path.join(ROOT, "icon.jpg")
    if not os.path.exists(icon_src):
        print("[assets] 缺少根目录 icon.jpg，跳过图标生成")
        sys.exit(1)
    make_icon(os.path.join(ASSETS, "favicon.ico"),
              os.path.join(ASSETS, "icon-180.png"), icon_src)
