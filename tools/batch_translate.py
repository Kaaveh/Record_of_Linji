#!/usr/bin/env python3
"""Batch translate remaining slices of a markdown file.

Usage:
    batch_translate.py <source> <start_block> [--max-chars N] [--dry-run]
    
Pipeline per slice:
1. Tokenize (translate_slice.py creates .en.md)
2. Translate via gTranslator (.fa.md)
3. Inject missing sentinels (inject_sentinels.py)
4. Restore anchors (translate_slice.py --skip-translate)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from linji_tools import _md

MAX_CHARS = 3500


def plan_slices(blocks: list, start: int, max_chars: int = MAX_CHARS) -> list[tuple[int, int, int]]:
    slices = []
    current_start = start
    current_size = 0
    for i in range(start, len(blocks)):
        blen = len(blocks[i].text)
        if blen > max_chars:
            if current_size > 0:
                slices.append((current_start, i, current_size))
            slices.append((i, i + 1, blen))
            current_start = i + 1
            current_size = 0
        elif current_size + blen > max_chars:
            slices.append((current_start, i, current_size))
            current_start = i
            current_size = blen
        else:
            current_size += blen
    if current_size > 0:
        slices.append((current_start, len(blocks), current_size))
    return slices


def translate_one_slice(source: Path, s: int, e: int, tag: str, *, show: bool = False) -> int:
    """Translate a single slice: tokenize + gTranslator + inject sentinels + restore."""
    python = str(REPO / ".venv/bin/python")
    inject_script = str(REPO / "tools/inject_sentinels.py")
    translate_script = str(REPO / "tools/translate_slice.py")

    en_file = Path(f"/tmp/{tag}.en.md")
    fa_file = Path(f"/tmp/{tag}.fa.md")
    out_file = Path(f"/tmp/{tag}_out.md")

    # Step 1: Translate (creates .en.md and .fa.md)
    cmd = [python, translate_script, str(source), str(s), str(e),
           "-o", str(out_file), "--cache-prefix", tag]
    if show:
        cmd.append("--show")

    res = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
    
    if "Success!" in res.stdout:
        print(res.stdout.strip())
        return 0
    
    # If translate_slice had parity issues or failed, try sentinel injection
    if fa_file.exists() and en_file.exists():
        # Remove the bad _out.md
        if out_file.exists():
            out_file.unlink()
        
        # Step 2: Inject sentinels
        res2 = subprocess.run([python, inject_script, str(en_file), str(fa_file)],
                            capture_output=True, text=True, cwd=str(REPO))
        if res2.returncode != 0:
            print(f"  inject_sentinels failed: {res2.stderr}")
            return 1
        
        # Step 3: Re-restore with fixed sentinels
        res3 = subprocess.run([python, translate_script, str(source), str(s), str(e),
                             "-o", str(out_file), "--cache-prefix", tag, "--skip-translate"],
                            capture_output=True, text=True, cwd=str(REPO))
        
        if "Success!" in res3.stdout:
            print(res3.stdout.strip())
            return 0
        else:
            print(f"  After injection: {(res3.stderr or res3.stdout).strip()}")
            return 1
    
    # Translation itself failed (gTranslator crash)
    if res.returncode != 0:
        print(f"  gTranslator failed: {(res.stderr or res.stdout).strip().split(chr(10))[-1]}")
        return res.returncode
    
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("start", type=int, help="start block index (0-based)")
    parser.add_argument("--max-chars", type=int, default=MAX_CHARS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args(argv)

    doc = _md.read(str(args.source))
    blocks = _md.iter_blocks(doc)
    slices = plan_slices(blocks, args.start, args.max_chars)

    prefix = args.source.stem
    print(f"Planned {len(slices)} slices starting from block {args.start}:")
    for s, e, sz in slices:
        tag = f"{prefix}_{s}_{e}"
        out = Path(f"/tmp/{tag}_out.md")
        status = "✅ EXISTS" if out.exists() else "⬜ TODO"
        print(f"  {status} {s}..{e} ({e-s} blocks, {sz} chars) -> {out}")

    if args.dry_run:
        todo = [sl for sl in slices if not Path(f"/tmp/{prefix}_{sl[0]}_{sl[1]}_out.md").exists()]
        print(f"\n{len(todo)} slices remaining to translate.")
        return 0

    failed = []
    for idx, (s, e, sz) in enumerate(slices):
        tag = f"{prefix}_{s}_{e}"
        out = Path(f"/tmp/{tag}_out.md")
        if out.exists():
            print(f"\n[{idx+1}/{len(slices)}] Skipping {s}..{e} (already done)")
            continue

        print(f"\n[{idx+1}/{len(slices)}] Translating {s}..{e} ({e-s} blocks, {sz} chars)...")
        rc = translate_one_slice(args.source, s, e, tag, show=args.show)
        
        if rc != 0:
            print(f"  ❌ Failed. Will continue with next slice.")
            failed.append(tag)
        
        time.sleep(2)

    if failed:
        print(f"\n❌ {len(failed)} slices failed: {failed}")
        return 1
    
    print(f"\n✅ All slices complete!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
