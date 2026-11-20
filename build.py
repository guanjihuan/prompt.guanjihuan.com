#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build.py — 从 src/prompts/*.md 生成静态站点 dist/

数据源：src/prompts/ 下的 Markdown，每个文件一个分类。
条目格式：
    ## 标题
    <!-- id: 全局唯一且不再变更的稳定标识 -->
    <!-- t: 标签1,标签2 -->
    <!-- s: 简洁表达（可选，仅在确有详略差异时保留） -->
    正文（一个自然段）

用法：
    python build.py            # 构建
    python build.py --check    # 只做校验，不产出
    python build.py --serve    # 构建后本地预览
"""

import datetime
import json
import os
import re
import shutil
import sys

from console_utf8 import use_utf8_console as _use_utf8_console  # 供 tests/ 与 _tools/ 复用

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")
PROMPT_DIR = os.path.join(SRC, "prompts")
ASSET_DIR = os.path.join(SRC, "assets")
I18N_DIR = os.path.join(SRC, "i18n", "en")
DIST = os.path.join(ROOT, "dist")

SITE_URL = "https://prompt.guanjihuan.com"

FRONT_RE = re.compile(r"^---\s*$")
TITLE_RE = re.compile(r"^##\s+(.*\S)\s*$")
ID_RE = re.compile(r"^<!--\s*id:\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*-->\s*$", re.I)
TAG_RE = re.compile(r"^<!--\s*t:\s*(.*?)\s*-->\s*$", re.I)
SHORT_RE = re.compile(r"^<!--\s*s:\s*(.*?)\s*-->\s*$", re.I)
NOTE_RE = re.compile(r"^<!--\s*n:\s*(.*?)\s*-->\s*$", re.I)
FENCE_RE = re.compile(r"^\s*(```|~~~)")

KNOWN_KEYS = {"id", "name", "icon", "desc", "order", "section"}

# 分区在侧栏的顺序。分类的 order 只决定全库分类的先后，分区位置在这里单独定；
# 没写进这个表的分区按分类首次出现的顺序接在后面。
SECTION_ORDER = [
    "通用任务",
    "办公事务",
    "软件工程",
    "界面与产品",
    "文档与表达",
    "学术研究",
    "智能体与指令",
]

# 侧栏固定图标（全部/收藏/自定义）与用户自建分类图标，分类图标不得占用
RESERVED_ICONS = {"✦", "★", "✚", "▪"}

# 形近字分组：同组内两个图标在小字号下容易被看成同一个，命中只提示不阻断
CONFUSABLE_GROUPS = [
    {"✦", "✧"},
    {"✱", "✳", "✻"},
    {"✎", "✍", "✒"},
    {"◎", "⊙", "◉", "⊚"},
    {"◐", "◑", "◒", "◓"},
    {"◨", "◧", "◩", "◪"},
    {"⬢", "⬦", "⬣"},
    {"▤", "▦", "▧", "▨", "▩"},
    {"≡", "☰"},
    {"⇄", "⇆", "⇅", "↔"},
    {"⟳", "↻", "↺", "⟲"},
    {"⌫", "⌦"},
    {"☼", "☀"},
    {"☑", "☒"},
    {"⧉", "⊠", "⊡"},
]


def use_utf8_console():
    """让中文输出在终端里正常显示（实现见 console_utf8.py）。"""
    return _use_utf8_console()


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------
def parse_frontmatter(lines, path, errors):
    meta = {}
    if not lines or not FRONT_RE.match(lines[0]):
        errors.append("%s: 缺少 frontmatter（--- 包裹的元信息）" % path)
        return meta, lines
    i = 1
    while i < len(lines) and not FRONT_RE.match(lines[i]):
        line = lines[i]
        if ":" in line:
            k, v = line.split(":", 1)
            k = k.strip()
            if k not in KNOWN_KEYS:
                errors.append("%s: 未知的前置字段 '%s'" % (path, k))
            meta[k] = v.strip().strip("\"'")
        elif line.strip():
            errors.append("%s: frontmatter 第 %d 行格式无法识别" % (path, i + 1))
        i += 1
    if i >= len(lines):
        errors.append("%s: frontmatter 未闭合" % path)
    return meta, lines[i + 1:]


def parse_category(path, errors):
    """解析一个分类文件。代码块内的 ## 不会被误判为新条目。"""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().replace("\r\n", "\n")
    lines = raw.split("\n")
    rel = os.path.basename(path)

    meta, body = parse_frontmatter(lines, rel, errors)

    items = []
    cur = None
    in_fence = False
    fence_marker = None

    for line in body:
        m = FENCE_RE.match(line)
        if m:
            marker = m.group(1)
            if not in_fence:
                in_fence, fence_marker = True, marker
            elif marker == fence_marker:
                in_fence, fence_marker = False, None
            if cur:
                cur["body"].append(line.rstrip())
            continue

        tm = None if in_fence else TITLE_RE.match(line)
        if tm:
            if cur:
                items.append(cur)
            cur = {"id": "", "title": tm.group(1), "tags": [], "short": "", "note": "", "body": []}
            continue

        if cur is None:
            continue

        id_m = ID_RE.match(line)
        if id_m:
            cur["id"] = id_m.group(1)
            continue
        tag_m = TAG_RE.match(line)
        if tag_m:
            cur["tags"] = [t.strip() for t in tag_m.group(1).split(",") if t.strip()]
            continue
        short_m = SHORT_RE.match(line)
        if short_m:
            cur["short"] = short_m.group(1).strip()
            continue
        note_m = NOTE_RE.match(line)
        if note_m:
            cur["note"] = note_m.group(1).strip()
            continue

        cur["body"].append(line.rstrip())

    if cur:
        items.append(cur)

    out = []
    for it in items:
        content = "\n".join(it["body"]).strip("\n")
        content = re.sub(r"\n{3,}", "\n\n", content)
        if not content:
            errors.append("%s: 条目「%s」正文为空" % (rel, it["title"]))
            continue
        if not it["tags"]:
            errors.append("%s: 条目「%s」缺少标签（<!-- t: ... -->）" % (rel, it["title"]))
        if it["short"] == content:
            it["short"] = ""
        if it["short"] and len(it["short"]) >= len(content):
            errors.append("%s: 条目「%s」的简洁表达不短于正文" % (rel, it["title"]))
        out.append({
            "id": it["id"],
            "title": it["title"],
            "tags": it["tags"],
            "short": it["short"],
            "note": it["note"],
            "content": content,
        })
    return meta, out


def collect(errors, warnings=None):
    files = sorted(f for f in os.listdir(PROMPT_DIR) if f.endswith(".md"))
    categories = []
    seen_cat = set()
    seen_titles = {}
    seen_icons = {}
    seen_prompt_ids = {}

    for fn in files:
        path = os.path.join(PROMPT_DIR, fn)
        meta, items = parse_category(path, errors)
        if not items:
            errors.append("%s: 分类内没有任何条目" % fn)
            continue

        cat_id = meta.get("id")
        if not cat_id:
            errors.append("%s: 缺少 id" % fn)
            cat_id = re.sub(r"^\d+-|\.md$", "", fn)
        if cat_id in seen_cat:
            errors.append("%s: 分类 id 重复 '%s'" % (fn, cat_id))
        seen_cat.add(cat_id)

        if not meta.get("name"):
            errors.append("%s: 缺少 name" % fn)

        icon = meta.get("icon", "")
        if not icon:
            errors.append("%s: 缺少 icon" % fn)
        elif icon in seen_icons:
            errors.append("%s: 图标 '%s' 与 %s 重复" % (fn, icon, seen_icons[icon]))
        elif icon in RESERVED_ICONS:
            errors.append("%s: 图标 '%s' 与侧栏固定图标重复" % (fn, icon))
        else:
            seen_icons[icon] = fn

        section = meta.get("section")
        if not section:
            errors.append("%s: 缺少 section" % fn)
            section = "未分组"

        if not meta.get("desc"):
            errors.append("%s: 缺少 desc" % fn)

        order_raw = meta.get("order", "99")
        try:
            order = int(order_raw)
        except ValueError:
            errors.append("%s: order 不是整数 '%s'" % (fn, order_raw))
            order = 99

        prompts = []
        for it in items:
            item_id = it["id"]
            if not item_id:
                errors.append("%s: 条目「%s」缺少稳定 id（<!-- id: ... -->）" % (fn, it["title"]))
            elif item_id in seen_prompt_ids:
                errors.append("%s: 条目 id 与 %s 重复 —— '%s'"
                              % (fn, seen_prompt_ids[item_id], item_id))
            else:
                seen_prompt_ids[item_id] = fn
            key = it["title"].strip().lower()
            if key in seen_titles:
                errors.append("%s: 标题与 %s 重复 —— 「%s」"
                              % (fn, seen_titles[key], it["title"]))
            seen_titles[key] = fn
            # 缺简洁表达不拦构建，但要点名提醒：卡片会少一个版本，
            # 「简洁表达」缺失的条目历史上反复漏过，新增时顺手补上
            if not it["short"] and warnings is not None:
                warnings.append("%s: 条目「%s」没有简洁表达（s 字段），卡片只会有一个版本"
                                % (fn, it["title"]))
            prompts.append({
                "id": item_id,
                "title": it["title"],
                "tags": it["tags"],
                "short": it["short"],
                "note": it["note"],
                "content": it["content"],
            })

        categories.append({
            "id": cat_id,
            "name": meta.get("name", cat_id),
            "icon": icon,
            "desc": meta.get("desc", ""),
            "section": section,
            "order": order,
            "prompts": prompts,
        })

    categories.sort(key=lambda c: (c["order"], c["name"]))

    # 形近图标提示：字符不同但外观接近，侧栏里看上去像重复
    if warnings is not None:
        by_icon = {}
        for c in categories:
            by_icon.setdefault(c["icon"], []).append(c["name"])
        for group in CONFUSABLE_GROUPS:
            hits = [(ic, by_icon[ic]) for ic in sorted(group) if ic in by_icon]
            for i in range(len(hits)):
                for j in range(i + 1, len(hits)):
                    warnings.append("图标 '%s'（%s）与 '%s'（%s）外形相近，视觉上容易被当成重复"
                                    % (hits[i][0], "、".join(hits[i][1]),
                                       hits[j][0], "、".join(hits[j][1])))

    # 分区：按分类首次出现的顺序归并，再按 SECTION_ORDER 调整侧栏里的先后。
    # 分类的 order 只管全库分类的排序（42~49 号的办公分类会排在末尾），
    # 分区在侧栏的位置单独在这里定，免得为了挪一个分区去重排几十个分类的编号。
    sections = []
    seen_sec = set()
    for c in categories:
        if c["section"] in seen_sec:
            continue
        seen_sec.add(c["section"])
        sections.append({
            "name": c["section"],
            "categories": [x["id"] for x in categories if x["section"] == c["section"]],
        })

    def section_rank(sec):
        name = sec["name"]
        return SECTION_ORDER.index(name) if name in SECTION_ORDER else len(SECTION_ORDER)

    sections.sort(key=section_rank)

    return categories, sections


# --------------------------------------------------------------------------
# 英文译文与构建
# --------------------------------------------------------------------------
def load_english(categories, errors):
    """读取英文翻译并逐 id 对账；测试用的临时站点没有翻译目录时保持单语。"""
    root = os.path.join(SRC, "i18n")
    en_dir = os.path.join(root, "en")
    if not os.path.isdir(en_dir):
        return None

    out = {"sections": {}, "categories": {}, "prompts": {}}
    sections_path = os.path.join(root, "sections.json")
    try:
        with open(sections_path, "r", encoding="utf-8") as f:
            sections = json.load(f)
        if not isinstance(sections, dict) or not all(
                isinstance(k, str) and isinstance(v, str) and k and v.strip()
                for k, v in sections.items()):
            raise ValueError("每个分区都需要非空的中英文名称")
        out["sections"] = sections
    except (OSError, ValueError) as exc:
        errors.append("英文分区翻译无法读取：%s" % exc)
        sections = {}

    source_files = sorted(f for f in os.listdir(PROMPT_DIR) if f.endswith(".md"))
    expected_json = {os.path.splitext(f)[0] + ".json" for f in source_files}
    actual_json = {f for f in os.listdir(en_dir) if f.endswith(".json")}
    for name in sorted(expected_json - actual_json):
        errors.append("英文翻译缺少文件：src/i18n/en/%s" % name)
    for name in sorted(actual_json - expected_json):
        errors.append("英文翻译存在无对应分类的文件：src/i18n/en/%s" % name)

    category_by_id = {c["id"]: c for c in categories}
    seen_prompt_ids = set()
    for filename in source_files:
        json_name = os.path.splitext(filename)[0] + ".json"
        if json_name not in actual_json:
            continue
        path = os.path.join(en_dir, json_name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                translated = json.load(f)
            if not isinstance(translated, dict):
                raise ValueError("顶层必须是对象")
        except (OSError, ValueError) as exc:
            errors.append("%s: 英文翻译无法读取（%s）" % (json_name, exc))
            continue

        parse_errors = []
        meta, items = parse_category(os.path.join(PROMPT_DIR, filename), parse_errors)
        cat_id = meta.get("id", "")
        category = translated.get("category")
        if (not isinstance(category, dict) or
                not isinstance(category.get("name"), str) or not category.get("name", "").strip() or
                not isinstance(category.get("desc"), str) or not category.get("desc", "").strip()):
            errors.append("%s: category 需要非空的 name 与 desc" % json_name)
        elif cat_id in category_by_id:
            out["categories"][cat_id] = {"name": category["name"], "desc": category["desc"]}

        prompts = translated.get("prompts")
        if not isinstance(prompts, dict):
            errors.append("%s: prompts 必须是按条目 id 索引的对象" % json_name)
            continue
        expected = {item["id"]: item for item in items}
        for item_id in sorted(set(expected) - set(prompts)):
            errors.append("%s: 条目 %s 缺英文翻译" % (json_name, item_id))
        for item_id in sorted(set(prompts) - set(expected)):
            errors.append("%s: 英文翻译含未知条目 id %s" % (json_name, item_id))
        for item_id, source in expected.items():
            tr = prompts.get(item_id)
            if not isinstance(tr, dict):
                if item_id in prompts:
                    errors.append("%s: 条目 %s 的英文翻译必须是对象" % (json_name, item_id))
                continue
            if set(tr) != {"title", "tags", "short", "content"}:
                errors.append("%s: 条目 %s 的字段必须恰好为 title/tags/short/content" % (json_name, item_id))
                continue
            valid = all(isinstance(tr.get(k), str) for k in ("title", "short", "content"))
            valid = valid and isinstance(tr.get("tags"), list) and all(
                isinstance(tag, str) and tag.strip() for tag in tr.get("tags", []))
            if not valid or not tr["title"].strip() or not tr["content"].strip():
                errors.append("%s: 条目 %s 的英文标题、正文或标签格式不正确" % (json_name, item_id))
                continue
            if len(tr["tags"]) != len(source["tags"]):
                errors.append("%s: 条目 %s 的英文标签数量与中文不一致" % (json_name, item_id))
            if bool(source["short"]) != bool(tr["short"].strip()):
                errors.append("%s: 条目 %s 的简洁表达有无与中文不一致" % (json_name, item_id))
            if item_id in seen_prompt_ids:
                errors.append("%s: 英文条目 id 重复 %s" % (json_name, item_id))
            seen_prompt_ids.add(item_id)
            out["prompts"][item_id] = tr

    for c in categories:
        if c["id"] not in out["categories"]:
            errors.append("分类 %s 缺英文名称或说明" % c["id"])
        if c["section"] not in out["sections"]:
            errors.append("分区「%s」缺英文名称" % c["section"])
    return out


def build(write=True):
    errors = []
    warnings = []
    categories, sections = collect(errors, warnings)
    english = load_english(categories, errors)

    # 在清空旧产物前完成所有可预检项目，失败时保留上一份可用构建。
    template_path = os.path.join(SRC, "index.html")
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()
        if "/*__PROMPT_DATA__*/" not in html:
            errors.append("模板中找不到数据占位符 /*__PROMPT_DATA__*/")
    except OSError as exc:
        errors.append("无法读取页面模板：%s" % exc)
        html = ""

    if errors:
        print("[check] 发现 %d 个问题：" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1

    print("[check] 数据校验通过")
    for w in warnings:
        print("  ! %s" % w)
    if not write:
        return 0

    if os.path.isdir(DIST):
        # 目录可能被预览服务器占用，退化为「清空内容」而不是删除目录本身。
        shutil.rmtree(DIST, ignore_errors=True)
        if os.path.isdir(DIST):
            for name in os.listdir(DIST):
                path = os.path.join(DIST, name)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
    os.makedirs(DIST, exist_ok=True)

    total = sum(len(c["prompts"]) for c in categories)
    data = {
        "site": {
            "title": "GUAN 提示词库",
            "subtitle": "常用智能体提示词 · 分类检索 · 一键复制",
            "updated": datetime.date.today().isoformat(),
        },
        "sections": sections,
        "categories": categories,
    }
    if english is not None:
        data["en"] = english

    if errors:
        print("[check] 发现 %d 个问题：" % len(errors))
        for e in errors:
            print("  - " + e)
        return 1

    # 资源：复制并计算内容哈希，避免线上命中旧缓存
    import hashlib
    dist_assets = os.path.join(DIST, "assets")
    os.makedirs(dist_assets, exist_ok=True)
    versions = {}
    for name in sorted(os.listdir(ASSET_DIR)):
        with open(os.path.join(ASSET_DIR, name), "rb") as fh:
            blob = fh.read()
        versions[name] = hashlib.sha1(blob).hexdigest()[:8]
        with open(os.path.join(dist_assets, name), "wb") as fh:
            fh.write(blob)

    # 分享预览图：用库里的真实数字重画一遍（缺 Pillow 时沿用 src/assets 里的静态图）
    og_path = os.path.join(dist_assets, "og.png")
    if os.path.exists(og_path):
        try:
            from _tools import make_assets
            if not make_assets.HAVE_PILLOW:
                raise RuntimeError("未安装 Pillow")
            make_assets.make_og(og_path, total=total, cats=len(categories),
                                sections=len(sections))
            with open(og_path, "rb") as fh:
                versions["og.png"] = hashlib.sha1(fh.read()).hexdigest()[:8]
        except Exception as exc:  # Pillow 缺失或绘图出错都不该让构建失败
            print("[build] 预览图沿用静态版本（%s）" % exc)

    # 模板注入：payload 用紧凑格式（dist 是产物，不需要可读性），比缩进版小约 15%；
    # `</` 必须转义，否则内容里的 </script> 会提前闭合脚本块。
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = html.replace("/*__PROMPT_DATA__*/", payload)
    for name, ver in versions.items():
        html = html.replace('assets/%s"' % name, 'assets/%s?v=%s"' % (name, ver))

    # 产物一律写 LF：Windows 默认会写成 CRLF，那样本机 build 出来的 dist
    # 与 Linux CI 重建的产物行尾符不同，CI 的产物同步检查会一直误报。
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    # 404 页面：静态托管下任意路径都有落到的地方
    not_found = os.path.join(SRC, "404.html")
    if os.path.exists(not_found):
        with open(not_found, "r", encoding="utf-8") as f:
            nf = f.read()
        for name, ver in versions.items():
            nf = nf.replace('assets/%s"' % name, 'assets/%s?v=%s"' % (name, ver))
        with open(os.path.join(DIST, "404.html"), "w", encoding="utf-8", newline="\n") as f:
            f.write(nf)

    # robots / sitemap
    with open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % SITE_URL)

    today = datetime.date.today().isoformat()
    with open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8", newline="\n") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        f.write("  <url>\n    <loc>%s/</loc>\n    <lastmod>%s</lastmod>\n"
                "    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>\n"
                % (SITE_URL, today))
        f.write("</urlset>\n")

    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(DIST) for f in fs)
    print("[build] %d 个分区，%d 个分类，%d 条提示词 -> %s（%.1f KB）"
          % (len(sections), len(categories), total, DIST, size / 1024.0))
    return 1 if errors else 0


def serve():
    import http.server
    import socket
    import socketserver

    class Handler(http.server.SimpleHTTPRequestHandler):
        """未知路径回站点自带的 404 页面。

        线上由 nginx 把 404 落到 /404.html；预览服务器用默认处理器的话
        返回的是 Python 的英文报错页，与线上不一致，预览看不出真实效果。
        """

        def send_error(self, code, message=None, explain=None):
            if code == 404:
                page = os.path.join(DIST, "404.html")
                if os.path.exists(page):
                    with open(page, "rb") as f:
                        body = f.read()
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
            super().send_error(code, message, explain)

    port = 8777
    # 端口已经被别的预览服务器占着就别再起一个：Windows 上开了
    # allow_reuse_address 的话两个服务器会同时监听，访问时随机落到哪一个，
    # 表现为「改了 dist 有时刷新还是旧页面」。先探一下再决定。
    probe = socket.socket()
    probe.settimeout(0.5)
    try:
        probe.connect(("127.0.0.1", port))
    except OSError:
        pass
    else:
        probe.close()
        print("[serve] 端口 %d 已被占用（可能还有一个预览服务器在跑）。"
              "先停掉它，或换个端口再试。" % port)
        return 1
    finally:
        try:
            probe.close()
        except OSError:
            pass

    os.chdir(DIST)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print("[serve] http://127.0.0.1:%d  (Ctrl+C 结束)" % port)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] 已停止")
    return 0


if __name__ == "__main__":
    use_utf8_console()
    args = sys.argv[1:]
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            print("[build] --out 需要一个目录参数")
            sys.exit(2)
        DIST = os.path.abspath(args[i + 1])
    if "--check" in args:
        sys.exit(build(write=False))
    rc = build(write=True)
    if "--serve" in args:
        rc = serve() or rc
    sys.exit(rc)
