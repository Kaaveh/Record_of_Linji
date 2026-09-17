"""Persian orthographic normalization for fa/.

These errors are invisible in code review. An Arabic Yeh and a Farsi Yeh are
the same shape in almost every font; a missing ZWNJ looks like a space. Left
unchecked they accumulate for years and then break search, sort and hyphenation
all at once. This runs in CI on every PR so they never land.

Rules are individually toggleable in [tool.normalize] in pyproject.toml, and a
region of any file can be exempted with:

    <!-- normalize: off -->
    ...
    <!-- normalize: on -->

Nothing is rewritten inside fenced code, inline code, HTML tags, HTML comments,
link destinations or math -- see tools/_md.py. That matters here: this book's
506 note cross-references are inline HTML anchors, and an orthography pass that
touched `<a id="m39-1">` would break every one of them silently.

Checked against virastar (JS), hazm and persian-tools (Python). Deliberately
NOT implemented, with reasons:

  * Collapsing runs of spaces, and space-fixing around punctuation. Fights
    Markdown table alignment and the semantic-line-break discipline.
  * Hamza normalization -- Alef with hamza above/below to bare Alef, and Waw
    and Yeh with hamza. hazm does this. It is the right call for Persian prose
    but destructive to transliterated Sanskrit and to quoted Arabic, both of
    which this book contains. Revisit if STYLE.md asks for it.
  * Heh-with-hamza to Heh + ZWNJ + Yeh for the ezafe. Genuinely contested in
    Persian typography; the maintainer should settle it in STYLE.md before a
    script enforces one side.
  * Converting "..." to a single ellipsis. check_linebreaks.py needs to see
    ellipses to tell them apart from sentence ends, and the choice is a style
    call, not an orthographic error.
  * persian-tools' phone-number, IBAN, ordinal-word and date helpers. Not
    orthography.

Usage:
    tools/normalize.py --check          # exit non-zero, print file:line report
    tools/normalize.py --fix            # rewrite in place
    tools/normalize.py --check fa/01.md
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

import regex


from . import _md
from ._md import ZWNJ

REPO = Path.cwd()

# Bidi overrides and isolates. Always an error, never auto-fixed: they can make
# a diff render in a different order than it is stored, which turns review of
# an outside PR into theatre. A human has to look at these.
BIDI_OVERRIDES = regex.compile(r"[‪-‮⁦-⁩]")

BIDI_NAMES = {
    "‪": "LRE U+202A",
    "‫": "RLE U+202B",
    "‬": "PDF U+202C",
    "‭": "LRO U+202D",
    "‮": "RLO U+202E",
    "⁦": "LRI U+2066",
    "⁧": "RLI U+2067",
    "⁨": "FSI U+2068",
    "⁩": "PDI U+2069",
}

ARABIC = r"\p{Arabic}"

DEFAULTS = {
    "arabic_yeh": True,
    "arabic_kaf": True,
    "arabic_digits": True,
    "latin_digits": False,
    "tatweel": True,
    "punctuation": True,
    "zwnj_mi": True,
    "zwnj_plural": True,
    "zwnj_comparative": True,
    "zwnj_collapse": True,
    "zwnj_trim": True,
    "quotes": True,
    "harakat": "preserve",
}

ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹")
LATIN_TO_PERSIAN = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
ASCII_PUNCT = {",": "،", ";": "؛", "?": "؟"}

# mi / nemi verbal prefix. [ \t]+ rather than \s+ on purpose: joining across a
# newline would destroy a semantic line break.
RE_MI = regex.compile(rf"(?<![{ARABIC}‌])(ن?می)[ \t]+(?=[{ARABIC}])")
# Plural haa and its common suffixed forms, written as a separate word.
RE_PLURAL = regex.compile(rf"(?<=[{ARABIC}])[ \t]+(ها(?:ی|یی|یم|یت|یش|یمان|یتان|یشان)?)(?![{ARABIC}])")
# Comparative tar / superlative tarin.
RE_COMPARATIVE = regex.compile(rf"(?<=[{ARABIC}])[ \t]+(تر(?:ین)?)(?![{ARABIC}])")
RE_ZWNJ_RUN = regex.compile("‌{2,}")
# ZWNJ only belongs between two letters. Anywhere else it is invisible noise.
RE_ZWNJ_LOOSE = regex.compile(rf"(?<![{ARABIC}])‌|‌(?![{ARABIC}])")
RE_ASCII_PUNCT = regex.compile(rf"(?<=[{ARABIC}])([,;?])")
RE_HARAKAT = regex.compile(r"[ً-ْ]")
RE_STRAIGHT_QUOTES = regex.compile(r'"([^"\n]*)"')
RE_CURLY_QUOTES = regex.compile(r"“([^”\n]*)”")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


def load_config(path: Path | None = None) -> dict:
    config = dict(DEFAULTS)
    path = path or REPO / "pyproject.toml"
    if path.is_file():
        with path.open("rb") as handle:
            data = tomllib.load(handle)
        config.update(data.get("tool", {}).get("normalize", {}))
    return config


# Each rule is (config key, human description, function).
#
# Order matters, and it is cleanup-before-insertion. A stray ZWNJ sitting
# between a space and a suffix -- "کتاب <ZWNJ>ها" -- blocks the plural rule
# from matching, because the rule expects the suffix immediately after the
# space. Collapsing and trimming first turns that into "کتاب ها", which then
# joins correctly. The reverse order leaves the space in place.
#
# Insertion cannot undo the cleanup: every insertion rule requires an Arabic
# letter on both sides, so it can only ever place a ZWNJ where one belongs,
# and never two in a row.
def _rules(config: dict):
    rules = [
        ("arabic_yeh", "Arabic Yeh U+064A should be Farsi Yeh U+06CC",
         lambda s: s.replace("ي", "ی")),
        ("arabic_kaf", "Arabic Kaf U+0643 should be Keheh U+06A9",
         lambda s: s.replace("ك", "ک")),
        ("arabic_digits", "Arabic-Indic digits should be Persian U+06F0-U+06F9",
         lambda s: s.translate(ARABIC_INDIC)),
        ("latin_digits", "Latin digits should be Persian U+06F0-U+06F9",
         lambda s: s.translate(LATIN_TO_PERSIAN)),
        ("tatweel", "Tatweel/Kashida U+0640 should be removed",
         lambda s: s.replace("ـ", "")),
        ("punctuation", "ASCII punctuation after Persian should be Persian",
         lambda s: RE_ASCII_PUNCT.sub(lambda m: ASCII_PUNCT[m.group(1)], s)),
        ("quotes", "ASCII quotes should be Persian guillemets",
         lambda s: RE_CURLY_QUOTES.sub(r"«\1»", RE_STRAIGHT_QUOTES.sub(r"«\1»", s))),
        ("zwnj_collapse", "repeated ZWNJ should collapse to one",
         lambda s: RE_ZWNJ_RUN.sub(ZWNJ, s)),
        ("zwnj_trim", "ZWNJ outside a word should be removed",
         lambda s: RE_ZWNJ_LOOSE.sub("", s)),
        ("zwnj_mi", "mi/nemi prefix should join with ZWNJ",
         lambda s: RE_MI.sub(rf"\1{ZWNJ}", s)),
        ("zwnj_plural", "plural haa should join with ZWNJ",
         lambda s: RE_PLURAL.sub(rf"{ZWNJ}\1", s)),
        ("zwnj_comparative", "comparative tar/tarin should join with ZWNJ",
         lambda s: RE_COMPARATIVE.sub(rf"{ZWNJ}\1", s)),
    ]
    enabled = [(name, desc, fn) for name, desc, fn in rules if config.get(name, False)]

    if config.get("harakat", "preserve") == "strip":
        enabled.append(("harakat", "harakat should be stripped", lambda s: RE_HARAKAT.sub("", s)))
    return enabled


def _editable_chunks(text: str):
    """Yield (start, end) spans that normalization may rewrite."""
    disabled = _md.toggle_regions(text, "normalize")
    cursor = 0
    for start, end in disabled:
        if start > cursor:
            yield cursor, start
        cursor = end
    if cursor < len(text):
        yield cursor, len(text)


def apply_rule(text: str, func) -> str:
    """Apply `func` only where it is allowed: outside disabled regions, and
    outside protected spans within them."""
    out = []
    cursor = 0
    for start, end in _editable_chunks(text):
        out.append(text[cursor:start])
        out.append(_md.apply_outside_protected(text[start:end], func))
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


def changed_lines(before: str, after: str) -> list[int]:
    """1-based line numbers that differ. Every rule is line-count preserving,
    so a positional comparison is exact."""
    a, b = before.split("\n"), after.split("\n")
    return [i for i, (x, y) in enumerate(zip(a, b), start=1) if x != y]


def normalize_text(path: str, text: str, config: dict) -> tuple[str, list[Finding]]:
    findings: list[Finding] = []

    # Bidi overrides first, and independent of every toggle. Reported against
    # the raw text -- inside code spans and disabled regions too, because the
    # hazard is the stored bytes, not the rendered prose.
    for match in BIDI_OVERRIDES.finditer(text):
        char = match.group()
        findings.append(
            Finding(
                path,
                _md.line_of(text, match.start()),
                "bidi",
                f"bidi override {BIDI_NAMES.get(char, repr(char))} — remove it by hand, "
                "never auto-fixed",
            )
        )

    for name, description, func in _rules(config):
        updated = apply_rule(text, func)
        if updated != text:
            for line in changed_lines(text, updated):
                findings.append(Finding(path, line, name, description))
            text = updated

    return text, findings


def process(paths: list[Path], config: dict, fix: bool) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    rewritten = 0
    for path in paths:
        original = path.read_text(encoding="utf-8")
        updated, found = normalize_text(str(path), original, config)
        findings.extend(found)
        if fix and updated != original:
            path.write_text(updated, encoding="utf-8")
            rewritten += 1
    return findings, rewritten


def default_paths() -> list[Path]:
    return sorted(p for p in (REPO / "fa").rglob("*.md") if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="report and exit non-zero")
    mode.add_argument("--fix", action="store_true", help="rewrite files in place")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--config", type=Path, help="pyproject.toml to read [tool.normalize] from")
    args = parser.parse_args(argv)

    paths = args.paths or default_paths()
    config = load_config(args.config)
    findings, rewritten = process(paths, config, fix=args.fix)

    bidi = [f for f in findings if f.rule == "bidi"]
    other = [f for f in findings if f.rule != "bidi"]

    for finding in sorted(findings, key=lambda f: (f.path, f.line, f.rule)):
        print(finding)

    if args.fix:
        print(f"\nnormalized {rewritten} file(s)")
        # Orthography is fixed; bidi overrides are not, and must still fail.
        if bidi:
            print(f"{len(bidi)} bidi override(s) left in place — remove by hand", file=sys.stderr)
            return 1
        return 0

    if findings:
        print(
            f"\n{len(other)} orthography issue(s), {len(bidi)} bidi override(s) "
            f"in {len({f.path for f in findings})} file(s)",
            file=sys.stderr,
        )
        if other:
            print("run `just fix` to correct the orthography", file=sys.stderr)
        return 1

    print(f"normalize: {len(paths)} file(s) clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
