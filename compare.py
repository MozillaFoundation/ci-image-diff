"""
Compare script requires:

- argparse
- playwright

"""

import os
import re
import sys
import json
import argparse
import asyncio

from pathlib import Path
from distutils.dir_util import copy_tree
from shutil import copyfile
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


def path_safe(str):
    return str.replace(':', '-').replace('@','-')


async def capture_screenshot_for_url(p, browser, browser_type, url_path, page_url):
    browser_name = browser_type.name

    print(f'Navigating to {page_url} using {browser_name}, url_path:', url_path)
    page = await browser.new_page()
    await page.set_viewport_size({ 'width': args.width, 'height': 800 })
    await page.goto(page_url)

    # It would be lovely if Webkit actually, you know, worked like everything else...
    wait_type = 'networkidle' if browser_type is not p.webkit else 'domcontentloaded'
    await page.wait_for_load_state(wait_type)

    # Figure out which path we need to write to, and ensure the dir for that exists.
    parent = f'./diffs/{screenshot_base_dir}/{browser_name}-{args.width}/{url_path}'
    Path(parent).mkdir(parents=True, exist_ok=True)
    image_path = f'{parent}/screenshot.png'

    print(f'Creating {image_path}')
    await page.screenshot(path=image_path, full_page=True)


async def capture_screenshots_for(p, browser_type, urls, url_paths):
    browser_name = browser_type.name
    browser = await browser_type.launch(headless=True)

    print(f'Initialising captures for {browser_name}')
    screenshot_queue = asyncio.Queue()
    screenshot_tasks = []
    for (i, page_url) in enumerate(url_list):
        task = asyncio.create_task(
            capture_screenshot_for_url(
                p,
                browser,
                browser_type,
                path_safe(url_paths[i]),
                page_url,
            )
        )
        screenshot_tasks.append(task)

    print(f'Starting {len(screenshot_tasks)} captures')
    await screenshot_queue.join()
    await asyncio.gather(*screenshot_tasks, return_exceptions=True)
    await browser.close()
    print(f'Fininshed capturing for {browser_name}')


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
                task = asyncio.create_task(
                    capture_screenshots_for(
                        p,
                        browser_type,
                        urls,
                        url_paths
                    )
                )
                tasks.append(task)

            print('Starting captures')
            await asyncio_queue.join()
            await asyncio.gather(*tasks, return_exceptions=True)

        # TODO: we can almost certainly parallelise all diffing tasks
        if not args.update:
            print("comparing screenshots")
            report = {}
            failures = 0

            for browser_type in browsers:
                key = f'{browser_type.name}-{args.width}'
                report[key] = await compare_screenshots(
                    args.base_dir,
                    args.result_dir,
                    args.ground_truth,
                    args.compare,
                    url_paths,
                    browser_type.name,
                    args.width
                )
                failures += len(report[key])

            # Save the diff report as a JSON file in the result dir for this compare branch
            result_file = open(f'./{args.result_dir}/{args.compare}/diffs.json', 'w')
            result_file.write(json.dumps(report, indent=2))
            result_file.close()

            if failures > 0:
                print(f'Visual diffs found for {failures} screenshots')
                print(f'run:\n    python -m http.server --directory {args.result_dir} 8080')
                print(f'then open:\n    rhttp://localhost:8080/?reference={args.ground_truth}&compare={args.compare}')
                sys.exit(failures)



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


if len(url_list) == 0:
    parser.print_help()
else:
    asyncio.run(capture_screenshots(url_list))
