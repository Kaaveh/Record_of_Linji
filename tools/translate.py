#!/usr/bin/env python3
"""Automated translation orchestrator for The Record of Linji.

Drives the complete pipeline:
  1. Strip inline markup, Chinese text blocks, and headings to sentinels (tools/anchors.py)
  2. Translate English draft to Persian with Google Translate's Advanced (Gemini) model (gTranslator)
  3. Restore sentinels to Persian headings, original Chinese blocks, and footnote links (tools/anchors.py)
  4. Normalize Persian orthography (linji_tools.normalize)
  5. Enforce semantic line breaks (linji_tools.check_linebreaks)
  6. Validate block parity (linji_tools.check_parity)

Usage:
    tools/translate.py source/01-discourses/01.md
    tools/translate.py source/01-discourses/01.md -o fa/01-discourses/01.md
    tools/translate.py --skip-translate source/01-discourses/01.md -o fa/01-discourses/01.md
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from linji_tools import check_linebreaks, check_parity, normalize
from tools import anchors

GTRANSLATOR_DIR = Path("/Users/kaavehmohamedi/Project/Backend/gTranslator")
GTRANSLATOR_PYTHON = GTRANSLATOR_DIR / ".venv" / "bin" / "python"
GTRANSLATOR_SCRIPT = GTRANSLATOR_DIR / "gtranslate.py"


def resolve_target(source: Path, target: Path | None) -> Path:
    if target:
        return target
    try:
        rel = source.resolve().relative_to((REPO / "source").resolve())
        return REPO / "fa" / rel
    except ValueError:
        return REPO / "fa" / source.name


def run_translation(
    source_path: Path,
    target_path: Path,
    *,
    skip_translate: bool = False,
    show_browser: bool = False,
    keep_temps: bool = False,
) -> int:
    if not source_path.is_file():
        print(f"error: source file {source_path} does not exist", file=sys.stderr)
        return 1

    stem = source_path.stem
    temp_en = Path(f"/tmp/{stem}.en.md")
    temp_fa = Path(f"/tmp/{stem}.fa.md")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    src_text = source_path.read_text(encoding="utf-8")

    # Step 1: Strip tokens to sentinels
    print(f"[1/5] Stripping protected tokens -> {temp_en} ...")
    stripped = anchors.strip(source_path.name, src_text)
    temp_en.write_text(stripped, encoding="utf-8")

    # Step 2: Translate with gTranslator
    if skip_translate:
        print("[2/5] Skipping gTranslator invocation (--skip-translate requested).")
        temp_fa.write_text(stripped, encoding="utf-8")
    else:
        if not GTRANSLATOR_PYTHON.exists() or not GTRANSLATOR_SCRIPT.exists():
            print(
                f"error: gTranslator not found at {GTRANSLATOR_DIR}.\n"
                f"Expected {GTRANSLATOR_PYTHON} and {GTRANSLATOR_SCRIPT}",
                file=sys.stderr,
            )
            return 1

        print(f"[2/5] Translating with Gemini Advanced model via gTranslator...")
        cmd = [
            str(GTRANSLATOR_PYTHON),
            str(GTRANSLATOR_SCRIPT),
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
            print(f"error: gTranslator exited with status {res.returncode}", file=sys.stderr)
            return res.returncode

    if not temp_fa.exists():
        print(f"error: expected draft output at {temp_fa} not found", file=sys.stderr)
        return 1

    draft_text = temp_fa.read_text(encoding="utf-8")

    # Step 3: Restore tokens
    print(f"[3/5] Restoring sentinels and headings -> {target_path} ...")
    try:
        restored = anchors.restore(source_path.name, src_text, draft_text)
        target_path.write_text(restored, encoding="utf-8")
    except ValueError as exc:
        print(f"\nerror during restore: {exc}", file=sys.stderr)
        print(
            f"\nTo fix dropped sentinels:\n"
            f"1. Edit {temp_fa} to place the missing sentinel(s) in the matching Persian clause.\n"
            f"2. Resume restoration with:\n"
            f"   python3 tools/anchors.py restore {source_path} {temp_fa} -o {target_path}\n"
            f"   python3 -m linji_tools.normalize {target_path} --fix\n"
            f"   python3 -m linji_tools.check_linebreaks {target_path} --fix\n"
            f"   python3 -m linji_tools.check_parity {source_path} {target_path}\n",
            file=sys.stderr,
        )
        return 1

    # Step 4: Orthographic Normalization
    print("[4/5] Normalizing Persian orthography...")
    norm_config = normalize.load_config()
    _, norm_rewritten = normalize.process([target_path], norm_config, fix=True)

    # Step 5: Semantic Line Breaks
    print("[5/5] Enforcing semantic line breaks...")
    _, lb_rewritten = check_linebreaks.process([target_path], fix=True)

    # Verification: Check parity
    findings = check_parity.compare_files(source_path, target_path)
    if findings:
        print(f"\nwarning: parity mismatch detected for {target_path}:", file=sys.stderr)
        for f in findings:
            print(f"  {f}", file=sys.stderr)
    else:
        print("Parity verification: PASSED (block counts align with source).")

    if not keep_temps:
        temp_en.unlink(missing_ok=True)

    print(f"\nSuccessfully processed: {source_path} -> {target_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("source", type=Path, help="source file to translate")
    parser.add_argument("-o", "--out", type=Path, help="target output file in fa/")
    parser.add_argument(
        "--skip-translate",
        action="store_true",
        help="skip calling gTranslator (useful for dry runs and testing pipeline)",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="show the browser window while gTranslator runs",
    )
    parser.add_argument(
        "--keep-temps",
        action="store_true",
        help="keep temporary intermediate files in /tmp",
    )
    args = parser.parse_args(argv)

    target = resolve_target(args.source, args.out)
    return run_translation(
        args.source,
        target,
        skip_translate=args.skip_translate,
        show_browser=args.show,
        keep_temps=args.keep_temps,
    )


if __name__ == "__main__":
    raise SystemExit(main())
