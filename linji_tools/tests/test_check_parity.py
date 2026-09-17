import tempfile
import unittest
from pathlib import Path


from linji_tools.check_parity import compare, is_skipped, main, parse_offset

TRANSLATED = "---\nstatus: translated\n---\n\n"


class Tree:
    """A throwaway source/ + fa/ pair."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        self.source = self.root / "source"
        self.fa = self.root / "fa"
        self.source.mkdir()
        self.fa.mkdir()

    def add(self, name, source_body, fa_body):
        (self.source / name).write_text(source_body, encoding="utf-8")
        (self.fa / name).write_text(fa_body, encoding="utf-8")

    def run(self, exclude=frozenset()):
        return compare(self.source, self.fa, exclude)


class TestOffsetDirective(unittest.TestCase):
    def test_reads_negative_offset(self):
        self.assertEqual(parse_offset("<!-- parity: offset -1 -->"), -1)

    def test_reads_positive_offset(self):
        self.assertEqual(parse_offset("<!-- parity: offset +2 -->"), 2)

    def test_absent_offset_is_zero(self):
        self.assertEqual(parse_offset("متن"), 0)

    def test_malformed_offset_raises(self):
        with self.assertRaises(ValueError):
            parse_offset("<!-- parity: offset banana -->")

    def test_skip_is_detected(self):
        self.assertTrue(is_skipped("<!-- parity: skip -->"))
        self.assertFalse(is_skipped("متن"))


class TestComparison(unittest.TestCase):
    def test_equal_block_counts_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add("01.md", "# A\n\npara\n", TRANSLATED + "# الف\n\nبند\n")
            findings, compared, skipped = tree.run()
            self.assertEqual(findings, [])
            self.assertEqual((compared, skipped), (1, 0))

    def test_dropped_paragraph_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add("01.md", "# A\n\none\n\ntwo\n", TRANSLATED + "# الف\n\nیک\n")
            findings, _, _ = tree.run()
            self.assertEqual(len(findings), 1)
            self.assertIn("2 blocks, source has 3", str(findings[0]))

    def test_untranslated_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add("01.md", "# A\n\none\n\ntwo\n", "---\nstatus: untranslated\n---\n\n# الف\n")
            findings, compared, skipped = tree.run()
            self.assertEqual(findings, [])
            self.assertEqual((compared, skipped), (0, 1))

    def test_skip_directive_exempts_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add("01.md", "# A\n\none\n\ntwo\n", TRANSLATED + "<!-- parity: skip -->\n\n# الف\n")
            findings, compared, skipped = tree.run()
            self.assertEqual(findings, [])
            self.assertEqual((compared, skipped), (0, 1))

    def test_declared_offset_is_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            # source has a part heading the translation moves into _quarto.yml
            tree.add(
                "01.md",
                "## Part One\n\n### 1\n\npara\n",
                TRANSLATED + "<!-- parity: offset -1 -->\n\n# ۱\n\nبند\n",
            )
            findings, compared, _ = tree.run()
            self.assertEqual(findings, [])
            self.assertEqual(compared, 1)

    def test_wrong_offset_is_reported_with_both_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add(
                "01.md",
                "## Part One\n\n### 1\n\none\n\ntwo\n",
                TRANSLATED + "<!-- parity: offset -1 -->\n\n# ۱\n",
            )
            findings, _, _ = tree.run()
            self.assertIn("offset -1 declared, actual -3", str(findings[0]))

    def test_fenced_code_counts_as_one_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            tree.add("01.md", "```\na\n\nb\n```\n", TRANSLATED + "```\na\n\nb\n```\n")
            findings, _, _ = tree.run()
            self.assertEqual(findings, [])


class TestPairing(unittest.TestCase):
    def test_missing_translation_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            (tree.source / "01.md").write_text("# A\n", encoding="utf-8")
            findings, _, _ = tree.run()
            self.assertIn("missing", str(findings[0]))

    def test_orphan_translation_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            (tree.fa / "99.md").write_text(TRANSLATED + "# الف\n", encoding="utf-8")
            findings, _, _ = tree.run()
            self.assertIn("orphan", str(findings[0]))

    def test_source_readme_is_not_expected_in_fa(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Tree(tmp)
            (tree.source / "README.md").write_text("# index\n", encoding="utf-8")
            # The project names these in [tool.book] exclude; pass it in here.
            findings, _, _ = tree.run({"README.md"})
            self.assertEqual(findings, [])


class TestMissingSourceTree(unittest.TestCase):
    def test_absent_source_exits_zero(self):
        # The normal state in CI. Failing here would make every run red.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fa").mkdir()
            code = main(["--check", "--source", str(root / "source"), "--fa", str(root / "fa")])
            self.assertEqual(code, 0)


class TestSubdirectoriesAndFiles(unittest.TestCase):
    def test_subdirectories_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            fa = root / "fa"
            (source / "01-discourses").mkdir(parents=True)
            (fa / "01-discourses").mkdir(parents=True)
            (source / "01-discourses" / "01.md").write_text("# A\n\none\n\ntwo\n", encoding="utf-8")
            (fa / "01-discourses" / "01.md").write_text(TRANSLATED + "# الف\n\nیک\n\nدو\n", encoding="utf-8")
            findings, compared, skipped = compare(source, fa, set())
            self.assertEqual(findings, [])
            self.assertEqual((compared, skipped), (1, 0))

    def test_two_files_direct_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src_file = root / "src.md"
            fa_file = root / "fa.md"
            src_file.write_text("# A\n\none\n", encoding="utf-8")
            fa_file.write_text(TRANSLATED + "# الف\n\nیک\n", encoding="utf-8")
            code = main([str(src_file), str(fa_file)])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
