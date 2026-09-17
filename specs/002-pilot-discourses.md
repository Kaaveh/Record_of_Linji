# 002 — Part One: Discourses (Pilot Translation)

**Scope**: `source/01-discourses/01.md` through `source/01-discourses/22.md`  
**Scale**: 22 files · ~24,000 translation words · ~110,000 commentary words  
**Depends on**: [`001-translation-pipeline.md`](./001-translation-pipeline.md)

---

## Context

Part One contains Master Linji's formal sermons in the Dharma Hall and evening lectures. It is the doctrinal core of the book and establishes the fundamental concepts and philosophical vocabulary of the Linji school.

Because it contains both high ceremonial rhetoric and abrupt dialogues, it serves as the **pilot phase** for the entire translation. Decisions made here regarding terminology, tone, and commentary formatting will govern the rest of the work.

---

## Key Concepts & Doctrinal Terminology

The following recurring formulas and terms must be established and kept consistent:

| English Source | Pinyin / Chinese | Recommended Persian Rendering |
|---|---|---|
| Ascend the hall / take the high seat | 上堂 / 升座 | برآمدن به تالار / بر جایگاه نشستن |
| Followers of the Way | 道流 (daoliu) | رهروان راه / پویندگان طریق |
| True man without rank | 無位真人 (wuwei zhenren) | انسان حقیقیِ بی‌مقام |
| Cardinal principle of buddhadharma | 佛法大意 | معنای بنیادین بودادارما |
| The Great Matter | 大事 (dashi) | امر عظیم (کار بزرگ) |
| Four Procedures | 四料簡 | چهار تدبیر (چهار شیوه) |
| Host and guest | 賓主 (binzhu) | میزبان و مهمان |
| Mind-ground | 心地 (xindi) | ساحتِ دل (زمینه‌ی ذهن) |
| Threefold body (Trikāya) | 三身 (sanshen) | پیکر سه‌گانه (سه کالبد) |
| Buddha-Māra | 佛魔 | بودا-مارا (بودا و اهریمن) |
| Mountain monk (self-reference) | 山僧 (shanseng) | راهب کوهستان (این راهب) |

---

## Checklist of Sections

- [x] `01.md` — Discourse I: Opening sermon before Prefectural Governor Wang; "advising warrior"
- [x] `02.md` — Discourse II: Mayu pulls Linji down from the high seat
- [x] `03.md` — Discourse III: The "True Man without Rank" on the lump of red flesh
- [x] `04.md` — Discourse IV: Head monks shout simultaneously; host and guest
- [x] `05.md` — Discourse V: Huangbo's stick like mugwort
- [x] `06.md` — Discourse VI: Sword of Vajra
- [x] `07.md` — Discourse VII: Sitting on top of the solitary peak
- [x] `08.md` — Discourse VIII: Endlessly on the road
- [x] `09.md` — Discourse IX: The Three Phrases (三句)
- [x] `10.md` — Discourse X: The Four Procedures (四料簡) and the great evening sermon
- [x] `11.md` — Discourse XI: Urgency of acquiring true insight; the three bodies
- [x] `12.md` — Discourse XII: Nothing to do; being ordinary; defecating and urinating
- [x] `13.md` — Discourse XIII: Buddha-Māra; goose separating milk from water
- [x] `14.md` — Discourse XIV: True insight; entering secular and sacred; mother of all buddhas
- [x] `15.md` — Discourse XV: Four elements and four phases formless
- [x] `16.md` — Discourse XVI: Faith in oneself; independent man of the Way
- [x] `17.md` — Discourse XVII: Lands of the Three Eyes
- [x] `18.md` — Discourse XVIII: Mind and Mind not differing; long comprehensive sermon
- [x] `19.md` — Discourse XIX: True buddha, true dharma, true way
- [x] `20.md` — Discourse XX: Bodhidharma's purpose in coming from the West
- [x] `21.md` — Discourse XXI: Supreme Penetration Surpassing Wisdom Buddha
- [x] `22.md` — Discourse XXII: Karma of the five heinous crimes

---

## Acceptance Criteria

1. All 22 files translated and placed in `fa/01-discourses/`.
2. Each file maintains the `## Part One: Discourses (上堂)`, `### Discourse N`, translation, `---`, and `## Commentary` structure.
3. Chinese text blocks in the commentary remain intact.
4. One sentence per line enforced.
5. `linji_tools.check_parity` confirms block alignment between source and Persian.
