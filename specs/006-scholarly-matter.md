# 006 — Historical Introduction & Reference Matter

**Scope**:
- `source/04-historical-introduction/` (1 file: `historical-introduction.md`)
- `source/05-chinese-text/` (3 files: `discourses.md`, `critical-examinations.md`, `record-of-pilgrimages.md`)
- `source/06-reference-matter/` (3 files: `bibliography.md`, `personal-names.md`, `index.md`)  
**Scale**: ~83,000 words total  
**Depends on**: [`001-translation-pipeline.md`](./001-translation-pipeline.md) through [`004-record-of-pilgrimages.md`](./004-record-of-pilgrimages.md)

---

## Context

This specification addresses the major scholarly apparatus compiled by **Yanagida Seizan (柳田聖山)** and the Ryōsen-an research team:

### 1. Historical Introduction (`04-historical-introduction/historical-introduction.md`)
Authored by Prof. Yanagida Seizan, the foremost 20th-century authority on Chan historiography:
- Traces the historical evolution of the *Recorded Sayings* (*yulu* 語錄) genre.
- Analyzes Tang-dynasty Chan in Hebei under warlord governors (fanzhen).
- Examines the lineage from Huineng to Mazu, Baizhang, Huangbo, and Linji.
- Textual history of early manuscript fragments up to the 1120 edition.

### 2. Chinese Original Text (`05-chinese-text/`)
- Collated from *Taishō Tripiṭaka* Vol. 47 (No. 1985) and the *Xu Guzunsu Yuyao*.
- Serves as the primary textual baseline. In the Persian edition, this can be presented side-by-side or as a bilingual appendix.

### 3. Reference Matter (`06-reference-matter/`)
- **`bibliography.md`**: Detailed encyclopedic entries on dozens of canonical Mahāyāna sutras and classic Chan texts (*Baizhang qinggui*, *Biyan lu*, *Zhaolun*, etc.).
- **`personal-names.md`**: Biographical directory of all historical figures, buddhas, patriarchs, and monastics cited in the book.
- **`index.md`**: Subject and term index.

---

## Technical Strategy

- Because `historical-introduction.md` is ~38,000 words, `gTranslator` will process it in natural thematic sections (chunked around its subheadings) to prevent browser timeout.
- The `bibliography.md` and `personal-names.md` entries contain thousands of Chinese and Sanskrit titles. Sentinels must protect foreign script tokens while allowing descriptive commentary to be translated cleanly.

---

## Checklist

- [x] `04-historical-introduction/historical-introduction.md` — Complete Persian translation of Yanagida Seizan's introduction
- [x] `05-chinese-text/` — Integrate / verify original Chinese texts for Quarto build
- [x] `06-reference-matter/bibliography.md` — Translate encyclopedic bibliography
- [x] `06-reference-matter/personal-names.md` — Translate personal names directory
- [x] `06-reference-matter/index.md` — Localize index terms
