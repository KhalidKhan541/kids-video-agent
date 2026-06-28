#!/usr/bin/env python3
"""Bing Image Creator Login Script.
Saves your Microsoft login session for headless image generation.

Usage:
    python login_bing.py
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

BING_URL = "https://www.bing.com/images/create/ai-image-generator"
STORAGE_FILE = ROOT / "bing_auth_state.json"


def main():
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Bing Image Creator Login")
    print("=" * 60)
    print("\nA browser window will open.")
    print("1. Sign in to your Microsoft account")
    print("2. Come back to this terminal once signed in")
    print("3. The session will save automatically\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()
        page.goto(BING_URL, timeout=60000)

        try:
            sign_in = page.locator("a, button", has_text="Sign in").first
            if sign_in.is_visible(timeout=3000):
                print("[Browser] Sign-in button found. Sign in to Microsoft in the browser...")
                sign_in.click()
        except Exception:
            pass

        print("[Browser] Waiting for you to sign in (checking every 5 seconds)...")
        for i in range(120):
            time.sleep(5)
            try:
                btn = page.locator("a, button", has_text="Sign in").first
                if not btn.is_visible(timeout=2000):
                    print(f"[OK] Login detected after {i * 5 + 5}s!")
                    break
            except Exception:
                print(f"[OK] Login detected!")
                break
            if i % 6 == 0:
                print(f"  Still waiting... ({i * 5 + 5}s)")
        else:
            print("[WARN] Timeout waiting for login. Saving whatever state exists.")

        context.storage_state(path=str(STORAGE_FILE))
        print(f"[OK] Session saved to: {STORAGE_FILE}")
        browser.close()

    print("[DONE] You can now run the pipeline without --skip-browser for real AI images!")


if __name__ == "__main__":
    main()
