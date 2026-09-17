"""_md.config() -- the [tool.*] reader the checkers get their project data from.

Five modules now take their book-specific constants from pyproject.toml rather
than carrying them. The failure mode that matters is silent: a missing file or a
renamed section returns {}, every caller falls back to its general default, and
the checkers go quietly permissive instead of failing loudly. These pin the
fallback down so it stays a deliberate choice.
"""

import tempfile
import unittest
from pathlib import Path


from linji_tools import _md

TOML = """\
[tool.book]
exclude = ["README.md"]

[tool.book.titles]
"b.md" = "ب"
"a.md" = "الف"

[tool.other]
n = 1
"""


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "pyproject.toml"
        self.path.write_text(TOML, encoding="utf-8")

    def test_reads_the_named_section(self):
        self.assertEqual(_md.config("other", self.path), {"n": 1})

    def test_nested_tables_come_through(self):
        book = _md.config("book", self.path)
        self.assertEqual(book["exclude"], ["README.md"])
        self.assertEqual(book["titles"]["a.md"], "الف")

    def test_declaration_order_is_preserved(self):
        # A checker that renders configured labels in order would silently
        # reorder its output if the loader handed back an unordered dict.
        self.assertEqual(list(_md.config("book", self.path)["titles"]), ["b.md", "a.md"])

    def test_an_absent_section_is_empty_not_an_error(self):
        self.assertEqual(_md.config("nosuch", self.path), {})

    def test_an_absent_file_is_empty_not_an_error(self):
        self.assertEqual(_md.config("book", self.path.parent / "gone.toml"), {})


if __name__ == "__main__":
    unittest.main()
