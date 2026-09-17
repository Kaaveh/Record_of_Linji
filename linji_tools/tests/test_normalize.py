import unittest


from linji_tools.normalize import DEFAULTS, normalize_text

ZWNJ = "‌"


def fix(text, **overrides):
    config = dict(DEFAULTS)
    config.update(overrides)
    result, _ = normalize_text("t.md", text, config)
    return result


def rules_fired(text, **overrides):
    config = dict(DEFAULTS)
    config.update(overrides)
    _, findings = normalize_text("t.md", text, config)
    return {f.rule for f in findings}


class TestLetters(unittest.TestCase):
    def test_arabic_yeh_becomes_farsi_yeh(self):
        self.assertEqual(fix("مي‌رود"), "می‌رود")

    def test_arabic_kaf_becomes_keheh(self):
        self.assertEqual(fix("كتاب"), "کتاب")

    def test_tatweel_is_stripped(self):
        self.assertEqual(fix("کتـــاب"), "کتاب")

    def test_rules_can_be_switched_off(self):
        self.assertEqual(fix("كتاب", arabic_kaf=False), "كتاب")


class TestDigits(unittest.TestCase):
    def test_arabic_indic_becomes_persian(self):
        self.assertEqual(fix("٤٢"), "۴۲")

    def test_latin_digits_are_left_alone_by_default(self):
        self.assertEqual(fix("سال 2019"), "سال 2019")

    def test_latin_digits_convert_when_enabled(self):
        self.assertEqual(fix("سال 2019", latin_digits=True), "سال ۲۰۱۹")


class TestZwnj(unittest.TestCase):
    def test_mi_prefix_joins(self):
        self.assertEqual(fix("می رود"), f"می{ZWNJ}رود")

    def test_nemi_prefix_joins(self):
        self.assertEqual(fix("نمی رود"), f"نمی{ZWNJ}رود")

    def test_mi_does_not_join_across_a_line_break(self):
        # Joining here would destroy a semantic line break.
        self.assertEqual(fix("می\nرود"), "می\nرود")

    def test_plural_haa_joins(self):
        self.assertEqual(fix("کتاب ها"), f"کتاب{ZWNJ}ها")

    def test_suffixed_plural_joins(self):
        self.assertEqual(fix("کتاب هایی"), f"کتاب{ZWNJ}هایی")

    def test_comparative_joins(self):
        self.assertEqual(fix("بزرگ تر"), f"بزرگ{ZWNJ}تر")

    def test_superlative_joins(self):
        self.assertEqual(fix("بزرگ ترین"), f"بزرگ{ZWNJ}ترین")

    def test_repeated_zwnj_collapses(self):
        self.assertEqual(fix(f"کتاب{ZWNJ}{ZWNJ}{ZWNJ}ها"), f"کتاب{ZWNJ}ها")

    def test_zwnj_next_to_space_is_dropped(self):
        self.assertEqual(fix(f"کتاب {ZWNJ}ها"), f"کتاب{ZWNJ}ها")

    def test_zwnj_at_line_end_is_dropped(self):
        self.assertEqual(fix(f"کتاب{ZWNJ}\nبعدی"), "کتاب\nبعدی")

    def test_correct_zwnj_is_preserved(self):
        self.assertEqual(fix(f"می{ZWNJ}رود"), f"می{ZWNJ}رود")


class TestPunctuationAndQuotes(unittest.TestCase):
    def test_ascii_comma_after_persian(self):
        self.assertEqual(fix("بله, درست است"), "بله، درست است")

    def test_ascii_question_mark_after_persian(self):
        self.assertEqual(fix("چیست?"), "چیست؟")

    def test_ascii_semicolon_after_persian(self):
        self.assertEqual(fix("یکم; دوم"), "یکم؛ دوم")

    def test_latin_run_punctuation_is_left_alone(self):
        self.assertEqual(fix("واژهٔ Lin-chi, master"), "واژهٔ Lin-chi, master")

    def test_straight_quotes_become_guillemets(self):
        self.assertEqual(fix('او گفت "سلام" و رفت'), "او گفت «سلام» و رفت")

    def test_curly_quotes_become_guillemets(self):
        self.assertEqual(fix("او گفت “سلام” و رفت"), "او گفت «سلام» و رفت")


class TestHarakat(unittest.TestCase):
    def test_preserved_by_default(self):
        self.assertEqual(fix("کِتاب"), "کِتاب")

    def test_stripped_when_configured(self):
        self.assertEqual(fix("کِتاب", harakat="strip"), "کتاب")


class TestProtectedSpans(unittest.TestCase):
    def test_html_anchor_id_is_untouched(self):
        # The book's 506 note cross-references live in these.
        text = '<a id="m39-1"></a>می رود'
        self.assertEqual(fix(text), f'<a id="m39-1"></a>می{ZWNJ}رود')

    def test_link_destination_is_untouched(self):
        text = "[<sup>۱</sup>](#n39-1) کتاب ها"
        self.assertEqual(fix(text), f"[<sup>۱</sup>](#n39-1) کتاب{ZWNJ}ها")

    def test_inline_code_is_untouched(self):
        self.assertEqual(fix("`كتاب` كتاب"), "`كتاب` کتاب")

    def test_fenced_code_is_untouched(self):
        text = "```\nكتاب\n```\n\nكتاب"
        self.assertEqual(fix(text), "```\nكتاب\n```\n\nکتاب")

    def test_quotes_inside_html_attribute_are_untouched(self):
        self.assertEqual(fix('<a id="x"></a>'), '<a id="x"></a>')


class TestToggleRegions(unittest.TestCase):
    def test_off_region_is_exempt(self):
        text = "كتاب\n\n<!-- normalize: off -->\nكتاب\n<!-- normalize: on -->\n\nكتاب"
        result = fix(text)
        self.assertEqual(result.count("كتاب"), 1)
        self.assertEqual(result.count("کتاب"), 2)

    def test_unclosed_off_disables_to_end_of_file(self):
        text = "كتاب\n\n<!-- normalize: off -->\nكتاب\nكتاب"
        result = fix(text)
        self.assertEqual(result.count("كتاب"), 2)


class TestBidi(unittest.TestCase):
    RLO = "‮"
    PDI = "⁩"

    def test_bidi_override_is_reported(self):
        self.assertIn("bidi", rules_fired(f"سلام{self.RLO}جهان"))

    def test_isolate_is_reported(self):
        self.assertIn("bidi", rules_fired(f"سلام{self.PDI}جهان"))

    def test_bidi_is_never_auto_fixed(self):
        text = f"سلام{self.RLO}جهان"
        self.assertIn(self.RLO, fix(text))

    def test_bidi_reported_even_inside_code_span(self):
        # The hazard is the stored bytes, not the rendered prose.
        self.assertIn("bidi", rules_fired(f"`{self.RLO}`"))

    def test_bidi_reported_even_in_disabled_region(self):
        text = f"<!-- normalize: off -->\n{self.RLO}\n<!-- normalize: on -->"
        self.assertIn("bidi", rules_fired(text))

    def test_clean_text_reports_nothing(self):
        self.assertEqual(rules_fired(f"می{ZWNJ}رود و کتاب{ZWNJ}ها"), set())


class TestReporting(unittest.TestCase):
    def test_finding_carries_the_right_line(self):
        text = "پاک\nكتاب\nپاک"
        _, findings = normalize_text("fa/01.md", text, dict(DEFAULTS))
        self.assertEqual([(f.line, f.rule) for f in findings], [(2, "arabic_kaf")])

    def test_finding_formats_as_file_line(self):
        _, findings = normalize_text("fa/01.md", "كتاب", dict(DEFAULTS))
        self.assertTrue(str(findings[0]).startswith("fa/01.md:1: arabic_kaf:"))

    def test_frontmatter_lines_are_counted(self):
        text = "---\nstatus: untranslated\n---\n\nكتاب\n"
        _, findings = normalize_text("fa/01.md", text, dict(DEFAULTS))
        self.assertEqual(findings[0].line, 5)


class TestIdempotence(unittest.TestCase):
    def test_fixing_twice_changes_nothing(self):
        text = "می رود، كتاب ها و بزرگ تر\nمي‌گويد \"سلام\"\n"
        once = fix(text)
        self.assertEqual(fix(once), once)

    def test_fixed_output_is_clean(self):
        text = "می رود، كتاب ها و بزرگ تر\n"
        self.assertEqual(rules_fired(fix(text)), set())


if __name__ == "__main__":
    unittest.main()
