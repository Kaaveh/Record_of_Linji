"""End-to-end: every checker must fail, via its CLI, on a known-bad tree.

The unit tests cover each rule in isolation. This covers the wiring -- argument
parsing, path defaults, exit codes, and the report actually reaching stdout --
which is what CI depends on and what unit tests never touch.

One deliberate defect per checker, matching the project's definition of done:
Arabic Yeh, a missing ZWNJ, a bidi override, a run-on line, and a parity
mismatch.
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path


from linji_tools import check_linebreaks
from linji_tools import check_parity
from linji_tools import normalize

ZWNJ = "‌"
RLO = "‮"

TRANSLATED = "---\nstatus: translated\n---\n\n"


def run(module, argv):
    """Call a checker's main() and capture (exit_code, stdout)."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        code = module.main(argv)
    return code, buffer.getvalue()


class BrokenTree:
    def __init__(self, tmp):
        self.root = Path(tmp)
        self.fa = self.root / "fa"
        self.source = self.root / "source"
        self.fa.mkdir()
        self.source.mkdir()

    def write(self, where, name, body):
        path = (self.fa if where == "fa" else self.source) / name
        path.write_text(body, encoding="utf-8")
        return path


class TestNormalizeCatchesDefects(unittest.TestCase):
    def test_arabic_yeh(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + "مي‌رود\n")
            code, out = run(normalize, ["--check", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("arabic_yeh", out)

    def test_missing_zwnj(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + "کتاب ها را می خواند\n")
            code, out = run(normalize, ["--check", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("zwnj_plural", out)
            self.assertIn("zwnj_mi", out)

    def test_bidi_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + f"سلام{RLO}جهان\n")
            code, out = run(normalize, ["--check", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("bidi", out)
            self.assertIn("U+202E", out)

    def test_fix_leaves_bidi_and_still_fails(self):
        # --fix must not silently launder a bidi override.
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + f"كتاب{RLO}\n")
            code, _ = run(normalize, ["--fix", str(path)])
            self.assertEqual(code, 1)
            after = path.read_text(encoding="utf-8")
            self.assertIn("کتاب", after)  # orthography was fixed
            self.assertIn(RLO, after)  # the override was not

    def test_clean_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + f"کتاب{ZWNJ}ها را می{ZWNJ}خواند\n")
            code, _ = run(normalize, ["--check", str(path)])
            self.assertEqual(code, 0)


class TestLinebreaksCatchesRunOn(unittest.TestCase):
    def test_run_on_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + "راه دور است. ما فردا می‌رویم.\n")
            code, out = run(check_linebreaks, ["--check", str(path)])
            self.assertEqual(code, 1)
            self.assertIn("sentence continues after end punctuation", out)
            self.assertIn("01.md:5", out)

    def test_fix_then_check_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            path = tree.write("fa", "01.md", TRANSLATED + "راه دور است. ما فردا می‌رویم.\n")
            run(check_linebreaks, ["--fix", str(path)])
            code, _ = run(check_linebreaks, ["--check", str(path)])
            self.assertEqual(code, 0)


class TestParityCatchesMismatch(unittest.TestCase):
    def test_dropped_paragraph(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            tree.write("source", "01.md", "# A\n\none\n\ntwo\n")
            tree.write("fa", "01.md", TRANSLATED + "# الف\n\nیک\n")
            code, out = run(
                check_parity, ["--check", "--source", str(tree.source), "--fa", str(tree.fa)]
            )
            self.assertEqual(code, 1)
            self.assertIn("2 blocks, source has 3", out)

    def test_matching_counts_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = BrokenTree(tmp)
            tree.write("source", "01.md", "# A\n\none\n")
            tree.write("fa", "01.md", TRANSLATED + "# الف\n\nیک\n")
            code, _ = run(
                check_parity, ["--check", "--source", str(tree.source), "--fa", str(tree.fa)]
            )
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
