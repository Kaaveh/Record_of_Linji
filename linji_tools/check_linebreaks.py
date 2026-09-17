"""Enforce semantic line breaks: one sentence per line.

This is the discipline the whole review process rests on. Git diffs by line,
and a word-level diff of right-to-left text is unreadable -- the changed words
scatter across the line in visual order that has nothing to do with storage
order. One sentence per line makes the sentence the unit of review, which is
also the unit a translator actually works in.

    before:  او گفت که راه دور است. ما فردا می‌رویم.
    after:   او گفت که راه دور است.
             ما فردا می‌رویم.

The heuristic: inside a prose block, sentence-final punctuation followed by
more text on the same line is a violation. Skipped:

  * headings, fenced code, block-level HTML and table rows
  * anything inside a code span, link destination, HTML tag or math
  * ellipses, decimals, single-letter initials, and known abbreviations
  * a numbered list marker -- "1." opens an item, it does not end a sentence

Note markers are stepped over rather than treated as text, so
"...seat.<a id="m2-2"></a>[<sup>2</sup>](#n2-2) The Master..." splits after the
marker and keeps the reference attached to the sentence it belongs to.

Usage:
    tools/check_linebreaks.py --check
    tools/check_linebreaks.py --fix
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import regex


from . import _md

REPO = _md.REPO

SKIP_KINDS = {"heading", "code", "html", "table"}

# Sentence-final punctuation, then any run of note markers, then a gap, then
# more text. The marker group is what keeps a footnote reference glued to the
# sentence it annotates instead of starting the next line.
SPLIT = regex.compile(
    r"""
      (?P<end>[.!?؟؛])
      (?P<marker>(?: <[^<>\n]*> | \[[^\]\n]*\]\([^)\n]*\) | \[\^[^\]\n]*\] | [¹²³⁰-⁹] )*)
      (?P<gap>[ \t]+)
      (?=\S)
    """,
    regex.VERBOSE,
)

# Only the prefix matters -- the match is on the word ending at the period.
# A general English set. Anything a particular text needs on top of it -- the
# language tags this book cites its sources in, say -- goes in
# [tool.linebreaks] abbreviations, so this list stays about English rather than
# about whichever book is being translated.
GENERAL_ABBREVIATIONS = frozenset(
    """
    cf eg ie etc vs viz
    p pp vol vols no nos ch chap chaps sec secs fig figs n nn
    ed eds trans comp rev repr
    Mr Mrs Ms Dr Prof St Mt Rev Fr
    ca fl b d r
    """.split()
)

ABBREVIATIONS = GENERAL_ABBREVIATIONS | frozenset(
    _md.config("linebreaks").get("abbreviations", [])
)

BLOCKQUOTE_PREFIX = regex.compile(r"^(\s*(?:>\s*)+)")
LIST_MARKER_ONLY = regex.compile(r"^\s{0,3}(?:<[^<>]*>)*\s*\d{1,9}$")
WORD_BEFORE = regex.compile(r"([\p{L}\p{N}]+)$")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def _is_exempt(line: str, match, protected: list[tuple[int, int]], offset: int, abbreviations) -> bool:
    """True if this punctuation does not actually end a sentence."""
    pos = match.start("end")
    absolute = offset + pos

    # Inside a code span, link destination, HTML tag or math.
    if any(start <= absolute < end for start, end in protected):
        return True

    char = match.group("end")
    if char != ".":
        return False

    # Ellipsis, in either spelling.
    if line[pos - 1 : pos] == "." or line[pos + 1 : pos + 2] == "." or line[pos - 1 : pos] == "…":
        return True

    before = line[:pos]
    word = WORD_BEFORE.search(before)
    if not word:
        return False

    token = word.group(1)

    # "1." opening a list item, with or without a leading anchor.
    if token.isdigit() and LIST_MARKER_ONLY.match(before):
        return True

    # Single-letter initial: "T. S. Eliot", "J. Buddhist".
    if len(token) == 1 and token.isalpha():
        return True

    return token in abbreviations


def find_violations(doc: _md.Document, abbreviations=None) -> list[tuple[int, int, int]]:
    """Returns (line_number, gap_start, gap_end) in body coordinates.

    `abbreviations` defaults to the general English set plus whatever
    [tool.linebreaks] adds. Pass a set to check against something else.
    """
    abbreviations = ABBREVIATIONS if abbreviations is None else abbreviations
    protected = _md.protected_spans(doc.body)
    kinds = doc.line_kinds()
    out = []
    line_start = 0

    for index, line in enumerate(doc.body.split("\n")):
        number = doc.body_line + index
        if kinds.get(number, "paragraph") not in SKIP_KINDS:
            for match in SPLIT.finditer(line):
                if not _is_exempt(line, match, protected, line_start, abbreviations):
                    out.append((number, line_start + match.start("gap"), line_start + match.end("gap")))
        line_start += len(line) + 1

    return out


def split_text(doc: _md.Document, abbreviations=None) -> str:
    """Insert the line breaks, preserving any blockquote marker."""
    violations = find_violations(doc, abbreviations)
    if not violations:
        return doc.body

    lines = doc.body.split("\n")
    body = doc.body
    for _, start, end in reversed(violations):
        line_index = body.count("\n", 0, start)
        prefix = BLOCKQUOTE_PREFIX.match(lines[line_index])
        # A blockquote continuation needs its own marker or the quote ends.
        replacement = "\n" + (prefix.group(1) if prefix else "")
        body = body[:start] + replacement + body[end:]

    return body


def process(paths: list[Path], fix: bool, abbreviations=None) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    rewritten = 0

    for path in paths:
        doc = _md.read(path)
        violations = find_violations(doc, abbreviations)
        for line, _, _ in violations:
            findings.append(Finding(str(path), line, "sentence continues after end punctuation"))

        if fix and violations:
            path.write_text(doc.prefix + split_text(doc, abbreviations), encoding="utf-8")
            rewritten += 1

    return findings, rewritten


def default_paths() -> list[Path]:
    return sorted(p for p in (REPO / "fa").rglob("*.md") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--fix", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)

    paths = args.paths or default_paths()
    findings, rewritten = process(paths, fix=args.fix)

    for finding in findings:
        print(finding)

    if args.fix:
        print(f"\nsplit lines in {rewritten} file(s)")
        return 0

    if findings:
        print(
            f"\n{len(findings)} run-on line(s) in {len({f.path for f in findings})} file(s)",
            file=sys.stderr,
        )
        print("run `just fix` to split them", file=sys.stderr)
        return 1

    print(f"linebreaks: {len(paths)} file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
