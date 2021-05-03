"""
Test script requires:

- argparse
- pyppeteer

"""

import sys
import argparse
import asyncio
from playwright.async_api import async_playwright

parser = argparse.ArgumentParser(description='Take a screenshot of a web page.')
parser.add_argument('url', help='The URL for the web page.')
parser.add_argument('-f', '--file', default='screenshot.png', help='The file path to save the screenshot to, defaults to "screenshot.png".')
parser.add_argument('-w', '--width', type=int, default='1200', help='The browser width in pixels, defaults to 1200.')
args = parser.parse_args()


async def main():
    async with async_playwright() as p:
        for browser_type in [p.chromium, p.firefox, p.webkit]:
            browser = await browser_type.launch(headless=True)

            print(f'Navigating to {args.url} using {browser_type.name}')
            page = await browser.new_page()
            await page.set_viewport_size({ 'width': args.width, 'height': 800 })
            await page.goto(args.url)

            # It would be lovely if Webkit actually, you know, worked like everything else
            wait_type = 'networkidle' if browser_type is not p.webkit else 'domcontentloaded'
            await page.wait_for_load_state(wait_type)

            print(f'Creating screenshot-{args.width} for {browser_type.name}')
            await page.screenshot(path=f'example-{browser_type.name}-{args.width}.png', full_page=True)
            await browser.close()
            print('')

asyncio.run(main())
