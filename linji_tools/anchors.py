"""Carry inline markup across a machine translator, and verify it survived.

Machine translation does not mangle inline markup -- measured, it *deletes* it,
every token, silently, leaving prose that reads perfectly well with no trace
that a note was ever there. Restoring by position afterwards is impossible
because markers sit mid-sentence, not at paragraph ends.

What the model does preserve is bracketed numeric sentinels, in place, including
mid-sentence. Measured across six bracket styles: twelve sentinels in, twelve
out, all positioned correctly. So:

    strip   source.md                 > draft.en.md
    <translator on draft.en.md>       > draft.fa.md
    restore source.md draft.fa.md     > out.md

`strip` replaces every token with U+27E6..U+27E7 sentinels. `restore` puts the
tokens back where the model left the sentinels -- if the model moved a sentence,
its marker moves with it, which is what you want. Token text is re-emitted from
the source, never from the translation, so ids cannot drift.

Nothing here knows what a token looks like. Callers supply a compiled pattern
and a render function, which between them are the only markup-aware parts:

    strip(text, token_re, render)
    restore(name, source_text, draft, token_re, render)

`render(match)` returns the form the token should take in the translation, or
None to drop it. See the calling project's adapter for a worked example.

When the model drops one anyway, `restore` refuses and quotes the source line
that sentinel sat in, so the caller can put it back in the draft and run again
rather than diff two whole files to find where it belonged.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import regex

from . import _md

# U+27E6 / U+27E7. Exotic enough that a collision with the text is not a live
# worry, and preserved in place by the models measured. Any bracketed numeric
# form survives; verify absence from the source before trusting a new one.
SENTINEL = "⟦{}⟧"
SENTINEL_RE = regex.compile(r"⟦(\d+)⟧")

ANCHOR_ID = regex.compile(r'<a id="([^"]*)"></a>')
LINK_DEST = regex.compile(r"\]\(([^)]*)\)")


@dataclass(frozen=True)
class Finding:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def tokenize(text: str, token_re, render) -> tuple[str, list[str | None]]:
    """Returns (text with sentinels, replacement form of each token by index).

    `token_re` and `render` are the only things here that know what a token
    looks like or what it should become, which is what keeps the round-trip
    itself free of any knowledge of a particular text's markup.
    """
    out: list[str] = []
    forms: list[str | None] = []
    cursor = 0
    for match in token_re.finditer(text):
        out.append(text[cursor : match.start()])
        out.append(SENTINEL.format(len(forms) + 1))
        forms.append(render(match))
        cursor = match.end()
    out.append(text[cursor:])
    return "".join(out), forms


def strip(text: str, token_re, render) -> str:
    return tokenize(text, token_re, render)[0]


# How much of the source line to quote around a lost sentinel. Long enough to
# carry the clause it sits in, short enough that a file's worth of them is still
# cheaper to read than the two whole files.
WINDOW = 240


def repair_brief(stripped: str, ids) -> str:
    """The source line each of `ids` sits in, so a caller can place it by hand.

    Read off the sentinel form of the source, not the source itself, so the
    neighbouring sentinels come along in the quote and localise the missing one
    even when the line is repetitive. An id with no sentinel in the source -- an
    invented one -- has no line to quote and is skipped; the caller's message
    for that case already says everything there is to say.
    """
    lines = []
    for n in ids:
        index = stripped.find(SENTINEL.format(n))
        if index < 0:
            continue
        start = stripped.rfind("\n", 0, index) + 1
        end = stripped.find("\n", index)
        end = len(stripped) if end < 0 else end

        # Window on the sentinel, not on the line, so a marker late in a long
        # paragraph is not the part that gets elided.
        left = max(start, index - WINDOW // 2)
        right = min(end, index + WINDOW // 2)
        quote = ("…" if left > start else "") + stripped[left:right] + ("…" if right < end else "")
        lines.append(f"  ⟦{n}⟧  {quote}")
    return "\n".join(lines)


def align_hard_breaks(source_text: str, draft: str) -> tuple[str, str | None]:
    """Re-apply the source's hard line breaks to a draft the model stripped them from.

    Returns (draft, problem or None). The two trailing spaces are invisible, and
    losing them reflows a stanza of verse into a paragraph, so this is worth
    putting back rather than only counting.

    Positional, and only where that is provably safe: if the model kept the line
    count, source line i and draft line i are the same line and the break goes
    back on. If it did not, there is no alignment to trust, and the caller is
    told which lines to fix instead.
    """
    wanted = hard_breaks(source_text)
    if not wanted or hard_breaks(draft) == wanted:
        # Nothing to carry, or the breaks are already there -- the model kept
        # them, or a previous refusal was acted on. The second case is what lets
        # a hand-repaired draft pass on the next run instead of looping.
        return draft, None

    src_lines, draft_lines = source_text.split("\n"), draft.split("\n")
    if len(src_lines) != len(draft_lines):
        broken = [line for line in src_lines if line.endswith("  ") and line.strip()]
        return draft, (
            f"the model dropped {wanted - hard_breaks(draft)} hard line break(s) and "
            f"moved {len(draft_lines) - len(src_lines):+d} line(s), so they cannot be "
            "put back by position. End the matching draft line(s) with two spaces:\n"
            + "\n".join(f"  ␣␣  {line.strip()}" for line in broken)
        )

    for i, line in enumerate(src_lines):
        if line.endswith("  ") and line.strip() and draft_lines[i].strip():
            draft_lines[i] = draft_lines[i].rstrip() + "  "
    return "\n".join(draft_lines), None


def restore(name: str, source_text: str, draft: str, token_re, render) -> str:
    """Put the tokens back where the model left the sentinels.

    Returns the restored body. Refuses -- by raising -- rather than returning a
    damaged file: a dropped sentinel means a note has been lost, and writing
    that out is worse than failing. The refusal quotes the source line each lost
    sentinel sat in, which is what a caller needs to put it back.
    """
    stripped, forms = tokenize(source_text, token_re, render)
    draft, break_problem = align_hard_breaks(source_text, draft)

    seen = [int(m.group(1)) for m in SENTINEL_RE.finditer(draft)]
    expected = set(range(1, len(forms) + 1))
    missing = sorted(expected - set(seen))
    unknown = sorted(set(seen) - expected)
    duplicated = sorted({n for n in seen if seen.count(n) > 1})

    problems = []
    if missing:
        problems.append(f"the model dropped sentinel(s) {missing}")
    if unknown:
        problems.append(f"sentinel(s) {unknown} are not in source/{name}")
    if duplicated:
        problems.append(f"the model duplicated sentinel(s) {duplicated}")
    if break_problem:
        problems.append(break_problem)
    if problems:
        brief = repair_brief(stripped, missing + duplicated)
        raise ValueError(f"{name}: " + "; ".join(problems) + (f"\n{brief}" if brief else ""))

    return SENTINEL_RE.sub(lambda m: forms[int(m.group(1)) - 1] or "", draft)


def anchors_of(text: str) -> tuple[list[str], list[str]]:
    """The anchor ids and note-link destinations a file carries."""
    dests = [d for d in LINK_DEST.findall(text) if "#" in d]
    return sorted(ANCHOR_ID.findall(text)), sorted(dests)


def hard_breaks(text: str) -> int:
    """Lines ending in a Markdown hard line break (two trailing spaces).

    The model strips these. Lose them and a stanza of verse reflows into one
    paragraph, which reads as prose and is easy to miss in a diff. Putting them
    back needs the draft to line up with the source line for line, which is
    `align_hard_breaks`' job and is not always possible; this is the count both
    that and `compare` are measured against.
    """
    return sum(1 for line in text.split("\n") if line.endswith("  ") and line.strip())


def is_excluded(p_rel: Path, exclude_set) -> bool:
    rel_str = p_rel.as_posix()
    return (
        rel_str in exclude_set
        or p_rel.name in exclude_set
        or any(part in exclude_set for part in p_rel.parts)
    )


def compare(source_dir: Path, target_dir: Path, exclude=frozenset()) -> tuple[list[Finding], int, int]:
    """Check every translated file still carries the source's anchors.

    Returns (findings, compared, skipped).
    """
    findings: list[Finding] = []
    compared = skipped = 0

    names = {
        p.relative_to(source_dir).as_posix()
        for p in source_dir.rglob("*.md")
        if not is_excluded(p.relative_to(source_dir), set(exclude))
    }
    for name in sorted(names):
        target_path = target_dir / name
        if not target_path.exists():
            continue
        target_doc = _md.read(target_path)
        if target_doc.status == "untranslated":
            skipped += 1
            continue

        compared += 1
        label = f"{target_dir.name}/{name}"
        src_text = (source_dir / name).read_text(encoding="utf-8")
        target_text = target_path.read_text(encoding="utf-8")
        src_ids, src_dests = anchors_of(src_text)
        target_ids, target_dests = anchors_of(target_text)

        src_breaks, target_breaks = hard_breaks(src_text), hard_breaks(target_text)
        if target_breaks != src_breaks:
            findings.append(
                Finding(
                    label,
                    f"{target_breaks} hard line break(s), source has {src_breaks} — "
                    "verse will reflow into prose",
                )
            )

        if target_ids != src_ids:
            lost = sorted(set(src_ids) - set(target_ids))
            extra = sorted(set(target_ids) - set(src_ids))
            detail = f"{len(target_ids)} anchor id(s), source has {len(src_ids)}"
            if lost:
                detail += f"; missing {lost}"
            if extra:
                detail += f"; unexpected {extra}"
            findings.append(Finding(label, detail))
        if target_dests != src_dests:
            findings.append(
                Finding(
                    label,
                    f"{len(target_dests)} note link(s), source has {len(src_dests)}",
                )
            )

    return findings, compared, skipped


def main(
    argv: list[str] | None,
    *,
    strip_text,
    restore_text,
    source_default: Path,
    target_default: Path,
    exclude=frozenset(),
    description: str | None = None,
) -> int:
    """The strip/restore/--check command line.

    `strip_text(name, text)` and `restore_text(name, source_text, draft)` are
    the caller's, and are where all knowledge of the markup lives. Everything
    here is the shell around them: argument parsing, the absent-source notice,
    and the write-only-if-valid discipline on -o.
    """
    parser = argparse.ArgumentParser(
        description=description or __doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("mode", nargs="?", choices=["strip", "restore"])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        help="write here, and only if validation passed. Prefer this to a shell "
        "redirect: `> out.md` truncates the file before the tool runs, so a "
        "draft this correctly refuses destroys the previous translation.",
    )
    parser.add_argument("--source", type=Path, default=source_default)
    parser.add_argument("--fa", type=Path, default=target_default, dest="target")
    args = parser.parse_args(argv)

    if args.check:
        if not args.source.is_dir():
            print(
                f"anchors: skipped — {args.source}/ is not present.\n"
                "This is expected where the source text is not redistributable. "
                "Run this locally."
            )
            return 0
        findings, compared, skipped = compare(args.source, args.target, exclude)
        for finding in findings:
            print(finding)
        if findings:
            print(f"\n{len(findings)} anchor problem(s)", file=sys.stderr)
            return 1
        print(f"anchors: {compared} file(s) match, {skipped} skipped (untranslated)")
        return 0

    if not args.mode:
        parser.error("give a mode (strip/restore) or --check")

    try:
        source = args.files[0]
        text = source.read_text(encoding="utf-8")
        if args.mode == "strip":
            result = strip_text(source.name, text)
        else:
            draft = args.files[1].read_text(encoding="utf-8")
            result = restore_text(source.name, text, draft)
        # Only now, with validation behind us, is anything written.
        if args.out:
            args.out.write_text(result, encoding="utf-8")
        else:
            sys.stdout.write(result)
    except IndexError:
        parser.error(f"{args.mode} needs {'SOURCE' if args.mode == 'strip' else 'SOURCE DRAFT'}")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
