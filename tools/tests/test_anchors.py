#!/usr/bin/env python3
"""Unit tests for tools/anchors.py adapter."""

import unittest
from pathlib import Path

from tools.anchors import (
    TOKEN,
    fa_heading,
    fa_token,
    restore,
    roman_to_int,
    strip,
)


class TestRomanNumerals(unittest.TestCase):
    def test_basic_numerals(self):
        self.assertEqual(roman_to_int("I"), 1)
        self.assertEqual(roman_to_int("IV"), 4)
        self.assertEqual(roman_to_int("V"), 5)
        self.assertEqual(roman_to_int("IX"), 9)
        self.assertEqual(roman_to_int("X"), 10)
        self.assertEqual(roman_to_int("XIV"), 14)
        self.assertEqual(roman_to_int("XIX"), 19)
        self.assertEqual(roman_to_int("XXII"), 22)
        self.assertEqual(roman_to_int("XXIV"), 24)

    def test_case_insensitive(self):
        self.assertEqual(roman_to_int("xxiv"), 24)
        self.assertEqual(roman_to_int("xii"), 12)


class TestHeadingMapping(unittest.TestCase):
    def test_part_headings_are_dropped(self):
        self.assertIsNone(fa_heading("01.md", "##", "Part One: Discourses (上堂)"))
        self.assertIsNone(fa_heading("23.md", "##", "Part Two: Critical Examinations (勘辨)"))
        self.assertIsNone(fa_heading("47.md", "##", "Part Three: Record of Pilgrimages (行錄)"))

    def test_discourses_headings(self):
        self.assertEqual(fa_heading("01.md", "###", "Discourse I"), "# گفتار ۱")
        self.assertEqual(fa_heading("02.md", "###", "Discourse II"), "# گفتار ۲")
        self.assertEqual(fa_heading("22.md", "###", "Discourse XXII"), "# گفتار ۲۲")

    def test_critical_examinations_headings(self):
        self.assertEqual(fa_heading("23.md", "###", "Critical Examination I"), "# سنجش ۱")
        self.assertEqual(fa_heading("46.md", "###", "Critical Examination XXIV"), "# سنجش ۲۴")

    def test_pilgrimages_headings(self):
        self.assertEqual(fa_heading("47.md", "###", "Pilgrimage I"), "# سفر ۱")
        self.assertEqual(fa_heading("68.md", "###", "Pilgrimage XXII"), "# سفر ۲۲")

    def test_commentary_headings(self):
        self.assertEqual(fa_heading("01.md", "##", "Commentary"), "## شرح")
        self.assertEqual(fa_heading("01.md", "####", "Commentary Section I"), "### شرح ۱")
        self.assertEqual(fa_heading("22.md", "####", "Commentary Section XXII"), "### شرح ۲۲")

    def test_front_matter_headings(self):
        self.assertEqual(fa_heading("foreword.md", "##", "Foreword"), "# پیش‌گفتار")
        self.assertEqual(fa_heading("abbreviations.md", "##", "Abbreviations"), "# کوته‌نوشت‌ها")
        self.assertEqual(fa_heading("editors-prologue.md", "##", "Editor’s Prologue"), "# پیش‌درآمد ویراستار")


class TestFootnotes(unittest.TestCase):
    def test_footnote_reference_conversion(self):
        match = TOKEN.search("This is a sentence.[^1] Next sentence.")
        self.assertIsNotNone(match)
        self.assertEqual(fa_token("test.md", match), "[^۱]")

    def test_multiple_digits_footnote(self):
        match = TOKEN.search("Reference to note.[^42]")
        self.assertIsNotNone(match)
        self.assertEqual(fa_token("test.md", match), "[^۴۲]")


class TestChineseMasking(unittest.TestCase):
    def test_standalone_cjk_block(self):
        cjk_text = "府主王常侍、與諸官請師升座。師上堂云、山僧今日事不獲已、曲順人情、方登此座。"
        stripped = strip("test.md", cjk_text)
        self.assertEqual(stripped.strip(), "⟦1⟧")

        restored = restore("test.md", cjk_text, stripped)
        self.assertIn(cjk_text, restored)

    def test_inline_cjk_terms(self):
        text = "Linji Yixuan 臨濟義玄 lived at Linji yuan 臨濟院."
        stripped = strip("test.md", text)
        self.assertEqual(stripped, "Linji Yixuan ⟦1⟧ lived at Linji yuan ⟦2⟧.")

        draft = "لین‌جی ییشوان ⟦1⟧ در لین‌جی یوان ⟦2⟧ می‌زیست."
        restored = restore("test.md", text, draft)
        self.assertIn("لین‌جی ییشوان 臨濟義玄 در لین‌جی یوان 臨濟院 می‌زیست.", restored)


class TestFullRoundTrip(unittest.TestCase):
    def test_section_strip_and_restore(self):
        src = (
            "## Part One: Discourses (上堂)\n\n"
            "### Discourse I\n\n"
            "The Governor requested the master to address them.\n\n"
            "---\n\n"
            "## Commentary\n\n"
            "#### Commentary Section I\n\n"
            "府主王常侍、與諸官請師升座。\n\n"
            "Governor Wang 府主王常侍 invited the master.\n"
        )
        stripped = strip("01.md", src)
        self.assertNotIn("Discourse I", stripped)
        self.assertNotIn("府主王常侍", stripped)

        # Simulated Persian draft with sentinels intact
        draft = (
            "⟦1⟧\n\n"
            "⟦2⟧\n\n"
            "حاکم از استاد خواست تا سخنرانی کند.\n\n"
            "---\n\n"
            "⟦3⟧\n\n"
            "⟦4⟧\n\n"
            "⟦5⟧\n\n"
            "فرماندار وانگ ⟦6⟧ از استاد دعوت کرد.\n"
        )
        restored = restore("01.md", src, draft)
        self.assertIn("status: reviewed", restored)
        self.assertIn("<!-- parity: offset -1 -->", restored)
        self.assertIn("# گفتار ۱", restored)
        self.assertIn("## شرح", restored)
        self.assertIn("### شرح ۱", restored)
        self.assertIn("府主王常侍、與諸官請師升座。", restored)
        self.assertIn("فرماندار وانگ 府主王常侍 از استاد دعوت کرد.", restored)


if __name__ == "__main__":
    unittest.main()
