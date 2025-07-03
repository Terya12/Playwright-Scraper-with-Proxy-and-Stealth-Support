import asyncio
import random
from pathlib import Path
from typing import Callable, Optional, Any, Dict
from patchright.async_api import async_playwright, Page, Playwright, Browser
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
    if not PROXY_FILE.exists():
        logger.warning(f"⚠️ Proxy file not found at {PROXY_FILE}")
        return proxies
    try:
        with open(PROXY_FILE, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) == 2:  # host:port
                    host, port = parts
                    proxies.append({"server": f"http://{host}:{port}"})
                elif len(parts) == 4:  # host:port:user:password
                    host, port, user, password = parts
                    proxies.append({
                        "server": f"http://{host}:{port}",
                        "username": user,
                        "password": password
                    })
    except Exception as e:
        logger.error(f"❌ Failed to load proxies: {e}")
    return proxies


async def human_like_activity(page: Page):
    """Simulate basic human-like behavior to bypass bot detection."""
    for _ in range(3):
        await page.mouse.move(random.randint(100, 1000), random.randint(100, 700))
        await asyncio.sleep(random.uniform(0.5, 1.2))
        await page.keyboard.press("PageDown")
        await asyncio.sleep(random.uniform(1, 2))


async def _launch_browser_instance(p: Playwright, user_agent: str, proxy: Optional[Dict[str, str]] = None) -> Browser:
    """Launches a browser instance with the specified configuration."""
    browser_args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    launch_options = {
        "headless": False,
        "channel": "chrome",
        "args": browser_args,
    }
    if proxy:
        launch_options["proxy"] = proxy
        launch_options["slow_mo"] = 100

    return await p.chromium.launch(**launch_options)


async def run_browser(task_func: Callable[[Page], Any]) -> Optional[Any]:
    logger.info("🚀 Launching browser...")
    proxies = load_proxies_from_file()
    user_agent = random.choice(USER_AGENTS)

    async with async_playwright() as p:
        if not proxies:
            logger.warning("⚠️ Proxy list is empty or file not found — launching browser without proxy.")
            browser = None
            try:
                browser = await _launch_browser_instance(p, user_agent)
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

                logger.info("✅ Successfully completed without proxy")
                return result
            except Exception as e:
                logger.error(f"⛔ Failed to run browser without proxy: {e}")
                return None
            finally:
                if browser:
                    await browser.close()
        else:
            logger.info(f"🔗 Found {len(proxies)} proxies. Starting rotation.")
            for attempt, proxy_config in enumerate(proxies, 1):
                proxy_server = proxy_config.get('server')
                logger.info(f"🔁 Attempt #{attempt} with proxy {proxy_server}")
                browser = None
                try:
                    browser = await _launch_browser_instance(p, user_agent, proxy_config)
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

                    logger.info(f"✅ Successfully completed with proxy {proxy_server}")
                    return result
                except Exception as e:
                    logger.warning(f"❌ Failed with proxy {proxy_server}: {e}")
                    if browser:
                        await browser.close()
                finally:
                    if browser and not browser.is_closed():
                        await browser.close()

            logger.error("⛔ All proxies from file have been tried — task failed.")
            return None
