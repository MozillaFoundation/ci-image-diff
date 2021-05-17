"""
Compare script requires:

- argparse
- playwright

"""

import os
import re
import sys
import json
import time
import argparse
import asyncio

from pathlib import Path
from shutil import copyfile
from distutils.dir_util import copy_tree
from playwright.async_api import async_playwright


parser = argparse.ArgumentParser(description='Take a screenshot of a web page.')
parser.add_argument('url', nargs='?', help='The URL for the web page.')
parser.add_argument('-b', '--base-dir', default='diffs', help='Directory for diffs. Defaults to diffs.')
parser.add_argument('-c', '--compare', default='compare', help='Save screenshots to the indicated dir. Defaults to compare.')
parser.add_argument('-co', '--compare-only', action='store_true', help='Do not (re)fetch screenshots.')
parser.add_argument('-g', '--ground-truth', default='main', help='Set the ground truth dir. Defaults to main.')
parser.add_argument('-l', '--list', help='Read list of URLs to test from a plain text, newline delimited file.')
parser.add_argument('-o', '--match-origin', action='store_true', help='Try to detect relocated content.')
parser.add_argument('-r', '--result-dir', default='results', help='Directory for comparison results. Defaults to results.')
parser.add_argument('-u', '--update', action='store_true', help='Update the ground truth screenshots.')
parser.add_argument('-w', '--width', type=str, default='1200', help='The browser width in pixels. Defaults to 1200.')
args = parser.parse_args()

# Make sure all width(s) are numbers
page_widths = args.width
page_widths = page_widths.split(',') if ',' in page_widths else [page_widths]
page_widths = [int(v) for v in page_widths]

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


def path_safe(str):
    return str.replace(':', '-').replace('@','-')


async def content_is_stable(page_inner_html, page_width, page):
    """
    Ideally we do this using screenshots, see https://github.com/MozillaFoundation/ci-image-diff/issues/21
    """
    attempt = 0

    while attempt < 10:
        attempt += 1

        html = await page.query_selector("html")
        inner_html = await html.inner_html()
        previous_inner_html = page_inner_html.get(str(page_width), '')

        if inner_html == previous_inner_html:
            # Page has stabilised
            return True

        page_inner_html[str(page_width)] = inner_html
        await asyncio.sleep(2)

    # Page has *not* stabilised but we've run out of attempts.
    return False


async def capture_screenshot_for_url(p, browser, browser_type, page_widths, url_path, page_url):
    browser_name = browser_type.name

    page_inner_html = {}

    for page_width in page_widths:
        print(f'Navigating to {page_url} using {browser_name} at size {page_width}, url:', url_path)
        page = await browser.new_page()

        # Size the viewport and navigate to the URL we want to capture.
        await page.set_viewport_size({ 'width': page_width, 'height': 800 })
        await page.goto(page_url)

        # Rather than relying on 'networkidle' or 'domcontentready', we wait for the page DOM to stabilize.
        await content_is_stable(page_inner_html, page_width, page)

        # Figure out which path we need to write to, and ensure the dir for that exists.
        parent = f'./diffs/{screenshot_base_dir}/{browser_name}-{page_width}/{url_path}'
        Path(parent).mkdir(parents=True, exist_ok=True)
        image_path = f'{parent}/screenshot.png'

        print(f'Creating {image_path}')
        await page.screenshot(path=image_path, full_page=True)


async def capture_screenshots_for(p, browser_type, page_widths, urls, url_paths):
    browser_name = browser_type.name
    browser = await browser_type.launch(headless=True)

    print(f'Initialising captures for {browser_name}')
    screenshot_tasks = []
    for (i, page_url) in enumerate(url_list):
        task = asyncio.create_task(
            capture_screenshot_for_url(
                p,
                browser,
                browser_type,
                page_widths,
                path_safe(url_paths[i]),
                page_url,
            )
        )
        screenshot_tasks.append(task)

    print(f'Starting {len(screenshot_tasks)} captures')
    await asyncio.gather(*screenshot_tasks, return_exceptions=True)
    await browser.close()
    print(f'Fininshed capturing for {browser_name}')


async def call_diff_script(base_dir, result_dir, ground_truth_dir, compare_dir, url_path, browser_name, width, failures):
    url_path = path_safe(url_path)

    image_path = f'{browser_name}-{width}/{url_path}/screenshot.png'
    ground_truth = f'./{base_dir}/{ground_truth_dir}/{image_path}'
    compare = f'./{base_dir}/{compare_dir}/{image_path}'

    result_path = f'./{result_dir}/{compare_dir}/{browser_name}-{width}/{url_path}'
    Path(result_path).mkdir(parents=True, exist_ok=True)
    cmd = f'{sys.executable} diff.py -w -r {result_path} {ground_truth} {compare}'

    if args.match_origin:
        cmd = f'{cmd} -o'

    print(f'\ncalling {cmd}')
    return_code = os.system(cmd)
    if return_code != 0:
        copyfile(compare, compare.replace(f'{base_dir}/', f'{result_dir}/'))
        failures.append(url_path)


async def compare_screenshots(base_dir, result_dir, ground_truth_dir, compare_dir, url_paths, browser_name, width):
    failures = list()

    copy_tree(f'./{base_dir}/{ground_truth_dir}', f'./{result_dir}/{ground_truth_dir}')

    print('Running diff scripts')
    for url_path in url_paths:
        await call_diff_script(
            base_dir,
            result_dir,
            ground_truth_dir,
            compare_dir,
            url_path,
            browser_name,
            width,
            failures,
        )

    return failures

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
            tasks = []

            for browser_type in browsers:
                task = asyncio.create_task(
                    capture_screenshots_for(
                        p,
                        browser_type,
                        page_widths,
                        urls,
                        url_paths
                    )
                )
                tasks.append(task)

            print('Starting captures')
            await asyncio.gather(*tasks, return_exceptions=True)
            print('Finished captures.')

        # TODO: we can almost certainly parallelise all diffing tasks
        if not args.update:
            print("comparing screenshots")
            report = {}
            failures = 0

            for browser_type in browsers:
                for page_width in page_widths:
                    key = f'{browser_type.name}-{page_width}'
                    report[key] = await compare_screenshots(
                        args.base_dir,
                        args.result_dir,
                        args.ground_truth,
                        args.compare,
                        url_paths,
                        browser_type.name,
                        page_width
                    )
                    failures += len(report[key])

            # Save the diff report as a JSON file in the result dir for this compare branch
            result_file = open(f'./{args.result_dir}/{args.compare}/diffs.json', 'w')
            result_file.write(json.dumps(report, indent=2))
            result_file.close()

            if failures > 0:
                print(f'\nVisual diffs found in {failures} screenshots')
                print(f'run:\n    python -m http.server --directory {args.result_dir} 8080')
                print(f'then open:\n    http://localhost:8080/?reference={args.ground_truth}&compare={args.compare}')
                sys.exit(failures)


if len(url_list) == 0:
    parser.print_help()
else:
    asyncio.run(capture_screenshots(url_list))
