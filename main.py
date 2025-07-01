import asyncio
import logging

from core.browser import run_browser
from scrapers import newegg
from core.logger import get_logger

logger = get_logger(__name__)

async def main():


    scraped_data = await run_browser(newegg.task)

    if scraped_data:
        logger.info(f"📦 Data scraped, total products: {len(scraped_data)}")
        # Here you can save the result, for example, to JSON
        import json
        with open("output/newegg_products.json", "w", encoding="utf-8") as f:
            json.dump(scraped_data, f, ensure_ascii=False, indent=4)
        logger.info("📦 Data saved to output/newegg_products.json")
    else:
        logger.error("❌ Scraping failed with all proxies.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    asyncio.run(main())
