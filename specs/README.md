# Specs Roadmap — The Record of Linji (Farsi Translation)

This directory contains the engineering and editorial specifications for translating **_The Record of Linji_** (Ruth Fuller Sasaki translation, edited by Thomas Yūhō Kirchner) into Persian.

Shared context and hard constraints: [`000-overview.md`](./000-overview.md).  
Translation pipeline and `gTranslator` integration: [`001-translation-pipeline.md`](./001-translation-pipeline.md).

---

## Status Table

| # | Spec | Scope | Depends On | Status |
|---|---|---|---|---|
| 000 | [Overview & Shared Context](./000-overview.md) | Project architecture, constraints, directories | — | 📖 Reference |
| 001 | [Translation Pipeline & Engine](./001-translation-pipeline.md) | `gTranslator` integration, sentinels, normalizer | — | 🟨 Ready |
| 002 | [Part One: Discourses (Pilot)](./002-pilot-discourses.md) | `01-discourses/` (22 sections: `01.md`–`22.md`) | 001 | ✅ Complete |
| 003 | [Part Two: Critical Examinations](./003-critical-examinations.md) | `02-critical-examinations/` (24 sections: `23.md`–`46.md`) | 001, 002 | ⬜ Planned |
| 004 | [Part Three: Record of Pilgrimages](./004-record-of-pilgrimages.md) | `03-record-of-pilgrimages/` (23 sections: `47.md`–`68.md` + `69-ma-fang-preface.md`) | 001, 002 | ⬜ Planned |
| 005 | [Front Matter](./005-front-matter.md) | `00-front-matter/` (5 files) | 001, 002 | ⬜ Planned |
| 006 | [Historical Introduction & Reference](./006-scholarly-matter.md) | `04-historical-introduction/`, `05-chinese-text/`, `06-reference-matter/` | 001–004 | ⬜ Planned |
| 007 | [Quarto Typesetting & Publication](./007-quarto-and-typesetting.md) | Quarto build, LuaLaTeX RTL typography, HTML/PDF/EPUB | 002–006 | ⬜ Planned |

---

## Recommended Execution Order

```
001 (Pipeline) → 002 (Discourses / Pilot) → 003 (Critical Examinations) → 004 (Pilgrimages) → 005 (Front Matter) → 006 (Scholarly Intro) → 007 (Publish)
```

1. **Spec 001 (Pipeline)** establishes the mechanical bridge between `source/`, `gTranslator`, and `fa/`.
2. **Spec 002 (Discourses)** is the pilot. 22 discourses containing Linji's central sermons and doctrine. Establishes the foundational Persian Buddhist vocabulary.
3. **Spec 003 (Critical Examinations)** covers 24 fast-paced encounter dialogues, shouts, and blows. Rapid, colloquial exchanges.
4. **Spec 004 (Record of Pilgrimages)** covers 22 biographical and historical episodes, the stupa inscription, and Ma Fang's preface.
5. **Spec 005 (Front Matter)** covers the modern prefaces (Yamada Mumon, Furuta Kazuhiro, Kirchner). Done after the core text so terminology is settled.
6. **Spec 006 (Scholarly Matter)** covers Yanagida Seizan's extensive historical introduction, Chinese text, and reference index.
7. **Spec 007 (Quarto Typesetting)** sets up LuaLaTeX bidi typesetting with Vazirmatn font and multi-format publication.

---

## Scale Overview

| Group | Files | Translation Words | Commentary Words | Total Source Units |
|---|---|---|---|---|
| `00-front-matter/` | 5 | ~14,000 | — | 5 |
| `01-discourses/` | 22 | ~24,000 | ~110,000 | 22 |
| `02-critical-examinations/` | 24 | ~6,500 | ~35,000 | 24 |
| `03-record-of-pilgrimages/` | 23 | ~8,500 | ~40,000 | 23 |
| `04-historical-introduction/` | 1 | ~38,000 | — | 1 |
| `05-chinese-text/` | 3 | — (Classical Chinese) | — | 3 |
| `06-reference-matter/` | 3 | ~45,000 | — | 3 |
| **Total** | **81** | **~131,000** | **~185,000** | **81** |

---

## Definition of Done (Every Spec)

- [ ] All target files created under `fa/<subdirectory>/` mirroring `source/<subdirectory>/`.
- [ ] Translation produced via `gTranslator` with `--web --raw` (Advanced Gemini model).
- [ ] Note anchors and Chinese text preserved without deletion or corruption.
- [ ] Persian text conforms to orthographic rules (half-spaces, proper `ی` and `ک`, Persian digits).
- [ ] One sentence per line enforced across all translated files.
- [ ] Parity between source and translated blocks verified.
- [ ] Spec status updated in this table upon completion.
