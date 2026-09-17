"""Shared helpers for the checkers in tools/.

This is deliberately not a Markdown parser. It is the smallest amount of
structure the four checkers need in common:

  * YAML front matter, split off with its line offset kept
  * blank-line-delimited blocks, aware of fenced code
  * "protected" spans that no rule may rewrite
  * <!-- name: value --> directives
  * the [tool.*] tables in pyproject.toml, and Persian digits

The protected-span logic matters more here than in most projects. This book's
notes are inline HTML anchors -- <a id="m39-1"></a>[<sup>1</sup>](#n39-1) --
so a naive orthography pass would happily rewrite an anchor id or a link
destination and silently break 506 cross-references.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

import regex
import yaml

# Installed code has no repository above it: the project being checked is
# whatever directory the tool was run from. Bound at import, which is correct
# for a command-line run and the only way this is used.
# ponytail: import-time cwd. Pass an explicit path if you ever need to chdir.
REPO = Path.cwd()

ZWNJ = "‌"

PERSIAN_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Spans no rule may touch. Order is precedence: the scanner takes the leftmost
# match, and among alternatives at the same position, the first listed wins.
# Indented (4-space) code blocks are NOT protected -- they are ambiguous with
# list continuation lines, and this book uses fenced blocks. Use a fence.
PROTECTED = regex.compile(
    r"""
      (?P<fence>^(?P<f>```|~~~).*?^(?P=f)[^\n]*$)   # fenced code block
    | (?P<comment><!--.*?-->)                        # HTML comment
    | (?P<code>`+[^`]*`+)                            # inline code span
    | (?P<tag></?[A-Za-z][^<>]*>)                    # HTML tag
    | (?P<dest>\]\([^)]*\))                          # link / image destination
    | (?P<math>\$\$.*?\$\$|\$[^$\n]+\$)              # math
    """,
    regex.VERBOSE | regex.DOTALL | regex.MULTILINE,
)

DIRECTIVE = regex.compile(r"<!--\s*(?P<name>[a-z_]+)\s*:\s*(?P<value>[^>]*?)\s*-->")

# A block that is nothing but HTML comments is metadata -- a directive, or a
# TODO marker. It renders as nothing, so it must not count towards parity.
COMMENT_ONLY = regex.compile(r"^(?:\s*<!--.*?-->\s*)+$", regex.DOTALL)

FENCE_OPEN = regex.compile(r"^\s{0,3}(```|~~~)")
LIST_ITEM = regex.compile(r"^\s{0,3}([-*+]|\d{1,9}[.)])\s")


@dataclass(frozen=True)
class Block:
    kind: str
    line: int  # 1-based, in the original file
    text: str


@dataclass(frozen=True)
class Document:
    path: str
    front: dict
    body: str
    body_line: int  # 1-based line of the first body line in the original file
    prefix: str = ""  # raw front matter, so a rewrite can restore it verbatim

    @property
    def status(self) -> str | None:
        value = self.front.get("status")
        return str(value) if value is not None else None

    def line_kinds(self) -> dict[int, str]:
        """Map every body line number to the kind of block it sits in."""
        kinds: dict[int, str] = {}
        for block in iter_blocks(self):
            for offset in range(block.text.count("\n") + 1):
                kinds[block.line + offset] = block.kind
        return kinds


def parse(path, text: str) -> Document:
    """Split YAML front matter from the body, keeping the line offset."""
    front: dict = {}
    body = text
    body_line = 1
    prefix = ""

    if text.startswith("---\n"):
        end = text.find("\n---", 3)
        if end != -1:
            raw = text[4:end]
            after = text.index("\n", end + 1) + 1 if "\n" in text[end + 1 :] else len(text)
            try:
                loaded = yaml.safe_load(raw)
            except yaml.YAMLError:
                loaded = None
            if isinstance(loaded, dict):
                front = loaded
                prefix = text[:after]
                body = text[after:]
                body_line = prefix.count("\n") + 1

    return Document(path=str(path), front=front, body=body, body_line=body_line, prefix=prefix)


def iter_blocks(doc: Document) -> list[Block]:
    """Blank-line-delimited blocks, with fenced code held together.

    This counts what a reviewer would call a paragraph, not what CommonMark
    calls a block. A loose list counts as one block per item. That is fine for
    parity, which compares like against like -- but it does mean a tight list
    on one side and a loose list on the other is a real reported difference.
    """
    blocks: list[Block] = []
    current: list[str] = []
    start = 0
    fence: str | None = None

    lines = doc.body.split("\n")

    def flush():
        nonlocal current, start
        if current:
            text = "\n".join(current).strip("\n")
            if text.strip() and not COMMENT_ONLY.match(text):
                blocks.append(Block(kind=classify(text), line=doc.body_line + start, text=text))
        current = []

    for index, line in enumerate(lines):
        if fence is None:
            match = FENCE_OPEN.match(line)
            if match:
                flush()
                start = index
                fence = match.group(1)
                current = [line]
                continue
            if not line.strip():
                flush()
                continue
            if not current:
                start = index
            current.append(line)
        else:
            current.append(line)
            if line.strip().startswith(fence):
                flush()
                fence = None

    flush()
    return blocks


# Tags that can open a run of ordinary prose. A block starting with one of
# these is a paragraph, not an HTML block -- every note in this book opens with
# <a id="n39-1"></a> and its text still has to be spell-checked and line-broken
# like any other sentence.
INLINE_TAGS = frozenset(
    "a abbr b br cite code em i img q s small span strong sub sup u".split()
)

TAG_NAME = regex.compile(r"^</?([A-Za-z][A-Za-z0-9]*)")


def classify(text: str) -> str:
    first = text.lstrip().split("\n", 1)[0]
    if first.startswith("#"):
        return "heading"
    if FENCE_OPEN.match(first):
        return "code"
    if first.startswith(">"):
        return "blockquote"
    if LIST_ITEM.match(first):
        return "list"
    if first.startswith("|"):
        return "table"
    if first.startswith("<"):
        match = TAG_NAME.match(first)
        if not match or match.group(1).lower() not in INLINE_TAGS:
            return "html"
    return "paragraph"


def directives(text: str, name: str) -> list[str]:
    """Values of every <!-- name: value --> directive, in order."""
    return [m.group("value") for m in DIRECTIVE.finditer(text) if m.group("name") == name]


def protected_spans(text: str) -> list[tuple[int, int]]:
    return [m.span() for m in PROTECTED.finditer(text)]


def apply_outside_protected(text: str, func) -> str:
    """Run `func` over every stretch of `text` that is not a protected span."""
    out = []
    cursor = 0
    for start, end in protected_spans(text):
        if start > cursor:
            out.append(func(text[cursor:start]))
        out.append(text[start:end])
        cursor = end
    out.append(func(text[cursor:]))
    return "".join(out)


def toggle_regions(text: str, name: str) -> list[tuple[int, int]]:
    """Character spans disabled by <!-- name: off --> ... <!-- name: on -->.

    An unclosed `off` disables everything to end of file, which is the safe
    reading: the author asked for hands off and never took it back.
    """
    spans = []
    off_at: int | None = None
    for match in DIRECTIVE.finditer(text):
        if match.group("name") != name:
            continue
        value = match.group("value").strip()
        if value == "off" and off_at is None:
            off_at = match.start()
        elif value == "on" and off_at is not None:
            spans.append((off_at, match.end()))
            off_at = None
    if off_at is not None:
        spans.append((off_at, len(text)))
    return spans


def line_of(text: str, offset: int, base: int = 1) -> int:
    return base + text.count("\n", 0, offset)


def read(path) -> Document:
    p = Path(path)
    return parse(p, p.read_text(encoding="utf-8"))


def to_persian_digits(value: str | int) -> str:
    return str(value).translate(PERSIAN_DIGITS)


def config(section: str, path: Path | None = None) -> dict:
    """The [tool.<section>] table from pyproject.toml, or {} if it is absent.

    Project data that a checker needs but should not contain lives there, so
    that the checker stays a checker. [tool.normalize] is the older example.
    """
    path = path or Path.cwd() / "pyproject.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        return tomllib.load(handle).get("tool", {}).get(section, {})
