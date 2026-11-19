import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from io import StringIO
import json
import xml.etree.ElementTree as ET

from scripts import update_repositories as generator


def repo(name, stars=1, **fields):
    return dict(name=name, stargazers_count=stars, owner={"login": "Frish07"},
                **fields)


class RepositoryCardsTests(unittest.TestCase):
    def test_ranking_and_filters(self):
        repos = [repo("Z", 2), repo("a", 2), repo("winner", 8),
                 repo("fork", 90, fork=True), repo("Frish07", 100),
                 repo("secret", 100, private=True)]
        self.assertEqual([r["name"] for r in generator.top_repositories(repos)],
                         ["winner", "a", "Z"])
        self.assertEqual(len(generator.top_repositories([repo(str(i)) for i in range(10)])), 6)

    def test_pagination(self):
        pages = [StringIO(json.dumps([repo(str(i)) for i in range(100)])),
                 StringIO(json.dumps([repo("last")]))]
        with patch.object(generator, "urlopen", side_effect=pages) as request:
            self.assertEqual(len(generator.fetch_repositories()), 101)
            self.assertIn("page=2", request.call_args.args[0].full_url)

    def test_svg_escapes_metadata(self):
        for theme in ("dark", "light"):
            svg = generator.card_svg(repo('a&b', description='<script> & "test"', language="C++"), theme)
            ET.fromstring(svg)
            self.assertIn("&lt;script&gt;", svg)
            self.assertNotIn("<script>", svg)

    def test_updates_preserve_profile_and_remove_old_cards(self):
        with tempfile.TemporaryDirectory(prefix=".test-cards-", dir=generator.ROOT) as directory:
            root = Path(directory)
            path = root / "README.md"
            path.write_text(f"Intro\n{generator.START}\nold\n{generator.END}\nFooter", encoding="utf-8")
            generator.update(root, [repo("one")])
            first = path.read_bytes()
            generator.update(root, [repo("one")])
            self.assertEqual(first, path.read_bytes())
            generator.update(root, [repo("two", 5)])
            self.assertEqual(len(list((root / "assets/repositories").glob("*.svg"))), 2)
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("Intro\n"))
            self.assertTrue(text.endswith("\nFooter"))
            self.assertIn("Frish07/two", text)


if __name__ == "__main__":
    unittest.main()
