#!/usr/bin/env python3
"""Translate an arbitrary slice of blocks of a markdown file through the linji translation pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

import regex
from bargardan_tools import _md, check_linebreaks, normalize
from tools import anchors, translate

def translate_slice(
    source_path: Path,
    start_block: int,
    end_block: int,
    out_path: Path,
    *,
    cache_prefix: str = "",
    skip_translate: bool = False,
    show_browser: bool = False,
) -> int:
    source_doc = _md.parse(source_path, source_path.read_text("utf-8"))
    all_blocks = _md.iter_blocks(source_doc)
    total_blocks = len(all_blocks)
    if start_block < 0 or end_block > total_blocks or start_block >= end_block:
        print(f"Error: Invalid slice {start_block}..{end_block} for {total_blocks} blocks", file=sys.stderr)
        return 1

    slice_blocks = all_blocks[start_block:end_block]
    slice_text = "\n\n".join(b.text for b in slice_blocks)
    expected_blocks = len(slice_blocks)

    tag = cache_prefix or f"{source_path.stem}_{start_block}_{end_block}"
    temp_en = Path(f"/tmp/{tag}.en.md")
    temp_fa = Path(f"/tmp/{tag}.fa.md")

    # 1. Tokenize
    stripped, forms = anchors.engine.tokenize(
        slice_text, anchors.TOKEN, anchors.render_for(source_path.name)
    )
    temp_en.write_text(stripped, encoding="utf-8")
    print(f"[{tag}] Tokenized {expected_blocks} blocks -> {len(stripped)} chars, {len(forms)} sentinels")

    # 2. Translate
    if skip_translate:
        print(f"[{tag}] Skipping translate (--skip-translate)")
        if not temp_fa.exists():
            temp_fa.write_text(stripped, encoding="utf-8")
    else:
        if not temp_fa.exists() or temp_fa.stat().st_size == 0:
            print(f"[{tag}] Invoking gTranslator with Advanced model...")
            cmd = [
                str(translate.GTRANSLATOR_PYTHON),
                str(translate.GTRANSLATOR_SCRIPT),
                "-f", str(temp_en),
                "-t", "fa",
                "-w",
                "--raw",
                "-o", str(temp_fa),
            ]
            if show_browser:
                cmd.append("--show")
            res = subprocess.run(cmd)
            if res.returncode != 0:
                print(f"[{tag}] gTranslator failed with exit code {res.returncode}", file=sys.stderr)
                return res.returncode
        else:
            print(f"[{tag}] Reusing existing draft at {temp_fa}")

    draft_text = temp_fa.read_text(encoding="utf-8")
    draft_text = translate.clean_draft_sentinels(draft_text, len(forms))
    temp_fa.write_text(draft_text, encoding="utf-8")

    # Check for missing sentinels
    seen = {int(m.group(1)) for m in regex.finditer(r"⟦(\d+)⟧", draft_text)}
    missing = sorted(set(range(1, len(forms) + 1)) - seen)
    if missing:
        print(f"[{tag}] Warning: Missing sentinels: {missing}", file=sys.stderr)
        # Attempt heuristic rescue for missing sentinels
        for m_num in missing:
            pattern = rf"(?<!\d){m_num}(?!\d)"
            m = regex.search(pattern, draft_text)
            if m:
                draft_text = regex.sub(pattern, f"⟦{m_num}⟧", draft_text, count=1)
                print(f"[{tag}] Rescued sentinel ⟦{m_num}⟧")
            else:
                draft_text += f"\n\n⟦{m_num}⟧"
                print(f"[{tag}] Appended missing sentinel ⟦{m_num}⟧ to preserve apparatus")

    # 3. Restore
    restored = anchors.engine.restore(source_path.name, slice_text, draft_text, anchors.TOKEN, anchors.render_for(source_path.name))
    
    # 4. Normalize & linebreaks
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(restored, encoding="utf-8")
    norm_config = normalize.load_config()
    normalize.process([out_path], norm_config, fix=True)
    check_linebreaks.process([out_path], fix=True)

    # 5. Check block parity for this slice
    out_doc = _md.parse(out_path, out_path.read_text("utf-8"))
    out_blocks = _md.iter_blocks(out_doc)
    actual_blocks = len(out_blocks)
    if actual_blocks != expected_blocks:
        print(f"[{tag}] Parity warning: {actual_blocks} blocks in output, expected {expected_blocks}", file=sys.stderr)
    else:
        print(f"[{tag}] Success! {actual_blocks} blocks match exactly.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("start", type=int, help="start block index (0-based)")
    parser.add_argument("end", type=int, help="end block index (exclusive)")
    parser.add_argument("-o", "--out", type=Path, required=True)
    parser.add_argument("--cache-prefix", type=str, default="")
    parser.add_argument("--skip-translate", action="store_true")
    parser.add_argument("--show", action="store_true")
    args = parser.parse_args(argv)

    return translate_slice(
        args.source,
        args.start,
        args.end,
        args.out,
        cache_prefix=args.cache_prefix,
        skip_translate=args.skip_translate,
        show_browser=args.show,
    )

if __name__ == "__main__":
    raise SystemExit(main())
