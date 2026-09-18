"""Catch dropped paragraphs by comparing block counts between source/ and fa/.

A translator skipping a paragraph is the single most expensive error in this
kind of project: it is invisible in review, because the Persian reads perfectly
well without it, and it surfaces years later when someone compares editions.
Counting blocks catches it mechanically.

Blocks are blank-line-delimited runs, with fenced code held together -- what a
reviewer would call a paragraph, not what CommonMark calls a block. See
tools/_md.py. That is enough here because the comparison is like against like.

Files are paired by filename, which must match byte-for-byte across the two
trees. tools/make_stubs.py is what guarantees that; do not create fa/ files by
hand.

Skipped:
  * any fa/ file still marked `status: untranslated`
  * any fa/ file containing <!-- parity: skip -->

For deliberate structural divergence, prefer an offset over a skip -- it keeps
the file checked instead of switching it off:

    <!-- parity: offset -1 -->     fa/ has one block fewer than source/

The four part-opening chapters use this. Their part heading lives in
_quarto.yml as a `part:` entry so Quarto renders a real part title page, which
means the heading is not repeated in the Markdown.

If source/ is absent this exits 0 with a notice. That is the normal state in
CI, where the source text is deliberately not present -- it is licensed to the
maintainer for translation, not for redistribution.

Usage:
    tools/check_parity.py --check
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


from . import _md

REPO = _md.REPO

# source/ files with no translation to pair against -- for this book, the
# maintainer's index and provenance note. Project data, so it comes from
# [tool.book] exclude rather than being named here. --exclude overrides it.
EXCLUDE = set(_md.config("book").get("exclude", []))


@dataclass(frozen=True)
class Finding:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def parse_offset(body: str) -> int:
    """Value of <!-- parity: offset N -->, or 0."""
    for value in _md.directives(body, "parity"):
        parts = value.split()
        if len(parts) == 2 and parts[0] == "offset":
            try:
                return int(parts[1])
            except ValueError:
                raise ValueError(f"bad parity offset: {value!r}")
    return 0


def is_skipped(body: str) -> bool:
    return any(v.strip() == "skip" for v in _md.directives(body, "parity"))


def is_excluded(p_rel: Path, exclude_set: set[str]) -> bool:
    rel_str = p_rel.as_posix()
    return (
        rel_str in exclude_set
        or p_rel.name in exclude_set
        or any(part in exclude_set for part in p_rel.parts)
    )


def compare(source_dir: Path, fa_dir: Path, exclude: set[str] | None = None) -> tuple[list[Finding], int, int]:
    """Returns (findings, compared, skipped)."""
    findings: list[Finding] = []
    compared = skipped = 0

    ex = EXCLUDE if exclude is None else exclude
    source_names = {
        p.relative_to(source_dir).as_posix()
        for p in source_dir.rglob("*.md")
        if not is_excluded(p.relative_to(source_dir), ex)
    }
    fa_names = {
        p.relative_to(fa_dir).as_posix()
        for p in fa_dir.rglob("*.md")
        if not is_excluded(p.relative_to(fa_dir), ex)
    }

    for name in sorted(source_names - fa_names):
        findings.append(Finding(f"fa/{name}", "missing — source/ has it, fa/ does not"))
    for name in sorted(fa_names - source_names):
        findings.append(Finding(f"fa/{name}", "orphan — no counterpart in source/"))

    for name in sorted(source_names & fa_names):
        fa_doc = _md.read(fa_dir / name)

        if fa_doc.status == "untranslated":
            skipped += 1
            continue
        if is_skipped(fa_doc.body):
            skipped += 1
            continue

        try:
            offset = parse_offset(fa_doc.body)
        except ValueError as exc:
            findings.append(Finding(f"fa/{name}", str(exc)))
            continue

        source_doc = _md.read(source_dir / name)
        source_count = len(_md.iter_blocks(source_doc))
        fa_count = len(_md.iter_blocks(fa_doc))
        compared += 1

        actual = fa_count - source_count
        if actual != offset:
            detail = f"{fa_count} blocks, source has {source_count}"
            if offset:
                detail += f" (offset {offset:+d} declared, actual {actual:+d})"
            findings.append(Finding(f"fa/{name}", detail))

    return findings, compared, skipped


def compare_files(source_file: Path, fa_file: Path) -> list[Finding]:
    """Compare block parity between two specific files."""
    findings = []
    if not source_file.exists():
        return [Finding(str(source_file), "does not exist")]
    if not fa_file.exists():
        return [Finding(str(fa_file), "does not exist")]

    fa_doc = _md.read(fa_file)
    if fa_doc.status == "untranslated":
        return []
    if is_skipped(fa_doc.body):
        return []

    try:
        offset = parse_offset(fa_doc.body)
    except ValueError as exc:
        return [Finding(str(fa_file), str(exc))]

    source_doc = _md.read(source_file)
    source_count = len(_md.iter_blocks(source_doc))
    fa_count = len(_md.iter_blocks(fa_doc))
    actual = fa_count - source_count
    if actual != offset:
        detail = f"{fa_count} blocks, source has {source_count}"
        if offset:
            detail += f" (offset {offset:+d} declared, actual {actual:+d})"
        findings.append(Finding(str(fa_file), detail))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true")
    parser.add_argument("files", nargs="*", type=Path, help="source and fa files to compare directly")
    parser.add_argument("--source", type=Path, default=REPO / "source")
    parser.add_argument("--fa", type=Path, default=REPO / "fa")
    parser.add_argument(
        "--exclude",
        nargs="*",
        help="source/ filenames with no translation to pair against "
        "(default: [tool.book] exclude in pyproject.toml)",
    )
    args = parser.parse_args(argv)

    if len(args.files) == 2:
        findings = compare_files(args.files[0], args.files[1])
        for finding in findings:
            print(finding)
        if findings:
            print(f"\n{len(findings)} parity problem(s)", file=sys.stderr)
            return 1
        print("parity: files match")
        return 0

    if not args.check:
        parser.error("give two files to compare, or --check to scan directories")

    if not args.source.is_dir():
        print(
            f"parity: skipped — {args.source}/ is not present.\n"
            "This is expected in CI: the source text is licensed to the maintainer "
            "for translation, not for redistribution. Run this locally."
        )
        return 0

    findings, compared, skipped = compare(
        args.source, args.fa, None if args.exclude is None else set(args.exclude)
    )

    for finding in findings:
        print(finding)

    if findings:
        print(f"\n{len(findings)} parity problem(s)", file=sys.stderr)
        return 1

    print(f"parity: {compared} file(s) match, {skipped} skipped (untranslated or exempt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
