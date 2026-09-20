#!/usr/bin/env python3
"""Build fa/04-historical-introduction/historical-introduction.md in modular verified slices."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from bargardan_tools import _md, check_linebreaks, check_parity, normalize
from tools.translate_slice import translate_slice

SLICES = [
    ("hist_s0", 0, 7),     # Preamble & Overview
    ("hist_s1", 7, 20),    # Historical Background
    ("hist_s2", 20, 41),   # Life of Linji Part 1 (Training & Awakening)
    ("hist_s3", 41, 61),   # Life of Linji Part 2 (Zhenzhou & Disciples)
    ("hist_s4", 61, 69),   # Development of Yulu genre
    ("hist_s5", 69, 88),   # The Linji lu in China & Japan
    ("hist_s6", 88, 107),  # Notes Part 1 (Notes 1..30)
    ("hist_s7", 107, 126), # Notes Part 2 (Notes 31..60)
    ("hist_s8", 126, 145), # Notes Part 3 (Notes 61..92)
]

def main():
    src_file = REPO / "source" / "04-historical-introduction" / "historical-introduction.md"
    dst_file = REPO / "fa" / "04-historical-introduction" / "historical-introduction.md"

    # Reuse sec0 if available
    sec0_cache = Path("/tmp/sec0.fa.md")
    hist_s0_cache = Path("/tmp/hist_s0.fa.md")
    if sec0_cache.exists() and not hist_s0_cache.exists():
        hist_s0_cache.write_text(sec0_cache.read_text("utf-8"), "utf-8")

    slice_outputs = []
    for tag, start, end in SLICES:
        print(f"\n=======================================================")
        print(f"Processing Slice: {tag} (blocks {start}..{end-1})")
        print(f"=======================================================")
        out_slice = Path(f"/tmp/{tag}_out.md")
        rc = translate_slice(src_file, start, end, out_slice, cache_prefix=tag)
        if rc != 0:
            print(f"Error processing {tag}, exiting.", file=sys.stderr)
            return rc
        slice_outputs.append(out_slice)

    print("\nMerging all slices...")
    merged_blocks = []
    for out_slice in slice_outputs:
        content = out_slice.read_text("utf-8").strip()
        merged_blocks.append(content)

    final_body = "\n\n".join(merged_blocks)
    final_text = f"---\nstatus: reviewed\n---\n\n{final_body}\n"
    dst_file.write_text(final_text, encoding="utf-8")

    print("Running final normalization and linebreaks check...")
    norm_config = normalize.load_config()
    normalize.process([dst_file], norm_config, fix=True)
    check_linebreaks.process([dst_file], fix=True)

    print("Verifying parity with source...")
    findings = check_parity.compare_files(src_file, dst_file)
    if findings:
        for f in findings:
            print(f"  Parity error: {f}", file=sys.stderr)
        return 1

    print(f"\nSUCCESS: {dst_file} fully built and verified!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
