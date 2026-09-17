#!/usr/bin/env python3
"""
split_transcript.py
Splits Record_of_Linji_Translation_&_Commentary_of_Ruth_Fuller_Sasaki_Thomas.md
into modular Markdown files inside the source/ directory according to the
approved implementation plan.
"""

import os
import re
from pathlib import Path

SOURCE_FILE = "Record_of_Linji_Translation_&_Commentary_of_Ruth_Fuller_Sasaki_Thomas.md"
SOURCE_DIR = Path("source")

def clean_block(lines):
    """Strip leading and trailing blank lines from a list of lines, return joined string."""
    text = "".join(lines).strip()
    return text + "\n" if text else ""

def main():
    if not os.path.exists(SOURCE_FILE):
        print(f"Error: {SOURCE_FILE} not found.")
        return

    print(f"Reading {SOURCE_FILE}...")
    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total_lines = len(lines)
    print(f"Total lines read: {total_lines}")

    # Subdirectories
    dirs = [
        SOURCE_DIR / "00-front-matter",
        SOURCE_DIR / "01-discourses",
        SOURCE_DIR / "02-critical-examinations",
        SOURCE_DIR / "03-record-of-pilgrimages",
        SOURCE_DIR / "04-historical-introduction",
        SOURCE_DIR / "05-chinese-text",
        SOURCE_DIR / "06-reference-matter",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Front Matter Boundaries
    idx_foreword = 8       # ## Foreword
    idx_preface1975 = 31   # ## Preface to the 1975 Edition
    idx_prologue = 52      # ## Editor’s Prologue
    idx_abbrev = 143       # ## Abbreviations
    idx_p1 = 228           # # Part 1: The Record of Linji

    # Extract Front Matter files
    files_to_write = {}

    files_to_write["00-front-matter/foreword.md"] = clean_block(lines[idx_foreword:idx_preface1975])
    files_to_write["00-front-matter/preface-1975.md"] = clean_block(lines[idx_preface1975:idx_prologue])
    files_to_write["00-front-matter/editors-prologue.md"] = clean_block(lines[idx_prologue:idx_abbrev])
    files_to_write["00-front-matter/abbreviations.md"] = clean_block(lines[idx_abbrev:idx_p1])

    # Record Title Page (Part 1 preamble before Discourse I)
    title_page_lines = lines[idx_p1:244]
    files_to_write["00-front-matter/record-title-page.md"] = clean_block(title_page_lines)

    # 2. Discourses (01 to 22)
    disc_p1_indices = [i for i in range(244, 475) if lines[i].startswith("### Discourse ")]
    disc_p1_indices.append(474) # End of discourses in Part 1

    comm_d_indices = [i for i in range(1168, 3698) if lines[i].startswith("#### Commentary Section ") and i != 2463]
    comm_d_indices.append(3697) # End of discourses commentary

    assert len(disc_p1_indices) - 1 == 22, f"Expected 22 Discourses, got {len(disc_p1_indices)-1}"
    assert len(comm_d_indices) - 1 == 22, f"Expected 22 Comm Discourses, got {len(comm_d_indices)-1}"

    for i in range(22):
        sec_num = i + 1
        fn = f"01-discourses/{sec_num:02d}.md"
        
        t_lines = lines[disc_p1_indices[i]:disc_p1_indices[i+1]]
        t_text = "".join(t_lines).strip()

        c_lines = lines[comm_d_indices[i]:comm_d_indices[i+1]]
        c_cleaned_lines = []
        for line_idx, line in enumerate(c_lines):
            actual_idx = comm_d_indices[i] + line_idx
            if actual_idx == 2463:
                continue
            c_cleaned_lines.append(line)
        c_text = "".join(c_cleaned_lines).strip()

        content = ""
        if sec_num == 1:
            content += "## Part One: Discourses (上堂)\n\n"
        content += t_text + "\n\n---\n\n## Commentary\n\n" + c_text + "\n"
        files_to_write[fn] = content

    # 3. Critical Examinations (23 to 46)
    ce_p1_indices = [i for i in range(474, 630) if lines[i].startswith("### Critical Examination ")]
    ce_p1_indices.append(629) # End of critical examinations in Part 1

    comm_ce_indices = [i for i in range(3698, 4229) if lines[i].startswith("#### Commentary Section ")]
    comm_ce_indices.append(4228) # End of critical examinations commentary

    assert len(ce_p1_indices) - 1 == 24, f"Expected 24 Critical Examinations, got {len(ce_p1_indices)-1}"
    assert len(comm_ce_indices) - 1 == 24, f"Expected 24 Comm Critical Examinations, got {len(comm_ce_indices)-1}"

    for i in range(24):
        sec_num = 23 + i
        fn = f"02-critical-examinations/{sec_num:02d}.md"

        t_lines = lines[ce_p1_indices[i]:ce_p1_indices[i+1]]
        t_text = "".join(t_lines).strip()

        c_lines = lines[comm_ce_indices[i]:comm_ce_indices[i+1]]
        c_text = "".join(c_lines).strip()

        content = ""
        if sec_num == 23:
            content += "## Part Two: Critical Examinations (勘辨)\n\n"
        content += t_text + "\n\n---\n\n## Commentary\n\n" + c_text + "\n"
        files_to_write[fn] = content

    # 4. Record of Pilgrimages (47 to 68)
    pilg_p1_indices = [i for i in range(629, 865) if lines[i].startswith("### Pilgrimage ")]
    pilg_p1_indices.append(864) # End of pilgrimages in Part 1

    comm_p_indices = [i for i in range(4229, 4892) if lines[i].startswith("#### Commentary Section ")]
    comm_p_indices.append(4891) # End of pilgrimages commentary

    assert len(pilg_p1_indices) - 1 == 22, f"Expected 22 Pilgrimages, got {len(pilg_p1_indices)-1}"
    assert len(comm_p_indices) - 1 == 22, f"Expected 22 Comm Pilgrimages, got {len(comm_p_indices)-1}"

    for i in range(22):
        sec_num = 47 + i
        fn = f"03-record-of-pilgrimages/{sec_num:02d}.md"

        t_lines = lines[pilg_p1_indices[i]:pilg_p1_indices[i+1]]
        t_text = "".join(t_lines).strip()

        c_lines = lines[comm_p_indices[i]:comm_p_indices[i+1]]
        c_text = "".join(c_lines).strip()

        content = ""
        if sec_num == 47:
            content += "## Part Three: Record of Pilgrimages (行錄)\n\n"
        content += t_text + "\n\n---\n\n## Commentary\n\n" + c_text + "\n"
        files_to_write[fn] = content

    # 5. Ma Fang's Preface (69-ma-fang-preface.md)
    maf_t_lines = lines[864:870]
    maf_t_text = "".join(maf_t_lines).strip()

    maf_c_lines = lines[4891:4938]
    maf_c_text = "".join(maf_c_lines).strip()

    files_to_write["03-record-of-pilgrimages/69-ma-fang-preface.md"] = (
        maf_t_text + "\n\n---\n\n## Commentary\n\n" + maf_c_text + "\n"
    )

    # 6. Historical Introduction (Yanagida Seizan)
    hist_lines = lines[872:1164]
    files_to_write["04-historical-introduction/historical-introduction.md"] = clean_block(hist_lines)

    # 7. Chinese Text (Part 3)
    files_to_write["05-chinese-text/discourses.md"] = clean_block(lines[4945:5038])
    files_to_write["05-chinese-text/critical-examinations.md"] = clean_block(lines[5038:5111])
    files_to_write["05-chinese-text/record-of-pilgrimages.md"] = clean_block(lines[5111:5188])

    # 8. Reference Matter (Part 4)
    files_to_write["06-reference-matter/bibliography.md"] = clean_block(lines[5190:5578])
    files_to_write["06-reference-matter/personal-names.md"] = clean_block(lines[5578:6052])
    files_to_write["06-reference-matter/index.md"] = clean_block(lines[6052:])

    # Write all files
    print(f"Writing {len(files_to_write)} modular files to {SOURCE_DIR}...")
    for rel_path, content in files_to_write.items():
        out_path = SOURCE_DIR / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

    generate_readme(files_to_write)
    print("Splitting completed successfully!")

def get_opening(text):
    lines = text.splitlines()
    for l in lines:
        l = l.strip()
        if not l or l.startswith("#") or l.startswith("*") or l.startswith(">") or l.startswith("---"):
            continue
        if len(l) > 75:
            return l[:75].rstrip() + "…"
        return l
    return ""

def generate_readme(files):
    readme_path = SOURCE_DIR / "README.md"
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# The Record of Linji (臨濟錄)\n\n")
        f.write("*Translation and Commentary by Ruth Fuller Sasaki, Edited by Thomas Yūhō Kirchner*\n\n")
        f.write("This directory contains the modular source text of *The Record of Linji*, organized into ")
        f.write("numbered subdirectories. Each numbered section integrates the English translation of the passage ")
        f.write("together with its corresponding scholarly commentary.\n\n")

        f.write("## Structure Overview\n\n")
        f.write("- **Front Matter**: `00-front-matter/` (Foreword, 1975 Preface, Editor's Prologue, Abbreviations, Title Page)\n")
        f.write("- **Discourses (上堂)**: `01-discourses/` (`01.md` – `22.md`)\n")
        f.write("- **Critical Examinations (勘辨)**: `02-critical-examinations/` (`23.md` – `46.md`)\n")
        f.write("- **Record of Pilgrimages (行錄)**: `03-record-of-pilgrimages/` (`47.md` – `68.md` and `69-ma-fang-preface.md`)\n")
        f.write("- **Historical Introduction**: `04-historical-introduction/` (`historical-introduction.md` by Yanagida Seizan)\n")
        f.write("- **Chinese Original Text**: `05-chinese-text/` (Discourses, Critical Examinations, Pilgrimages)\n")
        f.write("- **Reference Matter**: `06-reference-matter/` (Bibliography, Personal Names, Index)\n\n")

        # Table 1: Discourses
        f.write("## Part One: Discourses (上堂)\n\n")
        f.write("| # | File | Opens |\n")
        f.write("|---|---|---|\n")
        for i in range(1, 23):
            fn = f"01-discourses/{i:02d}.md"
            content = files.get(fn, "")
            trans_part = content.split("---")[0] if "---" in content else content
            opening = get_opening(trans_part)
            f.write(f"| **{i}** | [{i:02d}.md]({fn}) | {opening} |\n")
        f.write("\n")

        # Table 2: Critical Examinations
        f.write("## Part Two: Critical Examinations (勘辨)\n\n")
        f.write("| # | File | Opens |\n")
        f.write("|---|---|---|\n")
        for i in range(23, 47):
            fn = f"02-critical-examinations/{i:02d}.md"
            content = files.get(fn, "")
            trans_part = content.split("---")[0] if "---" in content else content
            opening = get_opening(trans_part)
            f.write(f"| **{i}** | [{i:02d}.md]({fn}) | {opening} |\n")
        f.write("\n")

        # Table 3: Record of Pilgrimages
        f.write("## Part Three: Record of Pilgrimages (行錄)\n\n")
        f.write("| # | File | Opens |\n")
        f.write("|---|---|---|\n")
        for i in range(47, 69):
            fn = f"03-record-of-pilgrimages/{i:02d}.md"
            content = files.get(fn, "")
            trans_part = content.split("---")[0] if "---" in content else content
            opening = get_opening(trans_part)
            f.write(f"| **{i}** | [{i:02d}.md]({fn}) | {opening} |\n")
        
        # Ma Fang Preface
        fn_maf = "03-record-of-pilgrimages/69-ma-fang-preface.md"
        content_maf = files.get(fn_maf, "")
        trans_maf = content_maf.split("---")[0] if "---" in content_maf else content_maf
        opening_maf = get_opening(trans_maf)
        f.write(f"| **69** | [69-ma-fang-preface.md]({fn_maf}) | {opening_maf} |\n\n")

        # Reference Sections
        f.write("## Additional Materials\n\n")
        f.write("- [Foreword](00-front-matter/foreword.md) (*Yamada Mumon*)\n")
        f.write("- [Preface to the 1975 Edition](00-front-matter/preface-1975.md) (*Furuta Kazuhiro*)\n")
        f.write("- [Editor's Prologue](00-front-matter/editors-prologue.md) (*Thomas Yūhō Kirchner*)\n")
        f.write("- [Abbreviations](00-front-matter/abbreviations.md)\n")
        f.write("- [Record Title Page](00-front-matter/record-title-page.md)\n")
        f.write("- [Historical Introduction](04-historical-introduction/historical-introduction.md) (*Yanagida Seizan*)\n")
        f.write("- [Chinese Text: Discourses](05-chinese-text/discourses.md)\n")
        f.write("- [Chinese Text: Critical Examinations](05-chinese-text/critical-examinations.md)\n")
        f.write("- [Chinese Text: Record of Pilgrimages](05-chinese-text/record-of-pilgrimages.md)\n")
        f.write("- [Bibliography](06-reference-matter/bibliography.md)\n")
        f.write("- [List of Personal Names](06-reference-matter/personal-names.md)\n")
        f.write("- [Cumulative Index](06-reference-matter/index.md)\n")

if __name__ == "__main__":
    main()
