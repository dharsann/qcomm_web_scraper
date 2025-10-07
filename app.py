# backend/app.py
from flask import Flask, jsonify, request
import asyncio
import pandas as pd
from scraping.instamart import InstamartScraper
from scraping.blinkit import BlinkitScraper
from scraping.zepto import ZeptoScraper
from models import ProductMatcher
from utils import DataExporter, PriceAnalyzer
from playwright.async_api import async_playwright

app = Flask(__name__)

scrapers = {
    'instamart': InstamartScraper(),
    'blinkit': BlinkitScraper(),
    'zepto': ZeptoScraper()
}

scraped_data = []

@app.route('/')
def home():
    return jsonify({
        'message': 'Bread Price Comparison API',
        'endpoints': {
            'GET /': 'This help',
            'POST /scrape': 'Scrape bread prices from all platforms',
            'GET /compare': 'Compare prices and find matches',
            'POST /export': 'Export data to file'
        }
    })

@app.route('/scrape', methods=['POST'])
async def scrape():
    global scraped_data
    scraped_data = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        try:
            for platform, scraper in scrapers.items():
                page = await context.new_page()
                try:
                    data = await scraper.scrape(page)
                    scraped_data.extend(data)
                    print(f"Scraped {len(data)} products from {platform}")
                except Exception as e:
                    print(f"Error scraping {platform}: {e}")
                finally:
                    await page.close()

        finally:
            await browser.close()

    return jsonify({
        'message': f'Scraped {len(scraped_data)} products total',
        'platforms': list(scrapers.keys())
    })

@app.route('/compare')
def compare():
    if not scraped_data:
        return jsonify({'error': 'No data scraped yet. Call /scrape first'}), 400

    df = pd.DataFrame(scraped_data)

    # Get matches
    matches = ProductMatcher.match_products(df)
    best_deals = ProductMatcher.get_best_deals(matches)

    # Get stats
    stats = PriceAnalyzer.calculate_statistics(df)
    platform_stats = ProductMatcher.get_platform_stats(df)

    return jsonify({
        'total_products': len(scraped_data),
        'matches_found': len(matches),
        'best_deals': [m.to_dict() for m in best_deals[:10]],
        'statistics': stats,
        'platform_stats': platform_stats
    })

@app.route('/export', methods=['POST'])
def export():
    if not scraped_data:
        return jsonify({'error': 'No data scraped yet. Call /scrape first'}), 400

    format_type = request.json.get('format', 'json') if request.json else 'json'

    df = pd.DataFrame(scraped_data)

    if format_type == 'json':
        filename = DataExporter.save_to_json({'products': scraped_data})
    elif format_type == 'csv':
        filename = DataExporter.save_to_csv(df)
    elif format_type == 'excel':
        data_dict = {
            'Products': df,
            'Statistics': pd.DataFrame([PriceAnalyzer.calculate_statistics(df)])
        }
        filename = DataExporter.save_to_excel(data_dict)
    else:
        return jsonify({'error': 'Invalid format. Use json, csv, or excel'}), 400

    return jsonify({
        'message': f'Data exported to {filename}',
        'filename': filename
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)