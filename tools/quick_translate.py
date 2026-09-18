#!/usr/bin/env python3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/kaavehmohamedi/Project/Backend/gTranslator")
import gtranslate
from playwright.sync_api import sync_playwright

def cleanup_locks():
    profile = Path(gtranslate.PROFILE_DIR)
    for f in profile.glob("Singleton*"):
        try:
            if f.is_symlink() or f.exists():
                f.unlink()
        except OSError:
            pass

def translate_file(in_path: Path, out_path: Path, source="en", target="fa"):
    text = in_path.read_text("utf-8")
    cleanup_locks()
    with sync_playwright() as p:
        ctx = gtranslate._open_context(p, headless=True)
        try:
            time.sleep(1)
            page = ctx.new_page()
            page.goto(f"https://translate.google.com/?sl={source}&tl={target}&op=translate", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(2500)
            gtranslate._dismiss_consent(page)
            gtranslate._select_advanced(page)
            box = page.locator(gtranslate.SRC_SEL).first
            box.fill(text)
            out = gtranslate._settle(page)
            out_path.write_text(out, "utf-8")
            print(f"Translated {len(text)} chars -> {len(out)} chars saved to {out_path}")
        finally:
            try:
                ctx.close()
            except Exception:
                pass
            cleanup_locks()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Usage: quick_translate.py <in_file> <out_file>")
    translate_file(Path(sys.argv[1]), Path(sys.argv[2]))
