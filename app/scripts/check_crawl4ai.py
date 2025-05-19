import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def test_url_crawling(url: str):
    print(f"--- Testing URL: {url} ---")
    try:
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS
        )
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=run_config)

        if result.success and result.markdown:
            print(f"Successfully fetched URL: {url}")
            print(f"Markdown length: {len(result.markdown.raw_markdown)}")
            print(f"Markdown content (first 100 chars): '{result.markdown.raw_markdown[:100]}'")
        elif not result.success:
            print(f"Failed to fetch URL: {url}. Error: {result.error_message}")
        else:
            print(f"Fetched URL: {url} successfully, but no markdown content was generated.")
        
    except Exception as e:
        print(f"Unexpected error testing URL {url}: {e}")
    print("----------------------------\n")

async def main():
    urls_to_test = [
        "https://example.com",
        "https://www.google.com",
        "https://www.wikipedia.org",
        "https://docs.crawl4ai.com/core/quickstart/", # A page we know has content
        "https://berlinhouse.com" # The problematic URL
        # Add any other URLs you want to test here
    ]

    for url in urls_to_test:
        await test_url_crawling(url)

if __name__ == "__main__":
    asyncio.run(main()) 