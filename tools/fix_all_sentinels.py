#!/usr/bin/env python3
"""Fix sentinel issues in all existing .fa.md slice files and re-restore them.

For each slice that has a .fa.md file:
1. Restore .fa.md from backup if exists, or use current clean version
2. Run inject_sentinels to add missing sentinels
3. Run translate_slice.py --skip-translate to restore anchors
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from linji_tools import _md


def plan_slices(blocks: list, start: int, max_chars: int = 3500) -> list[tuple[int, int, int]]:
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


def main() -> int:
    source = Path("source/04-historical-introduction/historical-introduction.md")
    doc = _md.read(str(source))
    blocks = _md.iter_blocks(doc)
    slices = plan_slices(blocks, 69)

    python = str(REPO / ".venv/bin/python")
    inject_script = str(REPO / "tools/inject_sentinels.py")
    translate_script = str(REPO / "tools/translate_slice.py")

    results = {"success": [], "failed": [], "missing_fa": []}

    for idx, (s, e, sz) in enumerate(slices):
        tag = f"hist_{s}_{e}"
        en_file = Path(f"/tmp/{tag}.en.md")
        fa_file = Path(f"/tmp/{tag}.fa.md")
        fa_bak = Path(f"/tmp/{tag}.fa.md.bak")
        out_file = Path(f"/tmp/{tag}_out.md")

        if not fa_file.exists():
            print(f"[{idx+1}/{len(slices)}] ⬜ {tag}: No .fa.md (not yet translated)")
            results["missing_fa"].append(tag)
            continue

        # Restore from backup if it exists (to get clean version)
        if fa_bak.exists():
            import shutil
            shutil.copy2(fa_bak, fa_file)

        # Step 1: Ensure .en.md exists (tokenize)
        if not en_file.exists():
            # Run translate_slice just for tokenization, it will create .en.md
            subprocess.run([python, translate_script, str(source), str(s), str(e),
                          "-o", str(out_file), "--cache-prefix", tag, "--skip-translate"],
                         capture_output=True, cwd=str(REPO))

        # Step 2: Inject sentinels
        res = subprocess.run([python, inject_script, str(en_file), str(fa_file)],
                           capture_output=True, text=True, cwd=str(REPO))
        if res.returncode != 0:
            print(f"[{idx+1}/{len(slices)}] ❌ {tag}: inject_sentinels failed: {res.stderr}")
            results["failed"].append(tag)
            continue

        # Step 3: Restore
        res = subprocess.run([python, translate_script, str(source), str(s), str(e),
                            "-o", str(out_file), "--cache-prefix", tag, "--skip-translate"],
                           capture_output=True, text=True, cwd=str(REPO))
        
        if "Success!" in res.stdout:
            print(f"[{idx+1}/{len(slices)}] ✅ {tag}: {res.stdout.strip().split(chr(10))[-1]}")
            results["success"].append(tag)
        elif "Parity warning" in res.stdout:
            print(f"[{idx+1}/{len(slices)}] ⚠️  {tag}: {res.stdout.strip().split(chr(10))[-1]}")
            results["failed"].append(tag)
        elif res.returncode != 0:
            err_lines = (res.stderr or res.stdout).strip().split('\n')
            print(f"[{idx+1}/{len(slices)}] ❌ {tag}: {err_lines[-1]}")
            results["failed"].append(tag)
        else:
            print(f"[{idx+1}/{len(slices)}] ✅ {tag}")
            results["success"].append(tag)

    print(f"\n--- Summary ---")
    print(f"✅ Success: {len(results['success'])}")
    print(f"❌ Failed: {len(results['failed'])}")
    print(f"⬜ Not translated: {len(results['missing_fa'])}")
    if results["failed"]:
        print(f"\nFailed slices: {results['failed']}")
    return 0 if not results["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
