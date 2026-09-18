#!/usr/bin/env python3
"""Automatically inject missing sentinels into Persian translations based on proportional position mapping.

Given an English tokenized text (.en.md) and Persian translation (.fa.md), this script:
1. Finds all sentinels in the English text and their relative positions
2. Identifies which sentinels are missing from the Persian text
3. Inserts missing sentinels at proportionally mapped positions in the Persian text
4. Snaps insertions to the nearest word/sentence boundary

Usage:
    inject_sentinels.py <en_file> <fa_file> [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def find_sentinel_positions(text: str) -> list[tuple[int, float, str, str]]:
    """Find all sentinels and their relative positions in text.
    
    Returns list of (sentinel_num, relative_position, before_context, after_context)
    """
    # Build clean text (without sentinels) to compute positions
    clean = re.sub(r'⟦\d+⟧', '', text)
    clean_len = len(clean)
    
    results = []
    # Track how many sentinel chars we've passed
    sentinel_offset = 0
    for m in re.finditer(r'⟦(\d+)⟧', text):
        num = int(m.group(1))
        # Position in clean text
        clean_pos = m.start() - sentinel_offset
        rel_pos = clean_pos / clean_len if clean_len > 0 else 0
        
        # Context in original text
        before = text[max(0, m.start()-40):m.start()]
        after = text[m.end():m.end()+40]
        
        results.append((num, rel_pos, before.strip(), after.strip()))
        sentinel_offset += len(m.group(0))
    
    return results


def find_best_insert_position(fa_clean: str, rel_pos: float, fa_len: int) -> int:
    """Find the best position to insert a sentinel in Persian text."""
    target_pos = int(rel_pos * fa_len)
    target_pos = max(0, min(target_pos, fa_len))
    
    # Preferred boundary characters (insert AFTER these)
    boundaries = set(' \n.،؛:؟!»)]\u200c')
    
    # Search for nearest boundary within ±50 chars
    for delta in range(0, 50):
        for pos in [target_pos + delta, target_pos - delta]:
            if 0 <= pos < fa_len:
                if fa_clean[pos] in boundaries:
                    return pos + 1
            if pos == target_pos - delta and 0 <= pos < fa_len:
                if fa_clean[pos] in boundaries:
                    return pos + 1
    
    # Fallback: just use target position
    return target_pos


def inject_sentinels(en_text: str, fa_text: str, *, verbose: bool = False) -> str:
    """Inject missing sentinels from en_text into fa_text at proportional positions."""
    
    en_positions = find_sentinel_positions(en_text)
    if not en_positions:
        return fa_text
    
    expected = {num for num, _, _, _ in en_positions}
    
    # Strip any bogus sentinels that don't exist in source
    fa_text = re.sub(r'⟦(\d+)⟧', lambda m: m.group(0) if int(m.group(1)) in expected else '', fa_text)
    
    # Deduplicate existing sentinels in fa_text (keep only first occurrence)
    seen_nums = set()
    def dedup(m):
        num = int(m.group(1))
        if num in seen_nums:
            return ""
        seen_nums.add(num)
        return m.group(0)
    fa_text = re.sub(r'⟦(\d+)⟧', dedup, fa_text)
    
    # Find existing valid sentinels in fa_text
    existing = set(int(m.group(1)) for m in re.finditer(r'⟦(\d+)⟧', fa_text))
    
    # Get missing sentinels
    missing = [(num, rel_pos, before, after) for num, rel_pos, before, after in en_positions 
               if num not in existing]
    
    if not missing:
        if verbose:
            print(f"All {len(en_positions)} sentinels present, nothing to inject.")
        return fa_text
    
    if verbose:
        print(f"Existing sentinels: {sorted(existing)}")
        print(f"Missing sentinels: {[m[0] for m in missing]}")
    
    # Remove existing sentinels from fa_text for position calculation, then re-add them
    fa_clean = re.sub(r'⟦\d+⟧', '', fa_text)
    fa_len = len(fa_clean)
    
    # Collect ALL sentinels (existing + missing) with their positions
    all_insertions: list[tuple[int, int]] = []  # (position_in_clean, sentinel_num)
    
    # Map existing sentinel positions
    sentinel_offset = 0
    for m in re.finditer(r'⟦(\d+)⟧', fa_text):
        num = int(m.group(1))
        clean_pos = m.start() - sentinel_offset
        all_insertions.append((clean_pos, num))
        sentinel_offset += len(m.group(0))
    
    # Add missing sentinels at proportional positions
    for num, rel_pos, before_ctx, after_ctx in missing:
        insert_pos = find_best_insert_position(fa_clean, rel_pos, fa_len)
        all_insertions.append((insert_pos, num))
        if verbose:
            context = fa_clean[max(0, insert_pos-20):insert_pos+20]
            print(f"  ⟦{num}⟧ at rel={rel_pos:.3f} -> pos={insert_pos}: ...{context}...")
    
    # Sort by position (ascending), then by sentinel number for ties
    all_insertions.sort(key=lambda x: (x[0], x[1]))
    
    # Ensure sentinel order is monotonically increasing by adjusting positions if needed
    # Actually, we just need to insert in the right order. Let's sort insertions by
    # sentinel number and ensure they're in the right positional order.
    
    # Build the result by inserting all sentinels into clean text from end to start
    all_insertions.sort(key=lambda x: x[0], reverse=True)
    
    result = fa_clean
    for pos, num in all_insertions:
        result = result[:pos] + f'⟦{num}⟧' + result[pos:]
    
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("en_file", type=Path, help="English tokenized file (.en.md)")
    parser.add_argument("fa_file", type=Path, help="Persian translation file (.fa.md)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without modifying files")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    
    en_text = args.en_file.read_text("utf-8")
    fa_text = args.fa_file.read_text("utf-8")
    
    result = inject_sentinels(en_text, fa_text, verbose=True)
    
    # Verify all sentinels present
    en_sentinels = sorted(set(int(m) for m in re.findall(r'⟦(\d+)⟧', en_text)))
    result_sentinels = sorted(set(int(m) for m in re.findall(r'⟦(\d+)⟧', result)))
    
    if en_sentinels == result_sentinels:
        print(f"✅ All {len(en_sentinels)} sentinels present in result.")
    else:
        still_missing = set(en_sentinels) - set(result_sentinels)
        print(f"❌ Still missing: {sorted(still_missing)}")
    
    # Check for duplicates
    all_found = [int(m) for m in re.findall(r'⟦(\d+)⟧', result)]
    from collections import Counter
    dupes = {k: v for k, v in Counter(all_found).items() if v > 1}
    if dupes:
        print(f"⚠️  Duplicated sentinels: {dupes}")
    
    if args.dry_run:
        print("\n--- Result preview (first 500 chars) ---")
        print(result[:500])
        return 0
    
    args.fa_file.write_text(result, "utf-8")
    print(f"Wrote {args.fa_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
