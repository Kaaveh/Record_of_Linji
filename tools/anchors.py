#!/usr/bin/env python3
"""This book's note, Chinese text, and heading apparatus, carried across gTranslator and verified.

The round-trip itself is general and lives in `bargardan_tools.anchors`, which knows
nothing about Sasaki's markup. This file is the half that does: the token
pattern and the Persian form each token takes for The Record of Linji.

Commentary sections contain Classical Chinese lines followed by English commentary.
Google Translate's Advanced model is designed for English-to-Persian, and will
mistranslate or corrupt Classical Chinese characters and Markdown footnotes if sent
raw. Our adapter masks:
  1. Classical Chinese text blocks and inline glyphs (⟦1⟧, ⟦2⟧...)
  2. Footnote references ([^n])
  3. Structural headings (## Part..., ### Discourse I, ## Commentary, #### Commentary Section I)

Usage:
    tools/anchors.py strip SOURCE -o OUT
    tools/anchors.py restore SOURCE DRAFT -o OUT
    tools/anchors.py --check
"""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Run as a script, sys.path[0] is tools/, so the checkers next door are not
# importable without this. Before the imports on purpose.
sys.path.insert(0, str(REPO))

import regex
from bargardan_tools import _md, anchors as engine
from bargardan_tools._md import to_persian_digits

# source/ files with no translation to pair against, from [tool.book] exclude.
EXCLUDE = set(_md.config("book").get("exclude", []))

# The Persian headings for named files, from [tool.book.titles].
TITLES = _md.config("book").get("titles", {})

FINAL_STATUS = "reviewed"

ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15,
    "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19, "XX": 20,
    "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25,
}

NAMED_HEADINGS = {
    "Foreword": "# پیش‌گفتار",
    "Preface to the 1975 Edition": "# دیباچهٔ نسخهٔ ۱۹۷۵",
    "Editor’s Prologue": "# پیش‌درآمد ویراستار",
    "Abbreviations": "# کوته‌نوشت‌ها",
    "Preface to the Recorded Sayings of Chan Master Linji Huizhao of Zhenzhou": "# دیباچهٔ ما فانگ",
    "Commentary: Preface of Ma Fang": "### شرح دیباچهٔ ما فانگ",
    "Historical Introduction to The Record of Linji": "# درآمد تاریخی",
    "Principal Sources": "## منابع اصلی",
    "Ruth Fuller Sasaki": "## روث فولر ساساکی",
    "The 2008 Edition": "## ویرایش ۲۰۰۸",
    "Acknowledgments": "## سپاس‌گزاری‌ها",
    "Bibliography": "# کتاب‌شناسی",
    "List of Personal Names": "# فهرست نام‌های اشخاص",
    "Cumulative Index": "# نمایه",
    "Additional Materials": "## یادداشت‌های تکمیلی",
    "Structure Overview": "## ساختار کتاب",
    "Discourses (上堂)": "## گفتارها (上堂)",
    "The Record of Linji (臨濟錄)": "# سخنان لین‌جی (臨濟錄)",
    "Part 1: The Record of Linji": "# بخش ۱: سخنان لین‌جی",
}

CJK_CHAR = r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]"
CJK_ANY = r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff\u3000-\u303f\uff00-\uffef\ufe30-\ufe4f]"

TOKEN = regex.compile(
    rf"""
      (?P<head>^(?P<hashes>\#{{1,6}})\ (?P<title>.*?)(?=<a\ id="|$))
    | (?P<ref>\[\^(?P<footnote_id>[^\]]+)\])
    | (?P<cjk>{CJK_CHAR}(?:(?:{CJK_ANY}|[ \t])*{CJK_ANY})?)
    """,
    regex.VERBOSE | regex.MULTILINE,
)


PART_DIVIDERS = ("Part One:", "Part Two:", "Part Three:")


def roman_to_int(roman: str) -> int:
    roman = roman.upper()
    if roman in ROMAN:
        return ROMAN[roman]
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(roman):
        val = values.get(ch, 0)
        if val < prev:
            total -= val
        else:
            total += val
        prev = val
    return total


def fa_heading(name: str, hashes: str, title: str) -> str | None:
    """The Persian form of a source heading, or None if fa/ drops it."""
    t = title.strip()
    if any(t.startswith(p) for p in PART_DIVIDERS):
        return None
    if t == "Commentary":
        return "## شرح"

    m = regex.match(r"^Discourse\s+([IVXLCDM]+)$", t, regex.IGNORECASE)
    if m:
        n = roman_to_int(m.group(1))
        return f"# گفتار {to_persian_digits(n)}"

    m = regex.match(r"^Critical\s+Examination\s+([IVXLCDM]+)$", t, regex.IGNORECASE)
    if m:
        n = roman_to_int(m.group(1))
        return f"# سنجش {to_persian_digits(n)}"

    m = regex.match(r"^Pilgrimage\s+([IVXLCDM]+)$", t, regex.IGNORECASE)
    if m:
        n = roman_to_int(m.group(1))
        return f"# سفر {to_persian_digits(n)}"

    m = regex.match(r"^Commentary\s+Section\s+([IVXLCDM]+)$", t, regex.IGNORECASE)
    if m:
        n = roman_to_int(m.group(1))
        return f"### شرح {to_persian_digits(n)}"

    if t in NAMED_HEADINGS:
        return NAMED_HEADINGS[t]

    p = Path(name)
    if name in TITLES:
        return f"# {TITLES[name]}"
    if p.name in TITLES:
        return f"# {TITLES[p.name]}"
    if p.stem in TITLES:
        return f"# {TITLES[p.stem]}"

    raise ValueError(f"{name}: no Persian form for heading {hashes} {title!r}")


def fa_token(name: str, match) -> str | None:
    """The Persian form of one source token, as it should land in fa/."""
    if match.group("cjk"):
        return match.group("cjk")
    if match.group("ref"):
        fn_id = match.group("footnote_id")
        if fn_id.isdigit():
            return f"[^{to_persian_digits(int(fn_id))}]"
        return f"[^{fn_id}]"
    return fa_heading(name, match.group("hashes"), match.group("title"))


def render_for(name: str):
    """This book's token renderer, bound to a filename."""
    return partial(fa_token, name)


def strip(name: str, text: str) -> str:
    return engine.strip(text, TOKEN, render_for(name))


def restore(name: str, source_text: str, draft: str) -> str:
    """The engine's round-trip, plus the front matter this book needs."""
    body = engine.restore(name, source_text, draft, TOKEN, render_for(name))
    parity_directive = (
        "<!-- parity: offset -1 -->\n\n"
        if any(f"## {p}" in source_text for p in PART_DIVIDERS)
        else ""
    )
    return f"---\nstatus: {FINAL_STATUS}\n---\n\n{parity_directive}{body.strip()}\n"


def main(argv: list[str] | None = None) -> int:
    return engine.main(
        argv,
        strip_text=strip,
        restore_text=restore,
        source_default=REPO / "source",
        target_default=REPO / "fa",
        exclude=EXCLUDE,
        description=__doc__,
    )


if __name__ == "__main__":
    raise SystemExit(main())
