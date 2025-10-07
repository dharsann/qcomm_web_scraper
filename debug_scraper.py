# backend/debug_scraper.py
import asyncio
from playwright.async_api import async_playwright

async def debug_selectors():
    """Debug script to inspect search inputs on each platform"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Visible browser for debugging
        context = await browser.new_context()

        platforms = {
            'instamart': 'https://www.swiggy.com/instamart',
            'blinkit': 'https://blinkit.com/',
            'zepto': 'https://www.zeptonow.com/'
        }

        for platform, url in platforms.items():
            print(f"\n🔍 Debugging {platform}...")
            page = await context.new_page()

            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_timeout(3000)

                # Find all input elements
                inputs = await page.query_selector_all('input')
                print(f"  Found {len(inputs)} input elements:")

                for i, inp in enumerate(inputs):
                    try:
                        tag = await inp.evaluate('el => el.outerHTML')
                        placeholder = await inp.get_attribute('placeholder') or ''
                        name = await inp.get_attribute('name') or ''
                        type_attr = await inp.get_attribute('type') or ''
                        aria_label = await inp.get_attribute('aria-label') or ''

                        print(f"    {i+1}. Placeholder: '{placeholder}' | Name: '{name}' | Type: '{type_attr}' | Aria-label: '{aria_label}'")
                        if len(tag) < 200:
                            print(f"        HTML: {tag}")
                    except:
                        continue

                # Let user inspect manually
                input(f"  Press Enter after inspecting {platform} page...")

            except Exception as e:
                print(f"  ❌ Error: {e}")

            await page.close()

        await browser.close()

if __name__ == '__main__':
    asyncio.run(debug_selectors())