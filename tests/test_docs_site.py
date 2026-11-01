from __future__ import annotations

import re
import sys
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SITE = REPO_ROOT / "site"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_site  # noqa: E402
from app import mcp_tools, rfp_connector  # noqa: E402


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
        if href.startswith("#") and len(href) > 1:
            self.fragments.add(href[1:])
        for attr in ("aria-controls", "aria-labelledby"):
            if values.get(attr):
                self.fragments.add(values[attr])


class DocsSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = (SITE / "index.html").read_text(encoding="utf-8")
        cls.assets = "\n".join(
            p.read_text(encoding="utf-8") for p in (SITE / "assets").iterdir()
        )

    def test_generated_reference_is_current(self) -> None:
        self.assertEqual(
            build_site.render_page(self.page),
            self.page,
            "site/index.html is stale. Run: python scripts/build_site.py",
        )

    def test_every_registered_tool_is_documented_and_grouped(self) -> None:
        for name in mcp_tools.MCP_TOOLS:
            self.assertIn(f'id="tool-{name}"', self.page)
        groups = [key for key, _, _ in build_site.grouped_tools()]
        self.assertNotIn("unsorted", groups, "place new tools in build_site.TOOL_GROUPS")

    def test_every_request_type_is_explained(self) -> None:
        for key in rfp_connector.ALLOWED_CONTRIBUTOR_REQUEST_TYPES:
            self.assertIn(key, build_site.REQUEST_TYPE_DETAILS)
            self.assertIn(f'id="request-{key}"', self.page)

    def test_states_that_a_request_is_not_a_grant(self) -> None:
        self.assertIn("A request is not a grant.", self.page)
        self.assertIn("explicit approval", self.page)

    def test_connector_only_entries_never_appear(self) -> None:
        text = (self.page + self.assets).lower()
        for rfp in rfp_connector.CONNECTOR_ONLY_PRIVATE_RFPS.values():
            self.assertNotIn(rfp["rfp_id"].lower(), text)
            self.assertNotIn(rfp["title"].lower(), text)

    def test_no_private_knowledge_references(self) -> None:
        text = (self.page + self.assets).lower()
        for marker in ("knowledgehq", "company brain", "hotmem"):
            self.assertNotIn(marker, text)

    def test_idea_catalogue_is_linked_not_copied(self) -> None:
        self.assertIn(
            "github.com/knowb-ai/cloud-builder-stack/blob/main/docs/fun-project-and-hackathon-ideas.md",
            self.page,
        )

    def test_internal_fragments_resolve(self) -> None:
        parser = _IdAndLinkParser()
        parser.feed(self.page)
        missing = sorted(parser.fragments - parser.ids)
        self.assertEqual(missing, [], f"links to missing ids: {missing}")

    def test_no_em_dashes(self) -> None:
        for path in [SITE / "index.html", *sorted((SITE / "assets").iterdir())]:
            self.assertNotIn("—", path.read_text(encoding="utf-8"), str(path))

    def test_custom_domain_is_recorded(self) -> None:
        self.assertEqual((SITE / "CNAME").read_text(encoding="utf-8").strip(), "hack.knowb.run")
        self.assertTrue((SITE / ".nojekyll").exists())

    def test_assets_are_local_except_fonts(self) -> None:
        external = re.findall(r'(?:src|href)="(https?://[^"]+)"', self.page)
        scripts_and_styles = [
            url for url in external
            if url.endswith((".js", ".css")) or "fonts.googleapis.com/css" in url
        ]
        for url in scripts_and_styles:
            self.assertTrue(url.startswith("https://fonts.googleapis.com/"), url)


if __name__ == "__main__":
    unittest.main()
