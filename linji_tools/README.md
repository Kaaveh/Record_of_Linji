# linji-tools

Markdown checkers for a translation project: one tree of source files, one tree
of translations, and CI that has to notice when they drift apart.

```bash
python -m linji_tools.normalize --check          # orthography
python -m linji_tools.check_linebreaks --check   # one sentence per line
python -m linji_tools.check_parity --check       # no dropped paragraphs
python -m linji_tools.make_stubs                 # mirror source/ into the target tree
```

Every command runs against the current working directory and reads its
configuration from that project's `pyproject.toml`. Nothing is baked in — the
tests in `tests/` pass with no configuration present at all, which is the point
of keeping them here rather than folding them into `tools/`.

Not packaged. There is one consumer, and a package with one consumer is
machinery nobody is paying for. If a second project ever needs these, `git mv`
this directory out and package it then; nothing in here assumes it lives inside
this repository.

| Section | Read by | Holds |
|---|---|---|
| `[tool.book]` | parity, stubs, anchors | `exclude`, `titles` — data shared across checkers |
| `[tool.normalize]` | normalize | one toggle per orthography rule |
| `[tool.linebreaks]` | linebreaks | `abbreviations`, on top of a general English set |

## What each one catches

- **`normalize`** — Arabic Yeh/Kaf where Persian letters belong, ZWNJ
  discipline, Arabic-Indic digits, Tatweel, quotes, and bidi overrides. Bidi
  overrides are reported and never auto-fixed: they can make a diff render in a
  different order than it is stored, so a human has to look.
- **`check_linebreaks`** — more than one sentence on a line. A word-level diff
  of right-to-left text is unreadable, so the sentence has to be the unit of
  review.
- **`check_parity`** — a dropped paragraph, by block count against the source.
  Exits 0 with a notice when the source tree is absent, which is the normal
  state in CI for a text that is licensed rather than public.
- **`anchors`** — a library, not a command. Inline markup does not survive
  machine translation; it is deleted outright, silently. `strip` swaps every
  token for a sentinel the model does preserve, `restore` puts the tokens back
  where the sentinels landed, and a dropped or duplicated sentinel is refused
  rather than written out — quoting the source line it sat in, so a caller can
  put it back without diffing two whole files. Hard line breaks the model
  stripped are re-applied where the draft still lines up with the source, and
  listed for the caller where it does not. Supply your own token pattern and
  renderer; see the module docstring.

MIT licensed — see `LICENSE-CODE` at the repo root.
