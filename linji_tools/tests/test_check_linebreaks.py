import unittest


from linji_tools import _md
from linji_tools.check_linebreaks import GENERAL_ABBREVIATIONS, find_violations, split_text

# A fixture, not the installed config. `Skt` is the kind of thing a project adds
# in [tool.linebreaks]; passing it explicitly keeps these tests honest in a
# repository that has no such section.
ABBREVIATIONS = GENERAL_ABBREVIATIONS | {"Skt"}


def doc(text):
    return _md.parse("t.md", text)


def lines_flagged(text):
    return [line for line, _, _ in find_violations(doc(text), ABBREVIATIONS)]


def fixed(text):
    d = doc(text)
    return d.prefix + split_text(d, ABBREVIATIONS)


class TestDetection(unittest.TestCase):
    def test_two_sentences_on_one_line_is_flagged(self):
        self.assertEqual(lines_flagged("راه دور است. ما فردا می‌رویم."), [1])

    def test_one_sentence_per_line_is_clean(self):
        self.assertEqual(lines_flagged("راه دور است.\nما فردا می‌رویم."), [])

    def test_persian_question_mark(self):
        self.assertEqual(lines_flagged("چیست؟ نمی‌دانم."), [1])

    def test_persian_semicolon(self):
        self.assertEqual(lines_flagged("یکم؛ دوم است."), [1])

    def test_exclamation(self):
        self.assertEqual(lines_flagged("برو! زود باش."), [1])

    def test_reports_the_right_line(self):
        self.assertEqual(lines_flagged("پاک است.\nیک. دو.\nپاک است."), [2])


class TestExemptions(unittest.TestCase):
    def test_heading_is_skipped(self):
        self.assertEqual(lines_flagged("# عنوان. ادامه"), [])

    def test_fenced_code_is_skipped(self):
        self.assertEqual(lines_flagged("```\nfoo. bar\n```"), [])

    def test_table_row_is_skipped(self):
        self.assertEqual(lines_flagged("| a. b | c. d |"), [])

    def test_code_span_is_skipped(self):
        self.assertEqual(lines_flagged("متن `foo. bar` است."), [])

    def test_link_destination_is_skipped(self):
        self.assertEqual(lines_flagged("[x](http://a. b) متن"), [])

    def test_ellipsis_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged("او گفت... و رفت"), [])

    def test_decimal_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged("عدد 3.14 است"), [])

    def test_numbered_list_marker_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged("1. گام نخست"), [])

    def test_numbered_note_after_anchor_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged('<a id="n39-1"></a>1. یادداشت'), [])

    def test_single_letter_initial_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged("نام J. Smith است"), [])

    def test_known_abbreviation_is_not_a_sentence_end(self):
        self.assertEqual(lines_flagged("واژهٔ Skt. nirvana است"), [])
        self.assertEqual(lines_flagged("رجوع کنید به p. 42 متن"), [])

    def test_real_sentence_end_after_abbreviation_still_caught(self):
        self.assertEqual(lines_flagged("متن Skt. nirvana است. ادامه دارد."), [1])


class TestNoteMarkers(unittest.TestCase):
    MARKER = '<a id="m2-2"></a>[<sup>²</sup>](#n2-2)'

    def test_marker_does_not_hide_a_run_on(self):
        self.assertEqual(lines_flagged(f"جملهٔ یکم.{self.MARKER} جملهٔ دوم."), [1])

    def test_split_keeps_marker_with_its_sentence(self):
        result = fixed(f"جملهٔ یکم.{self.MARKER} جملهٔ دوم.")
        self.assertEqual(result, f"جملهٔ یکم.{self.MARKER}\nجملهٔ دوم.")

    def test_trailing_marker_is_not_a_run_on(self):
        self.assertEqual(lines_flagged(f"جملهٔ یکم.{self.MARKER}"), [])


class TestFix(unittest.TestCase):
    def test_splits_at_the_boundary(self):
        self.assertEqual(fixed("یکم. دوم."), "یکم.\nدوم.")

    def test_splits_three_sentences(self):
        self.assertEqual(fixed("یکم. دوم. سوم."), "یکم.\nدوم.\nسوم.")

    def test_blockquote_marker_is_carried_to_the_new_line(self):
        # Without the marker the quote would end mid-block.
        self.assertEqual(fixed("> یکم. دوم."), "> یکم.\n> دوم.")

    def test_nested_blockquote_marker_is_preserved(self):
        self.assertEqual(fixed("> > یکم. دوم."), "> > یکم.\n> > دوم.")

    def test_frontmatter_survives(self):
        text = "---\nstatus: untranslated\n---\n\nیکم. دوم.\n"
        self.assertEqual(fixed(text), "---\nstatus: untranslated\n---\n\nیکم.\nدوم.\n")

    def test_fix_is_idempotent(self):
        once = fixed("یکم. دوم. سوم.")
        self.assertEqual(fixed(once), once)

    def test_fixed_output_is_clean(self):
        self.assertEqual(lines_flagged(fixed("یکم. دوم. سوم.")), [])

    def test_clean_text_is_untouched(self):
        text = "یکم.\nدوم.\n"
        self.assertEqual(fixed(text), text)


if __name__ == "__main__":
    unittest.main()
