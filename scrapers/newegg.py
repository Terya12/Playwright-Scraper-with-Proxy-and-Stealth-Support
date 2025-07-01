import json
from pathlib import Path
from playwright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.newegg.com/p/pl?d=laptop"
OUTPUT_FILE = Path("output/newegg_products.json")
UNIQUE_KEY = "link"  # Can be replaced with "title" or another unique field

def load_existing_items() -> list:
    """Load previously saved items from output file."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_unique_items(new_items: list):
    """Save new unique items by filtering out duplicates based on UNIQUE_KEY."""
    existing_items = load_existing_items()
    existing_links = {item[UNIQUE_KEY] for item in existing_items}

    deduplicated = []
    duplicates_count = 0

    for item in new_items:
        if item[UNIQUE_KEY] in existing_links:
            logger.warning(f"⚠️ Duplicate found and skipped: {item[UNIQUE_KEY]}")
            duplicates_count += 1
        else:
            deduplicated.append(item)

    combined = existing_items + deduplicated

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    logger.info(f"📦 Added new products: {len(deduplicated)} (total saved: {len(combined)}). Duplicates skipped: {duplicates_count}")

async def get_total_pages(page: Page) -> int:
    logger.info("\U0001F50D Determining total number of pages...")
    await page.goto(BASE_URL, timeout=60000)

    # Check for Cloudflare block
    if await page.locator(".page-content.page-404").count():
        raise Exception("⛔ Access blocked by Cloudflare (404 page)")

    try:
        await page.wait_for_selector(".list-tool-pagination-text", timeout=60000)
        pagination_texts = await page.locator(".list-tool-pagination-text strong").all_inner_texts()
        if len(pagination_texts) >= 2:
            total_pages = int(pagination_texts[1].split("/")[-1])
            logger.info(f"📄 Found total pages: {total_pages}")
            return total_pages
    except Exception as e:
        logger.warning(f"⚠️ Could not determine total pages: {e}")
    return 1

async def scrape_products_on_page(page: Page, page_num: int):
    url = f"{BASE_URL}&page={page_num}"
    logger.info(f"➡️ Navigating to page {page_num}: {url}")
    await page.goto(url, timeout=60000)

    # Check for Cloudflare block
    if await page.locator(".page-content.page-404").count():
        raise Exception("⛔ Access blocked by Cloudflare (404 page)")

    await page.wait_for_selector(".item-cell", timeout=20000)
    logger.info("Page loaded, starting scraping")

    products = await page.locator(".item-cell").all()
    logger.info(f"Found products: {len(products)}")

    result = []
    for product in products:
        title = await product.locator(".item-title").inner_text() if await product.locator(".item-title").count() else ""
        price = await product.locator(".price-current").inner_text() if await product.locator(".price-current").count() else ""
        link = await product.locator(".item-title").get_attribute("href") if await product.locator(".item-title").count() else ""

        result.append({
            "title": title.strip(),
            "price": price.strip(),
            "link": link.strip() if link else ""
        })

    logger.info(f"Scraping finished. Collected products: {len(result)}")
    return result

async def task(page: Page):
    total_pages = await get_total_pages(page)
    all_results = []
    for page_num in range(1, total_pages + 1):
        page_result = await scrape_products_on_page(page, page_num)
        all_results.extend(page_result)

    save_unique_items(all_results)
    return all_results
