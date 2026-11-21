"""Integration checks for redirect handling in the normal site build."""
import json, pathlib, re, shutil, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def render(pages, redirects):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "data").mkdir()
        for name in ("build_site.py", "wiki_redirects.py"):
            shutil.copy(ROOT / name, root / name)
        data = {"pages": pages, "sections": {}, "count": len(pages)}
        (root / "data/wiki_data.json").write_text(json.dumps(data), encoding="utf-8")
        (root / "data/redirects.json").write_text(json.dumps(redirects), encoding="utf-8")
        subprocess.run([sys.executable, "build_site.py"], cwd=root, check=True,
                       capture_output=True)
        html = (root / "index.html").read_text(encoding="utf-8")
    payload = json.loads(re.search(
        r'<script type="application/json" id="data">(.*?)</script>', html, re.S
    ).group(1))
    return payload, html


class RedirectBuildTest(unittest.TestCase):
    def test_future_data_rebuild_uses_available_legacy_target(self):
        from build_data import rewrite_html
        link = '<a href="https://wiki.walkscape.app/wiki/Bar_Keyword">Bar</a>'
        self.assertIn('href="#/Bar_%28Keyword%29"',
                      rewrite_html(link, {"Bar_(Keyword)"}))
        self.assertIn('href="#/Bar_Keyword"',
                      rewrite_html(link, {"Bar_Keyword", "Bar_(Keyword)"}))
        self.assertIn('href="https://wiki.walkscape.app/wiki/Bar_Keyword"',
                      rewrite_html(link, set()))
        anchored = '<a href="https://wiki.walkscape.app/wiki/Bar_Keyword#Uses_Table">Uses</a>'
        self.assertIn('href="#/Bar_%28Keyword%29#Uses_Table"',
                      rewrite_html(anchored, {"Bar_(Keyword)"}))

    def test_missing_legacy_and_upstream_titles(self):
        pages = {
            "Item_Finding": {"html": '<a href="https://wiki.walkscape.app/wiki/Item_Finding_Items">items</a>'},
            "That's_A_Wrap": {"html": '<a href="https://wiki.walkscape.app/wiki/Item_Finding_Items#Linens">Linens</a>'},
            "Roll_Special_Table_Items": {"html": '<h2>Linens</h2>'},
            "Advanced_diving_gear_(Keyword)": {"html": ""},
        }
        data, html = render(pages, {"Advanced_diving_gear_Keyword": "Advanced_diving_gear_(Keyword)"})
        self.assertEqual(data["redirects"]["Item_Finding_Items"], "Roll_Special_Table_Items")
        self.assertEqual(data["redirects"]["Advanced_diving_gear_Keyword"], "Advanced_diving_gear_(Keyword)")
        self.assertIn('href="#/Roll_Special_Table_Items"', data["pages"]["Item_Finding"]["html"])
        self.assertIn('href="#/Roll_Special_Table_Items#Linens"', data["pages"]["That's_A_Wrap"]["html"])
        self.assertIn("if (REDIRECTS[slug])", html)
        self.assertIn("slugify(decodeURIComponent(id).replace(/_/g, ' '))", html)

    def test_old_article_wins_and_missing_destination_stays_external(self):
        pages = {
            "Bar_Keyword": {"html": '<a href="https://wiki.walkscape.app/wiki/Bar_Keyword">Bar</a>'},
            "Other": {"html": '<a href="https://wiki.walkscape.app/wiki/Weapon_Keyword">Weapon</a>'},
        }
        data, _ = render(pages, {})
        self.assertNotIn("Bar_Keyword", data["redirects"])
        self.assertNotIn("Weapon_Keyword", data["redirects"])
        self.assertIn('href="https://wiki.walkscape.app/wiki/Bar_Keyword"', data["pages"]["Bar_Keyword"]["html"])
        self.assertIn('href="https://wiki.walkscape.app/wiki/Weapon_Keyword"', data["pages"]["Other"]["html"])


if __name__ == "__main__":
    unittest.main()
