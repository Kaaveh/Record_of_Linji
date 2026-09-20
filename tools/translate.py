#!/usr/bin/env python3
"""Automated translation orchestrator for The Record of Linji.

Drives the complete pipeline:
  1. Strip inline markup, Chinese text blocks, and headings to sentinels (tools/anchors.py)
  2. Translate English draft to Persian with Google Translate's Advanced (Gemini) model (gTranslator)
  3. Restore sentinels to Persian headings, original Chinese blocks, and footnote links (tools/anchors.py)
  4. Normalize Persian orthography (bargardan_tools.normalize)
  5. Enforce semantic line breaks (bargardan_tools.check_linebreaks)
  6. Validate block parity (bargardan_tools.check_parity)

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

import regex
from bargardan_tools import check_linebreaks, check_parity, normalize
from tools import anchors

GTRANSLATOR_DIR = Path("/Users/kaavehmohamedi/Project/Backend/gTranslator")
GTRANSLATOR_PYTHON = GTRANSLATOR_DIR / ".venv" / "bin" / "python"
GTRANSLATOR_SCRIPT = GTRANSLATOR_DIR / "gtranslate.py"


def clean_draft_sentinels(draft: str, expected_count: int = 0) -> str:
    """Normalize any formatting artifacts Google Translate introduces to sentinels."""
    def _to_ascii_digits(s: str) -> str:
        return s.translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        )

    # 1. Close any accidental internal spaces or digits inside brackets: ⟦ 3 ⟧ or ⟦ ۳ ⟧ -> ⟦3⟧
    draft = regex.sub(
        r"⟦\s*([0-9۰-۹٠-١]+)\s*⟧",
        lambda m: f"⟦{_to_ascii_digits(m.group(1))}⟧",
        draft,
    )

    # 2. Fix missing opening bracket: 9⟧ -> ⟦9⟧
    draft = regex.sub(
        r"(?<![⟦0-9۰-۹٠-١])([0-9۰-۹٠-١]+)⟧",
        lambda m: f"⟦{_to_ascii_digits(m.group(1))}⟧",
        draft,
    )

    # 3. Fix missing closing bracket: ⟦9 -> ⟦9⟧
    draft = regex.sub(
        r"⟦([0-9۰-۹٠-١]+)(?![0-9۰-۹٠-١]*⟧)",
        lambda m: f"⟦{_to_ascii_digits(m.group(1))}⟧",
        draft,
    )

    # 4. If expected_count is provided, fix bracket mutations like [15] -> ⟦15⟧ for missing numbers
    if expected_count > 0:
        seen = {int(m.group(1)) for m in regex.finditer(r"⟦(\d+)⟧", draft)}
        missing = set(range(1, expected_count + 1)) - seen
        for num in sorted(missing):
            pattern = rf"\[\s*{num}\s*\]"
            if regex.search(pattern, draft):
                draft = regex.sub(pattern, f"⟦{num}⟧", draft, count=1)
                missing.remove(num)
                continue
            p_num = str(num).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
            p_pattern = rf"\[\s*{p_num}\s*\]"
            if regex.search(p_pattern, draft):
                draft = regex.sub(p_pattern, f"⟦{num}⟧", draft, count=1)
                missing.remove(num)
                continue

    return draft


def resolve_target(source: Path, target: Path | None) -> Path:
    if target:
        if target.is_dir() or (not target.suffix and not target.exists()):
            return target / source.name
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
    stripped, forms = anchors.engine.tokenize(
        src_text, anchors.TOKEN, anchors.render_for(source_path.name)
    )
    temp_en.write_text(stripped, encoding="utf-8")

    # Step 2: Translate with gTranslator
    if skip_translate:
        print("[2/5] Skipping gTranslator invocation (--skip-translate requested).")
        if not temp_fa.exists():
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
    draft_text = clean_draft_sentinels(draft_text, len(forms))
    temp_fa.write_text(draft_text, encoding="utf-8")

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
            f"   python3 -m bargardan_tools.normalize {target_path} --fix\n"
            f"   python3 -m bargardan_tools.check_linebreaks {target_path} --fix\n"
            f"   python3 -m bargardan_tools.check_parity {source_path} {target_path}\n",
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
        temp_fa.unlink(missing_ok=True)

    print(f"\nSuccessfully processed: {source_path} -> {target_path}")
    return 0


def expand_sources(sources: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for s in sources:
        if s.is_dir():
            expanded.extend(sorted(s.glob("*.md")))
        elif s.is_file():
            expanded.append(s)
        else:
            matches = sorted(s.parent.glob(s.name)) if "*" in s.name else []
            if matches:
                expanded.extend(matches)
            else:
                expanded.append(s)
    return expanded


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "sources",
        type=Path,
        nargs="+",
        help="source file(s) or directory to translate",
    )
    parser.add_argument("-o", "--out", type=Path, help="target output file or directory in fa/")
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

    file_list = expand_sources(args.sources)
    if not file_list:
        print("error: no input files found", file=sys.stderr)
        return 1

    success_count = 0
    failed_files: list[tuple[Path, int]] = []

    for idx, src in enumerate(file_list, 1):
        target = resolve_target(src, args.out)
        print(f"\n==================================================")
        print(f"[{idx}/{len(file_list)}] Processing: {src} -> {target}")
        print(f"==================================================")
        rc = run_translation(
            src,
            target,
            skip_translate=args.skip_translate,
            show_browser=args.show,
            keep_temps=args.keep_temps,
        )
        if rc == 0:
            success_count += 1
        else:
            failed_files.append((src, rc))

    print(f"\n==================================================")
    print(f"Batch Summary: {success_count}/{len(file_list)} files succeeded.")
    if failed_files:
        print("Failures:")
        for f, code in failed_files:
            print(f"  {f} (exit code {code})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
