"""Checkers for a Markdown translation project.

Six checkers and a markup round-trip, none of which know which book they are
being run against. What makes them specific to a project is that project's
`pyproject.toml`: see `_md.config()` and the `[tool.*]` sections it reads.

    python -m linji_tools.normalize --check
    python -m linji_tools.check_linebreaks --check
    python -m linji_tools.check_parity --check
    python -m linji_tools.make_stubs

Run from the project root; every command works on the current directory.

`anchors` is a library rather than a command: the markup round-trip needs a
token pattern and a renderer from the caller, so each project wraps it in a
small adapter of its own. This one's is `tools/anchors.py`.

Kept importable from the tree rather than installed. There is one consumer, and
a package with one consumer is machinery nobody is paying for. If a second
project ever needs these, `git mv` this directory out and package it then --
nothing here assumes it lives inside this repository.
"""
