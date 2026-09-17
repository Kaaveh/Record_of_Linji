"""Mirror source/ into fa/ as translation stubs.

Filenames must match byte-for-byte across the two trees -- check_parity.py
pairs files by name, so any drift silently disables parity checking for the
affected chapter. This script is the only thing that should create fa/ files,
and it derives every name from source/ rather than from a count, so the two
trees cannot fall out of step.

Usage:
    tools/make_stubs.py                 # create missing fa/ stubs
    tools/make_stubs.py --force         # also overwrite existing stubs
    tools/make_stubs.py --titles t.tsv  # supply Persian headings

Existing files are never overwritten without --force, so re-running after
translation has started cannot destroy work. Orphans (files in fa/ with no
counterpart in source/) are reported but never deleted.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


from . import _md
from ._md import to_persian_digits

REPO = _md.REPO

# source/ files that get no translation stub -- for this book, the maintainer's
# own index and provenance note. From [tool.book] exclude, the same list
# check_parity.py and anchors.py pair files against.
DEFAULT_EXCLUDE = set(_md.config("book").get("exclude", []))

# Placeholder headings for the non-numbered files, from [tool.book.titles] in
# pyproject.toml. The translator replaces them on first pass; --titles
# overrides them for one run.
DEFAULT_TITLES = _md.config("book").get("titles", {})


def heading_for(name: str, titles: dict[str, str]) -> str:
    """Placeholder heading for a stub, by filename."""
    if name in titles:
        return titles[name]
    p = Path(name)
    if p.name in titles:
        return titles[p.name]
    stem = p.stem
    if stem.isdigit():
        return to_persian_digits(int(stem))
    if stem in titles:
        return titles[stem]
    return stem


def fa_stub(name: str, titles: dict[str, str]) -> str:
    return (
        "---\n"
        "status: untranslated\n"
        "---\n"
        "\n"
        f"# {heading_for(name, titles)}\n"
        "\n"
        "<!-- TODO: translate -->\n"
    )


def is_excluded(rel: Path, exclude: set[str]) -> bool:
    rel_str = rel.as_posix()
    return (
        rel_str in exclude
        or rel.name in exclude
        or any(part in exclude for part in rel.parts)
    )


def source_names(source: Path, exclude: set[str]) -> list[str]:
    if not source.is_dir():
        raise FileNotFoundError(f"{source} does not exist")
    names = [
        p.relative_to(source).as_posix()
        for p in source.rglob("*.md")
        if not is_excluded(p.relative_to(source), exclude)
    ]
    # Sort order: directories in order, then numbered sections numerically, then named files
    def sort_key(n: str):
        p = Path(n)
        stem = p.stem
        is_num = stem.isdigit()
        num_val = int(stem) if is_num else 0
        return (p.parent.as_posix(), not is_num, num_val, p.name)

    return sorted(names, key=sort_key)


def load_titles(path: Path | None, base: dict[str, str] | None = None) -> dict[str, str]:
    """The title table, from `base` (default: config) overlaid with a TSV."""
    titles = dict(DEFAULT_TITLES if base is None else base)
    if path:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, _, title = line.partition("\t")
            if not title:
                raise ValueError(f"expected 'filename<TAB>title', got: {line!r}")
            titles[name.strip()] = title.strip()
    return titles


def sync(source: Path, target: Path, titles: dict[str, str], exclude: set[str], force: bool):
    """Returns (written, skipped, orphans)."""
    names = source_names(source, exclude)
    target.mkdir(parents=True, exist_ok=True)

    written = skipped = 0
    for name in names:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not force:
            skipped += 1
            continue
        path.write_text(fa_stub(name, titles), encoding="utf-8")
        written += 1

    expected = set(names)
    target_files = [p.relative_to(target).as_posix() for p in target.rglob("*.md")]
    orphans = sorted(f for f in target_files if f not in expected)
    return written, skipped, orphans


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--source", type=Path, default=REPO / "source")
    parser.add_argument("--target", type=Path, default=REPO / "fa")
    parser.add_argument("--titles", type=Path, help="TSV of 'filename<TAB>Persian heading'")
    parser.add_argument("--exclude", nargs="*", default=sorted(DEFAULT_EXCLUDE))
    parser.add_argument("--force", action="store_true", help="overwrite existing stubs")
    args = parser.parse_args(argv)

    try:
        titles = load_titles(args.titles)
        written, skipped, orphans = sync(
            args.source, args.target, titles, set(args.exclude), args.force
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote {written} stub(s), skipped {skipped} existing")
    if orphans:
        print(
            f"\n{len(orphans)} file(s) in {args.target}/ have no counterpart in {args.source}/:",
            file=sys.stderr,
        )
        for name in orphans:
            print(f"  {name}", file=sys.stderr)
        print("parity cannot check these. Rename or remove them.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
