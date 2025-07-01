import asyncio
import random
from pathlib import Path
from typing import Callable, Optional, Any
from patchright.async_api import async_playwright, Page
from playwright_stealth import stealth_async
from core.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
PROXY_FILE = BASE_DIR / "data.txt"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
]


def load_proxies_from_file() -> list[dict]:
    """Load proxy list from the data.txt file."""
    proxies = []
    try:
        with open(PROXY_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 4:
                    host, port, user, password = parts
                    proxies.append({
                        "server": f"http://{host}:{port}",
                        "username": user,
                        "password": password
                    })
    except FileNotFoundError:
        logger.error(f"❌ File {PROXY_FILE} not found")
    return proxies


async def human_like_activity(page: Page):
    """Simulate basic human-like behavior to bypass bot detection."""
    for _ in range(3):
        await page.mouse.move(random.randint(100, 1000), random.randint(100, 700))
        await asyncio.sleep(random.uniform(0.5, 1.2))
        await page.keyboard.press("PageDown")
        await asyncio.sleep(random.uniform(1, 2))


async def run_browser(task_func: Callable[[Page], Any]) -> Optional[Any]:
    logger.info("🚀 Launching browser with proxy rotation")

    proxies = load_proxies_from_file()
    user_agent = random.choice(USER_AGENTS)

    async with async_playwright() as p:
        if not proxies:
            logger.warning("⚠️ Proxy list is empty — launching browser without proxy.")
            try:
                browser = await p.chromium.launch(
                    headless=False,
                    channel="chrome",
                    args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    # user_agent=user_agent,
                    # viewport={"width": 1280, "height": 800},
                    # locale="en-US",
                    # timezone_id="America/New_York",
                    # java_script_enabled=True,
                    # extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
                )

                page = await context.new_page()
                await stealth_async(page)

                result = await task_func(page)
                await human_like_activity(page)

                await context.close()
                await browser.close()

                logger.info("✅ Successfully completed without proxy")
                return result

            except Exception as e:
                logger.error(f"⛔ Failed to run browser without proxy: {e}")
                return None

        else:
            for attempt, proxy in enumerate(proxies, 1):
                logger.info(f"🔁 Attempt #{attempt} with proxy {proxy['server']}")
                try:
                    browser = await p.chromium.launch(
                        headless=False,
                        slow_mo=100,
                        channel="chrome",
                        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
                        proxy=proxy
                    )

                    context = await browser.new_context(
                        user_agent=user_agent,
                        viewport={"width": 1280, "height": 800},
                        locale="en-US",
                        timezone_id="America/New_York",
                        java_script_enabled=True,
                        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
                    )

                    page = await context.new_page()
                    await stealth_async(page)

                    result = await task_func(page)
                    await human_like_activity(page)

                    await context.close()
                    await browser.close()

                    logger.info(f"✅ Successfully completed with proxy {proxy['server']}")
                    return result

                except Exception as e:
                    logger.warning(f"❌ Failed with proxy {proxy['server']}: {e}")
                    try:
                        await browser.close()
                    except Exception:
                        pass

            logger.error("⛔ All proxies from file have been tried — task failed.")
            return None
