# 000 — Project Overview & Shared Context

> 📖 Reference document — shared foundation for all specs in this project.

## 1. What This Project Is

A comprehensive Persian translation of **_The Record of Linji_** (*Linji lu* 臨濟錄) based on the definitive scholarly translation and commentary by **Ruth Fuller Sasaki**, edited by **Thomas Yūhō Kirchner** (Nanzan Library of Asian Religion and Culture / University of Hawai‘i Press).

This edition is substantially richer and more scholarly than earlier versions:
- It provides Ruth Fuller Sasaki's meticulous English rendering of the Tang-dynasty sayings and encounter dialogues.
- It integrates the extensive phrase-by-phrase **Commentary** (incorporating research by Yanagida Seizan and Iriya Yoshitaka).
- It provides the original Chinese text collated from the *Taishō Tripiṭaka*.
- It features an in-depth Historical Introduction by Yanagida Seizan.

## 2. Directory Architecture

The Persian edition strictly mirrors the modular directory structure in `source/`:

```text
Record_of_Linji/
├── source/                            # [GITIGNORED] English source & commentary
│   ├── 00-front-matter/               # 5 files (foreword, prefaces, prologue, abbreviations, title)
│   ├── 01-discourses/                 # 22 files (01.md to 22.md)
│   ├── 02-critical-examinations/      # 24 files (23.md to 46.md)
│   ├── 03-record-of-pilgrimages/      # 23 files (47.md to 68.md + 69-ma-fang-preface.md)
│   ├── 04-historical-introduction/    # 1 file (Yanagida Seizan)
│   ├── 05-chinese-text/               # 3 files (Chinese original)
│   └── 06-reference-matter/           # 3 files (bibliography, personal names, index)
├── fa/                                # [TRACKED] Persian translations mirroring source/
│   ├── 00-front-matter/
│   ├── 01-discourses/
│   ├── 02-critical-examinations/
│   ├── 03-record-of-pilgrimages/
│   ├── 04-historical-introduction/
│   └── 06-reference-matter/
├── tools/                             # Automation adapters, pre/post-processors
├── specs/                             # Engineering and translation specifications
└── split_transcript.py                # Source splitting generator
```

## 3. Hard Constraints

1. **Source Text Must Remain Gitignored**:
   The English translation and commentary by Sasaki & Kirchner are under copyright. Neither `source/` nor the raw `.md`/`.pdf`/`.xml` source files may ever be committed to the git repository.

2. **One Sentence Per Line in `fa/`**:
   Git diffs right-to-left Persian text poorly when multiple sentences wrap onto single lines. To ensure clean, reviewable line diffs, every sentence in the Persian translation must terminate with a newline.

3. **Translation Engine Quality**:
   All machine-assisted translation drafts must be generated using `gTranslator` with the `--web` (`-w`) flag to access Google's **Advanced (Gemini)** model. Standard API endpoints or Classic NMT engines must not be used.

4. **Section File Structure Integrity**:
   Each numbered section file in `01-discourses/`, `02-critical-examinations/`, and `03-record-of-pilgrimages/` pairs the core passage translation with its corresponding scholarly commentary separated by a `---` and `## Commentary` heading. This structure must be preserved across `fa/`.

5. **Orthography Standards**:
   - Standard Persian Yeh (`ی`, `\u06CC`) and Keheh (`ک`, `\u06A9`) — no Arabic `ي` or `ك`.
   - Proper zero-width non-joiner (نیم‌فاصله `\u200C`) for prefixes (`می‌`, `نمی‌`) and suffixes (`‌ها`, `‌های`, `تر`).
   - Persian digits (`۰`–`۹`) in body text, headings, and note references.
   - Quotation marks: standard guillemets (« ») for dialogue and cited terms.
