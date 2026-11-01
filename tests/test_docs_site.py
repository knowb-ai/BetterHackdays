from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_site  # noqa: E402
from app import mcp_tools, rfp_connector  # noqa: E402


def _site_sources() -> list[Path]:
    return [
        p for p in SITE.rglob("*")
        if p.is_file() and "public" not in p.relative_to(SITE).parts and p.suffix != ".svg"
    ]


class _IdAndLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.fragments: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        href = values.get("href") or ""
        if "#" in href and (href.startswith("#") or href.startswith("/#") or "hack.knowb.run/#" in href):
            fragment = href.split("#", 1)[1]
            if fragment:
                self.fragments.add(fragment)
        for attr in ("aria-controls", "aria-labelledby"):
            if values.get(attr):
                self.fragments.add(values[attr])


class DocsSiteSourceTest(unittest.TestCase):
    """Checks that need only the repository."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.reference = json.loads((SITE / "data" / "reference.json").read_text(encoding="utf-8"))
        cls.sources = {p: p.read_text(encoding="utf-8") for p in _site_sources()}
        cls.text = "\n".join(cls.sources.values())

    def test_generated_reference_is_current(self) -> None:
        self.assertEqual(
            build_site.render_reference(),
            (SITE / "data" / "reference.json").read_text(encoding="utf-8"),
            "site/data/reference.json is stale. Run: python scripts/build_site.py",
        )

    def test_every_registered_tool_is_documented_and_grouped(self) -> None:
        documented = {t["name"] for g in self.reference["tool_groups"] for t in g["tools"]}
        self.assertEqual(documented, set(mcp_tools.MCP_TOOLS))
        groups = [g["key"] for g in self.reference["tool_groups"]]
        self.assertNotIn("unsorted", groups, "place new tools in build_site.TOOL_GROUPS")

    def test_every_request_type_is_explained(self) -> None:
        for key in rfp_connector.ALLOWED_CONTRIBUTOR_REQUEST_TYPES:
            self.assertIn(key, build_site.REQUEST_TYPE_DETAILS)
        self.assertEqual(
            [r["key"] for r in self.reference["request_types"]],
            list(rfp_connector.ALLOWED_CONTRIBUTOR_REQUEST_TYPES),
        )

    def test_states_that_a_request_is_not_a_grant(self) -> None:
        requests = (SITE / "content" / "manual" / "requests.md").read_text(encoding="utf-8")
        self.assertIn('alert(title="A request is not a grant.")', requests)
        self.assertIn("explicit approval", requests)

    def test_connector_only_entries_never_appear(self) -> None:
        text = self.text.lower()
        for rfp in rfp_connector.CONNECTOR_ONLY_PRIVATE_RFPS.values():
            self.assertNotIn(rfp["rfp_id"].lower(), text)
            self.assertNotIn(rfp["title"].lower(), text)

    def test_no_private_knowledge_references(self) -> None:
        text = self.text.lower()
        for marker in ("knowledgehq", "company brain", "hotmem"):
            self.assertNotIn(marker, text)

    def test_idea_catalogue_is_linked_not_copied(self) -> None:
        self.assertIn(
            "github.com/knowb-ai/cloud-builder-stack/blob/main/docs/fun-project-and-hackathon-ideas.md",
            self.text,
        )

    def test_brand_is_knowb_run(self) -> None:
        base = (SITE / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn('knowb<span class="dot">.</span>run</a>', base)
        self.assertIn("{{ config.title }}: knowb.run", base)
        self.assertNotIn('hack<span class="dot">', base)

    def test_no_em_dashes(self) -> None:
        for path, text in self.sources.items():
            self.assertNotIn("—", text, str(path))

    def test_custom_domain_is_recorded(self) -> None:
        self.assertEqual((SITE / "static" / "CNAME").read_text(encoding="utf-8").strip(), "hack.knowb.run")
        self.assertIn('base_url = "https://hack.knowb.run"', (SITE / "config.toml").read_text(encoding="utf-8"))


@unittest.skipUnless(shutil.which("zola"), "zola is not installed")
class DocsSiteBuildTest(unittest.TestCase):
    """Checks against the built site. They run wherever Zola is installed,
    including the Pages workflow."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "public"
        subprocess.run(
            ["zola", "--root", str(SITE), "build", "--output-dir", str(out)],
            check=True, capture_output=True, text=True,
        )
        cls.out = out
        cls.page = (out / "index.html").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_all_sections_and_references_render(self) -> None:
        sections = sorted(p.stem for p in (SITE / "content" / "manual").glob("[a-z]*.md"))
        for slug in sections:
            self.assertIn(f'<section class="doc" id="{slug}"', self.page)
            self.assertTrue((self.out / "manual" / slug / "index.html").exists())
        for name in mcp_tools.MCP_TOOLS:
            self.assertIn(f'id="tool-{name}"', self.page)
        self.assertIn("A request is not a grant.", self.page)

    def test_no_unrendered_template_syntax(self) -> None:
        for marker in ("{{", "{%", "<p><div", "<p><li>", "</div></p>"):
            self.assertNotIn(marker, self.page)

    def test_internal_fragments_resolve(self) -> None:
        parser = _IdAndLinkParser()
        parser.feed(self.page)
        missing = sorted(parser.fragments - parser.ids)
        self.assertEqual(missing, [], f"links to missing ids: {missing}")

    def test_section_urls_forward_to_their_anchor(self) -> None:
        faq = (self.out / "manual" / "faq" / "index.html").read_text(encoding="utf-8")
        self.assertRegex(faq, r'http-equiv="refresh" content="0; url=[^"]*#faq"')

    def test_custom_domain_ships_with_the_build(self) -> None:
        self.assertEqual((self.out / "CNAME").read_text(encoding="utf-8").strip(), "hack.knowb.run")

    def test_connector_only_entries_never_render(self) -> None:
        text = self.page.lower()
        for rfp in rfp_connector.CONNECTOR_ONLY_PRIVATE_RFPS.values():
            self.assertNotIn(rfp["title"].lower(), text)

    def test_only_fonts_load_from_elsewhere(self) -> None:
        external = re.findall(r'<(?:script|link)[^>]+(?:src|href)="(https?://[^"]+)"', self.page)
        for url in external:
            if "hack.knowb.run" in url or "127.0.0.1" in url:
                continue
            self.assertTrue(url.startswith("https://fonts.g"), url)


if __name__ == "__main__":
    unittest.main()
