"""Agent 2: BrowserAgent - Uses Playwright to automate Bing Image Creator."""

import asyncio
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright


BING_URL = "https://www.bing.com/images/create/ai-image-generator"
STORAGE_FILE = Path(__file__).resolve().parent.parent / "bing_auth_state.json"


async def run_async(scenes: list[dict], output_dir: Path, **kwargs) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    success_count = 0
    fail_count = 0

    async with async_playwright() as p:
        context_kwargs = {
            "viewport": {"width": 1280, "height": 900},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        }
        if STORAGE_FILE.exists():
            context_kwargs["storage_state"] = str(STORAGE_FILE)

        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**context_kwargs)
        page = await context.new_page()

        try:
            await page.goto(BING_URL, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)

            if await _needs_login(page):
                print("\n[BrowserAgent] Microsoft login required.")
                print("[BrowserAgent] Run: python login_bing.py to save your login session")
                print("[BrowserAgent] Then re-run the pipeline.\n")
                raise RuntimeError("Not logged into Bing Image Creator")

            for scene in scenes:
                scene_id = scene["scene_id"]
                prompt = scene["prompt"]
                out_path = output_dir / f"scene_{scene_id:03d}.png"
                try:
                    await _generate_single_image(page, prompt, out_path)
                    if out_path.exists() and out_path.stat().st_size > 5000:
                        results.append({"scene_id": scene_id, "path": str(out_path), "success": True})
                        success_count += 1
                    else:
                        results.append({"scene_id": scene_id, "success": False, "error": "Image too small or missing"})
                        fail_count += 1
                except Exception as e:
                    results.append({"scene_id": scene_id, "success": False, "error": str(e)})
                    fail_count += 1
        finally:
            await browser.close()

    return {
        "agent": "BrowserAgent",
        "output_dir": str(output_dir),
        "results": results,
        "success_count": success_count,
        "fail_count": fail_count,
        "total": len(scenes),
    }


async def _needs_login(page) -> bool:
    try:
        btn = page.locator("a, button", has_text="Sign in").first
        return await btn.is_visible(timeout=3000)
    except Exception:
        return False


async def _generate_single_image(page, prompt: str, output_path: Path):
    textarea = page.locator("textarea")
    await textarea.wait_for(state="visible", timeout=10000)
    await textarea.click()
    await textarea.fill("")
    await page.wait_for_timeout(500)
    await textarea.fill(prompt)
    await page.wait_for_timeout(500)
    await page.keyboard.press("Enter")

    await page.wait_for_timeout(8000)

    for _ in range(45):
        await page.wait_for_timeout(2000)
        try:
            imgs = await page.locator("img").all()
            for img in imgs:
                src = await img.get_attribute("src") or ""
                if "th.bing.com" in src or "bing.com/th" in src or "gimg" in src:
                    response = await page.request.get(src)
                    if response.ok:
                        data = await response.body()
                        if len(data) > 5000:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(data)
                            return
        except Exception:
            pass
    raise RuntimeError("Could not download generated image from Bing")


def run(scenes: list[dict], output_dir: Path, **kwargs) -> dict[str, Any]:
    return asyncio.run(run_async(scenes, output_dir, **kwargs))
