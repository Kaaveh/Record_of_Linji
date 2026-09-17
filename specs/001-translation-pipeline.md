# 001 — Translation Pipeline & `gTranslator` Engine Integration

## Context

All automated drafting for this book relies on the private translator service located at:
`/Users/kaavehmohamedi/Project/Backend/gTranslator`

This document details the internal mechanism of `gTranslator`, the critical requirements for running it safely, and the pre/post-processing apparatus needed for *The Record of Linji*.

---

## 1. `gTranslator` Mechanism & Findings

### The Two Google Models
Google Translate runs two distinct translation engines:
1. **Classic (NMT)**: The older neural machine translation model. It translates clause-by-clause, lacks literary register, and struggles with philosophical and classical terminology.
2. **Advanced (Gemini)**: *"Improved accuracy, built with Gemini."* It processes full paragraphs, restructures Persian sentences naturally, inserts correct ezafe markers, and handles nuance.

### The Headless Detection Gate
- **No public or cloud API serves the Advanced model.** Both `translate_a` and the official Cloud Translation API v2 serve only the Classic model.
- Google serves the Classic model to any browser whose User-Agent contains `HeadlessChrome`.
- `gtranslate.py` bypasses this by launching a real Chrome browser instance via Playwright with a spoofed standard macOS Chrome User-Agent:
  ```python
  UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
  ```
- **Silent Failure Warning**: If the User-Agent leaks, Google Translate silently serves Classic while the model picker in the UI still reports "Advanced". Always inspect the Persian output rather than relying on the UI picker.

### Command Line Invocation
The tool must be executed using its dedicated virtual environment:
```bash
GT=/Users/kaavehmohamedi/Project/Backend/gTranslator
"$GT/.venv/bin/python" "$GT/gtranslate.py" -f input.en.md -t fa -w --raw -o output.fa.md
```
- `-w` (`--web`): Mandatory. Drives the headless browser to access the Advanced (Gemini) model.
- `--raw`: Mandatory. Preserves line breaks as-is instead of stripping them.

### Input Constraints & Chunking
- Google's web client caps input at 5,000 characters.
- `gtranslate.py` automatically splits larger texts into chunks of at most 4,500 characters using paragraph boundaries (`\n\n`), line breaks (`\n`), and sentence ends.
- However, for large Commentary sections containing mixed English and Chinese, feeding whole files directly into `gTranslator` will cause Google Translate to attempt translating Classical Chinese characters into Persian, often resulting in garbled text.

---

## 2. Protection of Markup, Chinese Text, and Footnotes

### The Problem
Google's Advanced model cleanly *deletes* inline HTML markup (`<a id="...">`), Markdown footnotes (`[^1]`), and sometimes corrupts Classical Chinese quotes embedded in English commentary.

### The Solution: Strip & Restore Pipeline
Before sending text to `gTranslator`:
1. **Chinese Block Protection**:
   In Commentary sections, Classical Chinese text blocks must be replaced with numeric sentinels (e.g. `⟦CHINESE_01⟧`). Google Translate faithfully carries bracketed tokens like `⟦...⟧` through translation without alteration.
2. **Footnote & Anchor Protection**:
   Replace footnote references `[^n]` with `⟦n⟧`.
3. **Heading Protection**:
   Structural headings (`### Discourse I`, `## Commentary`, `#### Commentary Section I`) are replaced with standard sentinels so Google Translate does not translate them erratically.
4. **Post-Translation Restoration**:
   After `gTranslator` returns the Persian draft, the restoration step swaps `⟦CHINESE_01⟧` back into place, converts `⟦n⟧` to Persian superscripts (`[^۱^]`), and restores structural Persian headings (`# گفتار ۱`, `## شرح`, etc.).

---

## 3. End-to-End Pipeline Loop

For each section file (e.g., `source/01-discourses/01.md`):

```bash
# 1. Strip and replace protected tokens with sentinels
python3 tools/anchors.py strip source/01-discourses/01.md -o /tmp/01.en.md

# 2. Run gTranslator with Advanced Gemini model
/Users/kaavehmohamedi/Project/Backend/gTranslator/.venv/bin/python \
    /Users/kaavehmohamedi/Project/Backend/gTranslator/gtranslate.py \
    -f /tmp/01.en.md -t fa -w --raw -o /tmp/01.fa.md

# 3. Restore protected tokens, Chinese blocks, and Persian headings
python3 tools/anchors.py restore source/01-discourses/01.md /tmp/01.fa.md -o fa/01-discourses/01.md

# 4. Orthographic normalization and semantic line breaks
python3 -m linji_tools.normalize fa/01-discourses/01.md --fix
python3 -m linji_tools.check_linebreaks fa/01-discourses/01.md --fix

# 5. Verify parity
python3 -m linji_tools.check_parity source/01-discourses/01.md fa/01-discourses/01.md
```

---

## 4. Requirements & Deliverables

- [ ] Port/adapt `tools/anchors.py` and `linji_tools` from `/Users/kaavehmohamedi/Project/Books/The Zen Teachings of Master Lin-chi` to support subdirectories and Chinese text block masking.
- [ ] Verify test execution of a single sample section end-to-end.
