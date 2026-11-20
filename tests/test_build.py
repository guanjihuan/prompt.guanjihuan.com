# -*- coding: utf-8 -*-
"""构建器回归测试；所有读写均限制在临时目录。"""

import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build as site_build  # noqa: E402

site_build.use_utf8_console()  # 避免中文测试名在部分终端里显示成乱码


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.src = root / "src"
        self.prompts = self.src / "prompts"
        self.assets = self.src / "assets"
        self.dist = root / "dist"
        self.prompts.mkdir(parents=True)
        self.assets.mkdir()
        (self.assets / "app.js").write_text("console.log('ok');\n", encoding="utf-8")
        (self.assets / "style.css").write_text("body{}\n", encoding="utf-8")
        self.write_template()
        self.originals = {
            name: getattr(site_build, name)
            for name in ("SRC", "PROMPT_DIR", "ASSET_DIR", "DIST")
        }
        site_build.SRC = str(self.src)
        site_build.PROMPT_DIR = str(self.prompts)
        site_build.ASSET_DIR = str(self.assets)
        site_build.DIST = str(self.dist)

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(site_build, name, value)
        self.temp.cleanup()

    def write_template(self, marker=True):
        payload = "/*__PROMPT_DATA__*/" if marker else ""
        (self.src / "index.html").write_text(
            '<!doctype html><html><head><link rel="stylesheet" href="assets/style.css">'
            '</head><body><script id="prompt-data" type="application/json">'
            + payload
            + '</script><script src="assets/app.js"></script></body></html>',
            encoding="utf-8",
        )

    def write_category(self, filename, cat_id, name, icon, items, order=1, section="测试"):
        lines = [
            "---",
            "id: " + cat_id,
            "name: " + name,
            'icon: "' + icon + '"',
            "desc: 测试分类",
            "section: " + section,
            "order: " + str(order),
            "---",
            "",
        ]
        for item in items:
            lines.extend(["## " + item["title"]])
            if item.get("id"):
                lines.append("<!-- id: %s -->" % item["id"])
            lines.extend(["<!-- t: 测试 -->"])
            if item.get("short") is not None:
                lines.append("<!-- s: %s -->" % item["short"])
            lines.extend([
                item.get("content", "用于测试的完整提示词正文。"),
                "",
            ])
        (self.prompts / filename).write_text("\n".join(lines), encoding="utf-8")

    def collect(self):
        errors = []
        categories, sections = site_build.collect(errors)
        self.assertEqual([], errors)
        return categories, sections

    def test_explicit_ids_survive_rename_move_and_insert(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "原始标题"},
            {"id": "p002", "title": "待移动条目"},
        ])
        first, _ = self.collect()
        self.assertEqual(["p001", "p002"], [p["id"] for p in first[0]["prompts"]])

        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "new-task", "title": "新增条目"},
            {"id": "p001", "title": "修改后标题"},
        ])
        self.write_category("02-b.md", "b", "乙", "B", [
            {"id": "p002", "title": "移动并改名"},
        ], order=2)
        categories, _ = self.collect()
        by_id = {p["id"]: p for c in categories for p in c["prompts"]}
        self.assertEqual("修改后标题", by_id["p001"]["title"])
        self.assertEqual("移动并改名", by_id["p002"]["title"])
        generated = next(p["id"] for c in categories for p in c["prompts"] if p["title"] == "新增条目")
        self.assertEqual("new-task", generated)

    def test_missing_id_is_rejected(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"title": "没有标识"}])
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("缺少稳定 id" in error for error in errors))

    def test_duplicate_id_does_not_replace_previous_build(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "same", "title": "条目甲"}])
        self.write_category("02-b.md", "b", "乙", "B", [{"id": "same", "title": "条目乙"}], order=2)
        self.dist.mkdir()
        sentinel = self.dist / "index.html"
        sentinel.write_text("上一份可用构建", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            result = site_build.build(write=True)
        self.assertEqual(1, result)
        self.assertEqual("上一份可用构建", sentinel.read_text(encoding="utf-8"))

    def test_invalid_template_does_not_replace_previous_build(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "条目甲"}])
        self.write_template(marker=False)
        self.dist.mkdir()
        sentinel = self.dist / "index.html"
        sentinel.write_text("保留", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            result = site_build.build(write=True)
        self.assertEqual(1, result)
        self.assertEqual("保留", sentinel.read_text(encoding="utf-8"))

    def test_embedded_script_text_round_trips_safely(self):
        hostile = "保留 </script><script>window.bad=true</script> 这段普通文本"
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "安全注入", "content": hostile},
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        html = (self.dist / "index.html").read_text(encoding="utf-8")
        self.assertNotIn(hostile, html)
        match = re.search(
            r'<script id="prompt-data" type="application/json">(.*?)</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        data = json.loads(match.group(1))
        self.assertEqual(hostile, data["categories"][0]["prompts"][0]["content"])

    def test_payload_is_compact_single_line_json(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "条目甲", "content": "第一行\n第二行"},
        ])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        html = (self.dist / "index.html").read_text(encoding="utf-8")
        match = re.search(
            r'<script id="prompt-data" type="application/json">(.*?)</script>',
            html, re.S,
        )
        payload = match.group(1)
        self.assertNotIn("\n", payload)          # 紧凑格式：整份数据不换行
        self.assertIn('"title":"条目甲"', payload)  # 紧凑分隔符
        self.assertEqual("第一行\n第二行", json.loads(payload)["categories"][0]["prompts"][0]["content"])

    def write_translations(self, filename, payload):
        """在临时目录里放一份英文译文（src/i18n/en/ 下与分类同名的 JSON）。"""
        en_dir = self.src / "i18n" / "en"
        en_dir.mkdir(parents=True, exist_ok=True)
        (en_dir / filename).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def write_section_translations(self, mapping):
        """分区名译文放在 src/i18n/sections.json（与分类译文分开）。"""
        path = self.src / "i18n" / "sections.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")

    def read_payload(self):
        html = (self.dist / "index.html").read_text(encoding="utf-8")
        match = re.search(
            r'<script id="prompt-data" type="application/json">(.*?)</script>',
            html, re.S,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_english_translations_are_merged_into_payload(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "条目甲", "short": "简短甲"},
        ])
        self.write_translations("01-a.json", {
            "category": {"name": "Category A", "desc": "English desc"},
            "prompts": {"p001": {"title": "Item A", "tags": ["Test"],
                                 "short": "Short A", "content": "English body"}},
        })
        self.write_section_translations({"测试": "Test section"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        data = self.read_payload()
        en = data["en"]
        self.assertEqual("Item A", en["prompts"]["p001"]["title"])
        self.assertEqual("English body", en["prompts"]["p001"]["content"])
        self.assertEqual("Category A", en["categories"]["a"]["name"])
        self.assertEqual("Test section", en["sections"]["测试"])

    def test_missing_english_translation_blocks_build(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "条目甲", "short": "简短甲"},
            {"id": "p002", "title": "条目乙", "short": "简短乙"},
        ])
        self.write_translations("01-a.json", {
            "category": {"name": "Category A", "desc": "English desc"},
            "prompts": {"p002": {"title": "Item B", "tags": ["Test"],
                                 "short": "Short B", "content": "English body"}},
        })
        self.write_section_translations({"测试": "Test section"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, site_build.build(write=True))

    def test_english_translation_for_unknown_id_is_rejected(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "条目甲", "short": "简短甲"},
        ])
        self.write_translations("01-a.json", {
            "category": {"name": "Category A", "desc": "English desc"},
            "prompts": {
                "p001": {"title": "Item A", "tags": ["Test"],
                         "short": "Short A", "content": "English body"},
                "p404": {"title": "Ghost", "tags": ["Test"],
                         "short": "Ghost", "content": "Ghost body"},
            },
        })
        self.write_section_translations({"测试": "Test section"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, site_build.build(write=True))

    def test_english_translation_file_set_must_match_categories(self):
        """多一份没有对应分类的译文文件要被拦下。"""
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "条目甲", "short": "简短甲"},
        ])
        self.write_translations("01-a.json", {
            "category": {"name": "Category A", "desc": "English desc"},
            "prompts": {"p001": {"title": "Item A", "tags": ["Test"],
                                 "short": "Short A", "content": "English body"}},
        })
        self.write_translations("99-extra.json", {"category": {}, "prompts": {}})
        self.write_section_translations({"测试": "Test section"})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, site_build.build(write=True))

    def test_headings_inside_fences_do_not_split_items(self):
        path = self.prompts / "01-a.md"
        path.write_text(
            "---\nid: a\nname: 甲\nicon: A\ndesc: 测试\nsection: 测试\norder: 1\n---\n"
            "## 代码块\n<!-- id: p001 -->\n<!-- t: 测试 -->\n"
            "```markdown\n## 这不是新条目\n```\n正文。\n",
            encoding="utf-8",
        )
        categories, _ = self.collect()
        self.assertEqual(1, len(categories[0]["prompts"]))
        self.assertIn("## 这不是新条目", categories[0]["prompts"][0]["content"])

    def test_short_variant_must_be_shorter_than_body(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "简洁版反而更长", "short": "这是一段比正文还要长的简洁表达。",
             "content": "短正文。"},
        ])
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("简洁表达不短于正文" in error for error in errors))

    def test_short_equal_to_body_is_dropped_without_error(self):
        self.write_category("01-a.md", "a", "甲", "A", [
            {"id": "p001", "title": "两种说法一致", "short": "完全一样的一段提示词。",
             "content": "完全一样的一段提示词。"},
        ])
        categories, _ = self.collect()
        self.assertEqual("", categories[0]["prompts"][0]["short"])

    def test_unknown_frontmatter_field_is_rejected(self):
        path = self.prompts / "01-a.md"
        path.write_text(
            "---\nid: a\nname: 甲\nicon: A\ndesc: 测试\nsection: 测试\norder: 1\ncolour: 蓝\n---\n"
            "## 条目\n<!-- id: p001 -->\n<!-- t: 测试 -->\n正文。\n",
            encoding="utf-8",
        )
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("未知的前置字段" in error for error in errors))

    def test_duplicate_title_across_categories_is_rejected(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "同一个标题"}])
        self.write_category("02-b.md", "b", "乙", "B", [{"id": "p002", "title": "同一个标题"}], order=2)
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("标题与" in error and "重复" in error for error in errors))

    def test_duplicate_icon_is_rejected(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "甲条目"}])
        self.write_category("02-b.md", "b", "乙", "A", [{"id": "p002", "title": "乙条目"}], order=2)
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("图标" in error and "重复" in error for error in errors))

    def test_reserved_sidebar_icon_is_rejected(self):
        self.write_category("01-a.md", "a", "甲", "★", [{"id": "p001", "title": "甲条目"}])
        errors = []
        site_build.collect(errors)
        self.assertTrue(any("侧栏固定图标" in error for error in errors))

    def test_confusable_icons_are_warned(self):
        self.write_category("01-a.md", "a", "甲", "⊙", [{"id": "p001", "title": "甲条目"}])
        self.write_category("02-b.md", "b", "乙", "◎", [{"id": "p002", "title": "乙条目"}], order=2)
        errors, warnings = [], []
        site_build.collect(errors, warnings)
        self.assertFalse(errors)
        self.assertTrue(any("外形相近" in w for w in warnings))

    def test_asset_version_hash_is_injected(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "条目甲"}])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        html = (self.dist / "index.html").read_text(encoding="utf-8")
        blob = (self.dist / "assets" / "app.js").read_bytes()
        version = hashlib.sha1(blob).hexdigest()[:8]
        self.assertIn('assets/app.js?v=%s"' % version, html)
        self.assertIn('assets/style.css?v=', html)

    def test_robots_and_sitemap_are_generated(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "条目甲"}])
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        robots = (self.dist / "robots.txt").read_text(encoding="utf-8")
        self.assertIn("Sitemap: https://prompt.guanjihuan.com/sitemap.xml", robots)
        sitemap = (self.dist / "sitemap.xml").read_text(encoding="utf-8")
        self.assertIn("<loc>https://prompt.guanjihuan.com/</loc>", sitemap)

    def test_sections_group_categories_in_order(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "甲条目"}],
                            order=1, section="第一分区")
        self.write_category("02-b.md", "b", "乙", "B", [{"id": "p002", "title": "乙条目"}],
                            order=2, section="第二分区")
        categories, sections = self.collect()
        self.assertEqual(["第一分区", "第二分区"], [s["name"] for s in sections])
        self.assertEqual([["a"], ["b"]], [s["categories"] for s in sections])

    def test_not_found_page_is_copied_to_dist(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "条目甲"}])
        (self.src / "404.html").write_text(
            '<!doctype html><html><body><h1>404</h1><a href="/">回到首页</a></body></html>',
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        page = self.dist / "404.html"
        self.assertTrue(page.exists())
        self.assertIn("回到首页", page.read_text(encoding="utf-8"))

    def test_binary_assets_are_copied_and_preview_image_is_refreshed(self):
        self.write_category("01-a.md", "a", "甲", "A", [{"id": "p001", "title": "条目甲"}])
        (self.assets / "og.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, site_build.build(write=True))
        copied = self.dist / "assets" / "og.png"
        self.assertTrue(copied.exists())
        self.assertTrue(copied.read_bytes().startswith(b"\x89PNG"))

    def test_out_option_writes_to_the_given_directory(self):
        target = Path(self.temp.name) / "preview"
        result = subprocess.run(
            [sys.executable, str(ROOT / "build.py"), "--out", str(target)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue((target / "index.html").exists())
        self.assertTrue((target / "assets" / "app.js").exists())


class StaticSiteTests(unittest.TestCase):
    """静态资源的自洽性检查：改页面时最容易悄悄坏掉的几处。"""

    def read(self, *parts):
        return (ROOT.joinpath(*parts)).read_text(encoding="utf-8")

    def inline_scripts(self, html):
        return [m.group(1) for m in re.finditer(
            r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)]

    def theme_script_hash(self, html):
        """主题引导脚本的 sha256（base64），与 Nginx 里的 CSP 哈希是同一个值。"""
        scripts = [s for s in self.inline_scripts(html) if "plib.theme.v1" in s]
        self.assertEqual(1, len(scripts), "每个页面都应有且只有一段主题引导脚本")
        return base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()

    def test_theme_script_hash_matches_nginx_csp(self):
        """改了主题引导脚本就要同步 nginx.conf 里的 CSP 哈希，否则主题会被拦掉。"""
        digest = self.theme_script_hash(self.read("src", "index.html"))
        # 404 页也带同一段脚本，两页共用一个哈希；不一致就会有一页被 CSP 拦下
        self.assertEqual(digest, self.theme_script_hash(self.read("src", "404.html")))
        self.assertIn(digest, self.read("deploy", "nginx.conf"))

    def test_not_found_page_links_and_assets_exist(self):
        page = self.read("src", "404.html")
        self.assertIn('href="/"', page)
        self.assertIn('name="robots" content="noindex"', page)
        for ref in re.findall(r'(?:src|href)="(assets/[^"]+)"', page):
            self.assertTrue(ROOT.joinpath("src", ref).exists(), "404 页引用了不存在的资源：%s" % ref)

    def test_copied_assets_use_lf_line_endings(self):
        """静态资源是逐字节拷进 dist 的：工作区里混进 CRLF，Windows 构建出的
        资源哈希就和 Linux 检出后重建的产物对不上，CI 的产物同步检查会红。
        仓库有 .gitattributes（eol=lf）兜住入库，但编辑器另存成 CRLF 时
        工作区还是会脏——这里直接守住源文件本身。"""
        for name in ("app.js", "style.css"):
            blob = ROOT.joinpath("src", "assets", name).read_bytes()
            self.assertNotIn(b"\r\n", blob, "src/assets/%s 里混进了 CRLF，请另存为 LF" % name)


class DocumentationNumberTests(unittest.TestCase):
    """README 与体例文档里的统计数字要和库里的实际内容一致。

    规模数字是手写的，条目一增一删就容易对不上——这里直接按
    src/prompts/ 的实际内容核对，省得每次都靠人记着改。
    """

    def setUp(self):
        self.readme = ROOT.joinpath("README.md").read_text(encoding="utf-8")
        errors = []
        categories, sections = site_build.collect(errors)
        self.assertEqual([], errors)
        self.total = sum(len(c["prompts"]) for c in categories)
        self.cats = len(categories)
        self.by_section = {}
        for c in categories:
            self.by_section.setdefault(c["section"], 0)
            self.by_section[c["section"]] += len(c["prompts"])

    def test_headline_total_matches_library(self):
        m = re.search(r"这里收录了 (\d+) 条", self.readme)
        self.assertIsNotNone(m, "README 里找不到条目总数")
        self.assertEqual(self.total, int(m.group(1)),
                         "README 写的条目数（%s）与库里的实际条数（%d）对不上"
                         % (m.group(1), self.total))

    def test_category_count_matches_library(self):
        m = re.search(r"(\d+) 个分类覆盖", self.readme)
        self.assertIsNotNone(m, "README 里找不到分类数")
        self.assertEqual(self.cats, int(m.group(1)),
                         "README 写的分类数（%s）与实际（%d）对不上" % (m.group(1), self.cats))

    def test_short_variant_stats_match_philosophy_document(self):
        """体例文档里的简洁表达统计也要随内容一起更新。"""
        text = ROOT.joinpath("docs", "philosophy.md").read_text(encoding="utf-8")
        match = re.search(r"当前全库 (\d+) 条都带简洁表达，实测 (\d+)~(\d+) 字、中位数 (\d+) 字", text)
        self.assertIsNotNone(match, "体例文档里找不到简洁表达统计")
        lengths = sorted(len(p["short"]) for c in site_build.collect([])[0]
                         for p in c["prompts"] if p["short"])
        actual = (len(lengths), lengths[0], lengths[-1], statistics.median(lengths))
        self.assertEqual(actual, tuple(int(value) for value in match.groups()))

    def test_section_table_counts_match_library(self):
        """分区表里的「条数」列逐行核对。"""
        rows = re.findall(r"^\| (\S+) \| (\d+) \| .+ \|$", self.readme, re.M)
        self.assertTrue(rows, "README 里找不到分区表")
        self.assertEqual(len(self.by_section), len(rows),
                         "分区表有 %d 行，实际有 %d 个分区" % (len(rows), len(self.by_section)))
        for name, n in rows:
            self.assertIn(name, self.by_section, "分区表里的「%s」已不是库里的分区" % name)
            self.assertEqual(self.by_section[name], int(n),
                             "分区「%s」在 README 里写 %s 条，实际 %d 条"
                             % (name, n, self.by_section[name]))


if __name__ == "__main__":
    unittest.main()
