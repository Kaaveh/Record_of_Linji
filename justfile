# Task runner for Record of Linji (Farsi Translation)

# Prefer the project venv on the host; fall back to whatever python3 is around.
py := if path_exists(".venv/bin/python") == "true" { ".venv/bin/python" } else { "python3" }

_default:
    @just --list

# Everything CI runs on a pull request / release.
check:
    {{py}} -m linji_tools.check_parity --check
    {{py}} -m linji_tools.normalize --check
    {{py}} -m linji_tools.check_linebreaks --check

# Automatically fix orthography and linebreaks where possible.
fix:
    {{py}} -m linji_tools.normalize --fix
    {{py}} -m linji_tools.check_linebreaks --fix

# HTML, PDF and EPUB via Quarto.
build:
    quarto render

# Render PDF with LuaLaTeX.
pdf:
    quarto render --to pdf

# The mobile phone edition: 90x160mm page for comfortable phone reading.
pdf-mobile:
    quarto render --profile mobile --to pdf

# Render HTML website edition.
html:
    quarto render --to html

# Render EPUB edition.
epub:
    quarto render --to epub

# Start Quarto local live preview server (http://localhost:4200).
serve:
    quarto preview --port 4200

# Host-side Python environment.
venv:
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r tools/requirements.txt

# Clean build artifacts.
clean:
    rm -rf _book _book-mobile .quarto
