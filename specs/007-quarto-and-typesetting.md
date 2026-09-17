# 007 — Quarto Typesetting, Typography & Publication

**Scope**: Quarto configuration (`_quarto.yml`), TeX preamble, RTL typography, and multi-format publishing  
**Depends on**: [`002-pilot-discourses.md`](./002-pilot-discourses.md) through [`006-scholarly-matter.md`](./006-scholarly-matter.md)

---

## Context & Key Findings from Reference Project

In the previous project ([`The Zen Teachings of Master Lin-chi`](file:///Users/kaavehmohamedi/Project/Books/The%20Zen%20Teachings%20of%20Master%20Lin-chi)), several critical typographic and technical decisions were established by experiment:

1. **LuaLaTeX Over XeLaTeX**:
   Under XeLaTeX, Babel's `bidi=default` reverses embedded Latin-script runs (such as Sanskrit diacritics or English transliterations) inside Persian text. LuaLaTeX (`pdf-engine: lualatex` with `bidi=basic`) handles bidirectional embedding correctly and produces flawless mixed Persian/English/Chinese typography.
2. **Font Selection**:
   - Primary Persian body font: **Vazirmatn** (وزیرمتن) — clean modern Naskh with full glyph support and OpenType features.
   - Chinese characters in commentary: **Noto Serif CJK SC** / **Noto Sans CJK SC**.
   - Latin serif font: **Libertinus Serif** or **Charis SIL** (full Unicode support for Sanskrit diacritics like *śāstra*, *nirmāṇakāya*).
3. **Quarto Chapter Mapping**:
   `_quarto.yml` organizes the chapters under `part:` headings so Quarto generates genuine part-title separator pages in the PDF and collapsible sidebar groups in HTML:
   - Part: پیش‌گفتارها (Front matter)
   - Part: دفتر یکم: گفتارها (Discourses)
   - Part: دفتر دوم: سنجش‌های موشکافانه (Critical Examinations)
   - Part: دفتر سوم: کارنامهٔ سفرها (Record of Pilgrimages)
   - Part: درآمد تاریخی (Historical Introduction)
   - Part: متن کهن چینی و مراجع (Chinese Text & References)

---

## Deliverables

### 1. Quarto Configuration Files
- `_quarto.yml`: Root project configuration for HTML, PDF, and EPUB.
- `_quarto-mobile.yml`: Optimized PDF layout for smartphones and e-readers.
- `_language.yml`: Persian localization strings for Quarto UI (e.g. فهرست, فصل, بعدی, قبلی).

### 2. TeX Preamble & Typography
- `tex/preamble.tex`: Babel/LuaLaTeX bidirectional settings, line-spacing, footnote rules mirrored to right margin, and header/footer definitions.
- `tex/title.tex`: Typeset Persian title page featuring Calligraphy, Author, Translator, and Publisher credits.

### 3. Build Automation
- Create a `justfile` providing standard targets:
  ```bash
  just build          # Build HTML, PDF, EPUB via Quarto
  just pdf            # Render PDF with LuaLaTeX
  just serve          # Start Quarto local live preview server
  just check          # Run linji_tools orthography, linebreaks, and parity checks
  ```

---

## Acceptance Criteria

- [ ] `_quarto.yml` includes all translated files in `fa/`.
- [ ] HTML output renders with proper RTL layout, functional sidebar, and search.
- [ ] PDF compiles cleanly with LuaLaTeX with zero font errors or reversed Latin runs.
- [ ] EPUB generated and validates without broken links.
