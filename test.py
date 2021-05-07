"""
Test script requires:

- argparse
- playwright

"""

import os
import re
import sys
import argparse
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

import importlib
utils = importlib.import_module('utils')

parser = argparse.ArgumentParser(description='Take a screenshot of a web page.')
parser.add_argument('url', nargs='?', help='The URL for the web page.')
parser.add_argument('-c', '--compare', default='compare', help='Save screenshots to the indicated dir. Defaults to compare.')
parser.add_argument('-co', '--compare-only', action='store_true', help='Do not (re)fetch screenshots.')
parser.add_argument('-g', '--ground-truth', default='main', help='Set the ground truth dir. Defaults to main.')
parser.add_argument('-l', '--list', help='Read list of URLs to test from a plain text, newline delimited file.')
parser.add_argument('-u', '--update', action='store_true', help='Update the ground truth screenshots.')
parser.add_argument('-w', '--width', type=int, default='1200', help='The browser width in pixels. Defaults to 1200.')
args = parser.parse_args()

# Form the list of URLs we need to gather screenshots for
url_stripper = re.compile(r"https?://(www\.)?")
url_list = []
if args.list:
    data = open(args.list, 'r')
    for line in data:
        url_list.append(line.strip())
else:
    url_list.append(args.url)

# Which directory are we writing files to?
screenshot_base_dir = args.ground_truth if args.update else args.compare


async def capture_screenshots_for(p, browser_type, urls, url_paths, asyncio_queue):
    browser_name = browser_type.name
    browser = await browser_type.launch(headless=True)

    print(f'Starting captures for {browser_name}')

    for (i, page_url) in enumerate(url_list):
        print(f'Navigating to {page_url} using {browser_name}')
        page = await browser.new_page()
        await page.set_viewport_size({ 'width': args.width, 'height': 800 })
        await page.goto(page_url)

        # It would be lovely if Webkit actually, you know, worked like everything else...
        wait_type = 'networkidle' if browser_type is not p.webkit else 'domcontentloaded'
        await page.wait_for_load_state(wait_type)

        # Figure out which path we need to write to, and ensure the dir for that exists.
        parent = f'./diffs/{screenshot_base_dir}/{url_paths[i]}'
        Path(parent).mkdir(parents=True, exist_ok=True)
        image_name = f'{browser_name}-{args.width}.png'
        image_path = f'{parent}/{image_name}'

        print(f'Creating {image_path}')
        await page.screenshot(path=image_path, full_page=True)

    await browser.close()
    print(f'Fininshed capturing for {browser_name}')
    asyncio_queue.task_done()


async def capture_screenshots(urls):
    """
    Perform capturing in parallel, so that all browsers can
    capture screenshots at their own pace without blocking
    each other's execution.
    """

    async with async_playwright() as p:
        browsers = [p.chromium, p.firefox]  # we don't include p.webkit because it's just too fickle
        url_paths = [url_stripper.sub('', u.strip()).strip('/') for u in url_list]

        if not args.compare_only:
            asyncio_queue = asyncio.Queue()
            tasks = []

            for browser_type in browsers:
                task = asyncio.create_task(capture_screenshots_for(p, browser_type, urls, url_paths, asyncio_queue))
                tasks.append(task)

            print('Starting captures')
            await asyncio_queue.join()
            await asyncio.gather(*tasks, return_exceptions=True)

        # TODO: we can almost certainly parallelise all diffing tasks
        if not args.update:
            print("comparing screenshots")
            for browser_type in browsers:
                compare_screenshots('diffs', args.ground_truth, args.compare, url_paths, browser_type.name, args.width)


def compare_screenshots(base_dir, ground_truth_dir, compare_dir, url_paths, browser_name, width):
    for url_path in url_paths:
        image_path = f'{url_path}/{browser_name}-{width}.png'
        ground_truth = f'./{base_dir}/{ground_truth_dir}/{image_path}'
        compare = f'./{base_dir}/{compare_dir}/{image_path}'

        result_path = f'./results/{url_path}/{browser_name}-{width}'
        Path(result_path).mkdir(parents=True, exist_ok=True)
        cmd = f'{sys.executable} diff.py -w -r {result_path} {ground_truth} {compare}'

        print(f'calling {cmd}')
        os.system(cmd)


if len(url_list) == 0:
    parser.print_help()
else:
    asyncio.run(capture_screenshots(url_list))
