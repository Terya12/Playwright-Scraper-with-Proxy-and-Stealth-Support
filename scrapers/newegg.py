import asyncio
import json
from pathlib import Path
from patchright.async_api import Page
from core.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://www.newegg.com/p/pl?d=laptop"
OUTPUT_FILE = Path("output/newegg_products.json")
UNIQUE_KEY = "link"  # Can be replaced with "title" or another unique field

def load_existing_items() -> set:
    """Load unique keys of previously saved items from output file."""
    if not OUTPUT_FILE.exists():
        return set()
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # Flatten the list in case of nested lists from previous runs
            flat_list = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, list):
                        flat_list.extend(item)
                    elif isinstance(item, dict):
                        flat_list.append(item)
            
            return {item.get(UNIQUE_KEY) for item in flat_list if isinstance(item, dict) and item.get(UNIQUE_KEY)}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading existing items: {e}")
        return set()

def append_items_to_json(new_items: list):
    """Append new unique items to the existing JSON file."""
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_data = []
    if OUTPUT_FILE.exists() and OUTPUT_FILE.stat().st_size > 0:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    logger.warning("Output file is not a list. Starting fresh.")
                    existing_data = []
            except json.JSONDecodeError:
                logger.warning("Could not decode JSON, starting fresh.")
                existing_data = []

    # Flatten the list in case of nested lists from previous runs
    flat_list = []
    for item in existing_data:
        if isinstance(item, list):
            flat_list.extend(item)
        else:
            flat_list.append(item)
    
    flat_list.extend(new_items)

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(flat_list, f, ensure_ascii=False, indent=2)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to save items: {e}")


async def get_total_pages(page: Page) -> int:
    logger.info("\U0001F50D Determining total number of pages...")
    try:
        await page.goto(BASE_URL, timeout=60000)
        if "403 Forbidden" in await page.title():
             raise Exception("⛔ Access forbidden (403 Forbidden page)")
        if await page.locator(".page-content.page-404").count():
            raise Exception("⛔ Access blocked by Cloudflare (404 page)")

        pagination_text_element = page.locator(".list-tool-pagination-text strong").last
        await pagination_text_element.wait_for(timeout=15000)
        total_pages_text = await pagination_text_element.inner_text()
        total_pages = int(total_pages_text.split("/")[-1])
        logger.info(f"📄 Found total pages: {total_pages}")
        return total_pages
    except Exception as e:
        logger.warning(f"⚠️ Could not determine total pages, defaulting to 1. Reason: {e}")
        return 1

async def scrape_products_on_page(page: Page, page_num: int):
    url = f"{BASE_URL}&page={page_num}"
    logger.info(f"➡️ Navigating to page {page_num}: {url}")
    await page.goto(url, timeout=60000)

    await page.wait_for_selector(".item-cell", timeout=20000)
    product_items = await page.locator(".item-cell").all()
    logger.info(f"Found {len(product_items)} products on page {page_num}")

    async def extract(product):
        try:
            title_element = product.locator(".item-title")
            price_element = product.locator(".price-current")
            title = await title_element.inner_text()
            price = await price_element.inner_text()
            link = await title_element.get_attribute("href")
            return {
                "title": title.strip(),
                "price": price.strip(),
                "link": link.strip() if link else ""
            }
        except Exception as e:
            logger.error(f"Failed to extract product data: {e}")
            return None

    tasks = [extract(p) for p in product_items]
    results = await asyncio.gather(*tasks)
    return [item for item in results if item]

async def task(page: Page):
    total_pages = await get_total_pages(page)
    if total_pages == 0:
        return []

    existing_links = load_existing_items()
    all_new_products = []

    for page_num in range(1, total_pages + 1):
        try:
            logger.info(f"Scraping page {page_num}/{total_pages}")
            page_products = await scrape_products_on_page(page, page_num)

            new_products_on_page = []
            for product in page_products:
                if product[UNIQUE_KEY] not in existing_links:
                    new_products_on_page.append(product)
                    existing_links.add(product[UNIQUE_KEY])
                else:
                    logger.warning(f"⚠️ Duplicate found and skipped: {product[UNIQUE_KEY]}")

            if new_products_on_page:
                append_items_to_json(new_products_on_page)
                all_new_products.extend(new_products_on_page)
                logger.info(f"📦 Saved {len(new_products_on_page)} new products from page {page_num}")

        except Exception as e:
            logger.error(f"❌ Error scraping page {page_num}: {e}")
            continue # Continue to next page

    logger.info(f"✅ Scraping finished. Total new products saved: {len(all_new_products)}")
    return all_new_products
