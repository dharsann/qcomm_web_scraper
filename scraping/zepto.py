# backend/scraping/zepto.py
import asyncio
import re
from playwright.async_api import Page

class ZeptoScraper:
    def __init__(self):
        self.base_url = 'https://www.zeptonow.com/'
        
    def clean_price(self, price_text: str) -> float:
        """Extract numeric price from text"""
        if not price_text:
            return 0.0
        price_match = re.search(r'₹?\s*(\d+(?:,\d+)?(?:\.\d+)?)', price_text)
        if price_match:
            return float(price_match.group(1).replace(',', ''))
        return 0.0
    
    def clean_weight(self, weight_text: str) -> str:
        """Standardize weight format"""
        if not weight_text:
            return ""
        weight_text = weight_text.lower()
        match = re.search(r'(\d+(?:\.\d+)?)\s*(g|kg|ml|l|gm|gram|piece|pcs)', weight_text)
        if match:
            value, unit = match.groups()
            if unit in ['g', 'gm', 'gram']:
                return f"{value}g"
            elif unit in ['kg']:
                return f"{value}kg"
            elif unit in ['piece', 'pcs']:
                return f"{value}pc"
        return weight_text
    
    def extract_brand(self, product_name: str) -> str:
        """Extract brand name from product name"""
        brands = [
            'Britannia', 'Modern', 'Harvest Gold', 'Bread World', 
            'English Oven', 'Milk Bread', 'Kitty', 'Bonn',
            'Fresho', 'BBPopular', 'Monginis', 'Wibs'
        ]
        
        product_lower = product_name.lower()
        for brand in brands:
            if brand.lower() in product_lower:
                return brand
        
        words = product_name.split()
        if words:
            return words[0]
        return "Unknown"
    
    async def scrape(self, page: Page) -> list:
        """Scrape bread products from Zepto"""
        print('🟣 Scraping Zepto...')
        
        try:
            await page.goto(self.base_url, timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Handle location
            try:
                location_input = page.locator('input[placeholder*="delivery location" i]').first
                await location_input.fill('Mumbai', timeout=3000)
                await page.wait_for_timeout(1000)
                await page.keyboard.press('ArrowDown')
                await page.keyboard.press('Enter')
                await page.wait_for_timeout(2000)
            except:
                print("  Location already set")
            
            # Search for bread
            search_selectors = [
                'input[placeholder*="product" i]',
                'input[aria-label*="search" i]',
                '[class*="search-bar"] input',
                '[class*="product-search"] input',
                'input[type="search"]',
                'input[name*="search" i]',
                '[class*="search"] input',
                '[data-testid*="search"] input'
            ]

            search_box = None
            for selector in search_selectors:
                try:
                    candidates = page.locator(selector)
                    count = await candidates.count()
                    if count > 0:
                        # Take the first one that's not location-related
                        for i in range(count):
                            candidate = candidates.nth(i)
                            placeholder = await candidate.get_attribute('placeholder') or ''
                            if 'location' not in placeholder.lower():
                                search_box = candidate
                                print(f"  Found search input with placeholder: {placeholder}")
                                break
                        if search_box:
                            break
                except:
                    continue

            if not search_box:
                print("  Could not find product search box")
                return []

            await search_box.fill('bread')
            await page.keyboard.press('Enter')
            await page.wait_for_timeout(3000)
            
            # Scroll to load more products
            for _ in range(3):
                await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                await page.wait_for_timeout(1500)
            
            # Extract products
            products = await page.evaluate('''() => {
                const items = [];
                const selectors = [
                    'div[class*="Product"]',
                    '[data-testid*="product"]',
                    'div[class*="product-card"]'
                ];
                
                let productElements = [];
                for (const selector of selectors) {
                    productElements = document.querySelectorAll(selector);
                    if (productElements.length > 0) break;
                }
                
                productElements.forEach((card) => {
                    const nameEl = card.querySelector('h4, h3, [class*="name"], [class*="title"]');
                    const priceEl = card.querySelector('[class*="price"]');
                    const weightEl = card.querySelector('[class*="weight"], [class*="quantity"], [class*="size"]');
                    const imageEl = card.querySelector('img');
                    
                    const name = nameEl?.innerText?.trim();
                    const price = priceEl?.innerText?.trim();
                    
                    if (name && price && name.toLowerCase().includes('bread')) {
                        items.push({
                            name: name,
                            price: price,
                            weight: weightEl?.innerText?.trim() || '',
                            image: imageEl?.src || ''
                        });
                    }
                });
                
                return items;
            }''')
            
            # Clean and process
            processed_products = []
            for product in products:
                processed_products.append({
                    'name': product['name'],
                    'brand': self.extract_brand(product['name']),
                    'weight': product['weight'],
                    'weight_clean': self.clean_weight(product['weight']),
                    'price': product['price'],
                    'price_numeric': self.clean_price(product['price']),
                    'image': product['image'],
                    'platform': 'Zepto'
                })
            
            print(f"  ✅ Found {len(processed_products)} bread products")
            return processed_products
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return []