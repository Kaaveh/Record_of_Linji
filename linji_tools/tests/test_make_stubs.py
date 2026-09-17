import tempfile
import unittest
from pathlib import Path


from linji_tools.make_stubs import (
    fa_stub,
    heading_for,
    load_titles,
    source_names,
    sync,
    to_persian_digits,
)


# A fixture, not the installed config. These tests must pass in this repository,
# which has no [tool.book] section -- depending on a consuming project's titles
# would make them fail everywhere except inside that project.
TITLES = {
    "preface.md": "پیش‌گفتار",
    "glossary.md": "واژه‌نامه",
}


def make_source(root: Path, names) -> Path:
    source = root / "source"
    source.mkdir(parents=True, exist_ok=True)
    for name in names:
        (source / name).write_text(f"### {Path(name).stem}\n\nbody\n", encoding="utf-8")
    return source


class TestNaming(unittest.TestCase):
    def test_numbered_files_sort_numerically_not_lexically(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = make_source(Path(tmp), ["10.md", "2.md", "1.md", "preface.md"])
            self.assertEqual(source_names(source, set()), ["1.md", "2.md", "10.md", "preface.md"])

    def test_named_files_come_after_numbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = make_source(Path(tmp), ["glossary.md", "01.md"])
            self.assertEqual(source_names(source, set()), ["01.md", "glossary.md"])

    def test_exclusions_are_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = make_source(Path(tmp), ["01.md", "README.md"])
            self.assertEqual(source_names(source, {"README.md"}), ["01.md"])

    def test_missing_source_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                source_names(Path(tmp) / "nope", set())


class TestHeadings(unittest.TestCase):
    def test_numbered_file_gets_persian_digits(self):
        self.assertEqual(heading_for("42.md", TITLES), "۴۲")

    def test_zero_padding_is_dropped(self):
        self.assertEqual(heading_for("01.md", TITLES), "۱")

    def test_named_file_uses_title_table(self):
        self.assertEqual(heading_for("glossary.md", TITLES), "واژه‌نامه")

    def test_unknown_named_file_falls_back_to_stem(self):
        self.assertEqual(heading_for("colophon.md", TITLES), "colophon")

    def test_persian_digit_conversion(self):
        self.assertEqual(to_persian_digits(2026), "۲۰۲۶")

    def test_stub_has_status_heading_and_marker(self):
        body = fa_stub("42.md", TITLES)
        self.assertIn("status: untranslated", body)
        self.assertIn("<!-- TODO: translate -->", body)
        self.assertIn("# ۴۲", body)

    def test_stub_carries_no_source_text(self):
        self.assertNotIn("body", fa_stub("42.md", TITLES))


class TestTitlesFile(unittest.TestCase):
    def test_tsv_overrides_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.tsv"
            path.write_text("# comment\n\nglossary.md\tفرهنگ واژگان\n", encoding="utf-8")
            titles = load_titles(path, TITLES)
            self.assertEqual(titles["glossary.md"], "فرهنگ واژگان")
            self.assertEqual(titles["preface.md"], TITLES["preface.md"])

    def test_malformed_line_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.tsv"
            path.write_text("glossary.md no tab here\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_titles(path)


class TestSync(unittest.TestCase):
    def test_filenames_match_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = make_source(root, ["01.md", "02.md", "glossary.md", "README.md"])
            written, skipped, orphans = sync(
                source, root / "fa", TITLES, {"README.md"}, force=False
            )
            self.assertEqual((written, skipped, orphans), (3, 0, []))
            self.assertEqual(
                sorted(p.name for p in (root / "fa").iterdir()),
                ["01.md", "02.md", "glossary.md"],
            )

    def test_existing_files_are_not_clobbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = make_source(root, ["01.md"])
            sync(source, root / "fa", TITLES, set(), force=False)
            claimed = root / "fa" / "01.md"
            claimed.write_text("ترجمهٔ انجام‌شده", encoding="utf-8")

            written, skipped, _ = sync(source, root / "fa", TITLES, set(), force=False)
            self.assertEqual((written, skipped), (0, 1))
            self.assertEqual(claimed.read_text(encoding="utf-8"), "ترجمهٔ انجام‌شده")

    def test_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = make_source(root, ["01.md"])
            claimed = root / "fa" / "01.md"
            sync(source, root / "fa", TITLES, set(), force=False)
            claimed.write_text("ترجمهٔ انجام‌شده", encoding="utf-8")

            sync(source, root / "fa", TITLES, set(), force=True)
            self.assertIn("<!-- TODO: translate -->", claimed.read_text(encoding="utf-8"))

    def test_orphans_are_reported_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = make_source(root, ["01.md"])
            fa = root / "fa"
            fa.mkdir()
            orphan = fa / "99-back.md"
            orphan.write_text("stale\n", encoding="utf-8")

            _, _, orphans = sync(source, fa, TITLES, set(), force=False)
            self.assertEqual(orphans, ["99-back.md"])
            self.assertTrue(orphan.exists())

    def test_subdirectories_are_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "01-discourses").mkdir(parents=True)
            (source / "01-discourses" / "01.md").write_text("### 1\n", encoding="utf-8")
            (source / "00-front").mkdir(parents=True)
            (source / "00-front" / "preface.md").write_text("## preface\n", encoding="utf-8")
            (source / "05-chinese").mkdir(parents=True)
            (source / "05-chinese" / "raw.md").write_text("chinese\n", encoding="utf-8")

            names = source_names(source, {"05-chinese"})
            self.assertEqual(names, ["00-front/preface.md", "01-discourses/01.md"])

            written, skipped, orphans = sync(source, root / "fa", TITLES, {"05-chinese"}, force=False)
            self.assertEqual((written, skipped, orphans), (2, 0, []))
            self.assertTrue((root / "fa" / "01-discourses" / "01.md").exists())
            self.assertTrue((root / "fa" / "00-front" / "preface.md").exists())
            self.assertIn("# پیش‌گفتار", (root / "fa" / "00-front" / "preface.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
