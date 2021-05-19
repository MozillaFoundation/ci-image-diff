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
import math
import argparse
import asyncio

from pathlib import Path
from shutil import copyfile
from distutils.dir_util import copy_tree
from playwright.async_api import async_playwright

parser = argparse.ArgumentParser(description='Create diff sets for web pages, and view those difference in the browser.')
parser.add_argument('url', nargs='?', help='The URL for the web page.')
parser.add_argument('-b', '--base-dir', default='diffs', help='Directory for diffs. Defaults to diffs.')
parser.add_argument('-c', '--compare', default='compare', help='Save screenshots to the indicated dir. Defaults to compare.')
parser.add_argument('-co', '--compare-only', action='store_true', help='Do not (re)fetch screenshots.')
parser.add_argument('-g', '--ground-truth', default='main', help='Set the ground truth dir. Defaults to main.')
parser.add_argument('-i', '--stability-interval', type=int, default=1000, help='Set the "is DOM stable?" test interval in milliseconds. Defaults to 1000.')
parser.add_argument('-l', '--list', help='Read list of URLs to test from a plain text, newline delimited file.')
parser.add_argument('-m', '--missing-error', action='store_true', help='Treat missing ground truth screenshot as error.')
parser.add_argument('-o', '--match-origin', action='store_true', help='Try to detect relocated content when analysing diffs.')
parser.add_argument('-p', '--log-path-only', action='store_true', help='Only log which path is being compared, rather than image locations.')
parser.add_argument('-q', '--queue-size', type=int, default=10, help='Sets the number of concurrent network requests in the batch queue. Defaults to 10')
parser.add_argument('-r', '--result-dir', default='results', help='Directory for comparison results. Defaults to results.')
parser.add_argument('-u', '--update', action='store_true', help='Update the ground truth screenshots.')
parser.add_argument('-v', '--verbose', action='store_true', help="Log progress to stdout.")
parser.add_argument('-vx', '--verbose-exclusive', action='store_true', help="Log progress, but skip logging of each diff process.")
parser.add_argument('-w', '--width', type=str, default='1200', help='The browser width in pixels. Defaults to 1200.')
parser.add_argument('-z', '--server-hint', action='store_true', help="Print the diff viewer instructions at the end of the run.")
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

# master list of open browsers, for closing once done
open_browsers = []

# how verbose are we?
if args.verbose_exclusive:
    args.verbose = True

LOG_VERBOSE = args.verbose

def log_info(*args):
	if LOG_VERBOSE is False:
		return
	print(*args)

def path_safe(str):
    return str.replace(':', '-').replace('@','-')


async def content_is_stable(page):
    """
    Ideally we do this using screenshots, see https://github.com/MozillaFoundation/ci-image-diff/issues/21
    """
    attempt = 0
    previous_html = ''

    while attempt < 10:
        attempt += 1

        html = await page.query_selector("html")
        inner_html = await html.inner_html()

        if inner_html == previous_html:
            # Page has stabilised
            return True

        previous_html = inner_html
        await asyncio.sleep(args.stability_interval / 1000)

    # Page has *not* stabilised but we've run out of attempts.
    return False


async def capture_screenshot_for_url_at_width(p, browser, browser_type, url_path, page_url, page_width):
    browser_name = browser_type.name

    # Create a new viewport, size it to the correct width, and navigate to the URL we want to capture.
    page = await browser.new_page()
    await page.set_viewport_size({ 'width': page_width, 'height': 800 })

    log_info(f'Navigating to {page_url} using {browser_name} at size {page_width}, url:', url_path)
    await page.goto(page_url)

    # Rather than relying on 'networkidle' or 'domcontentready', we wait for the page DOM to stabilize.
    await content_is_stable(page)

    # Figure out which path we need to write to, and ensure the dir for that exists.
    parent = f'./diffs/{screenshot_base_dir}/{browser_name}-{page_width}/{url_path}'
    Path(parent).mkdir(parents=True, exist_ok=True)
    image_path = f'{parent}/screenshot.png'

    log_info(f'Creating {image_path}')
    await page.screenshot(path=image_path, full_page=True)


async def capture_screenshot_for_url(p, browser, browser_type, page_widths, url_path, page_url):
    tasklist = []
    for page_width in page_widths:
        tasklist.append(lambda:
            capture_screenshot_for_url_at_width(
                p,
                browser,
                browser_type,
                url_path,
                page_url,
                page_width
            )
        )
    return tasklist


async def capture_screenshots_for(p, browser_type, page_widths, urls, url_paths):
    browser_name = browser_type.name
    browser = await browser_type.launch(headless=True)
    open_browsers.append(browser)

    log_info(f'Creating captures schedule for {browser_name}')

    tasklist = []
    for (i, page_url) in enumerate(url_list):
        tasks = await capture_screenshot_for_url(
            p,
            browser,
            browser_type,
            page_widths,
            path_safe(url_paths[i]),
            page_url,
        )
        tasklist.extend(tasks)

    log_info(f'Scheduled {len(tasklist)} captures for {browser_name}')
    return tasklist


async def call_diff_script(base_dir, result_dir, ground_truth_dir, compare_dir, url_path, browser_name, width, failures):
    url_path = path_safe(url_path)

    image_path = f'{browser_name}-{width}/{url_path}/screenshot.png'
    ground_truth = f'./{base_dir}/{ground_truth_dir}/{image_path}'

    if os.path.exists(ground_truth) is False:
        log_info(f'Cannot find {ground_truth} - skipping compare for {browser_name} at {width}px')

        if args.missing_error is True:
            failures.append(url_path)

        return

    compare = f'./{base_dir}/{compare_dir}/{image_path}'

    result_path = f'./{result_dir}/{compare_dir}/{browser_name}-{width}/{url_path}'
    Path(result_path).mkdir(parents=True, exist_ok=True)
    cmd = f'{sys.executable} diff.py -w -r {result_path} {ground_truth} {compare}'

    # are we comparing with relocation detection?
    if args.match_origin:
        cmd = f'{cmd} -o'

    # what level of logging do we need for the diff.py call?
    if args.verbose == False or args.verbose_exclusive == True:
        if args.log_path_only is True:
            # no logging except for the diff pass/fail result
            cmd = f'{cmd} -t'
        else:
            # no logging at all
            cmd = f'{cmd} -s'



    if args.log_path_only is True:
        log_info(f'\ncomparing screenshots for {url_path} as taken by {browser_name} at {width}px...')
    else:
        log_info(f'\ncalling {cmd}')

    return_code = os.system(cmd)

    if return_code != 0:
        copyfile(compare, compare.replace(f'{base_dir}/', f'{result_dir}/'))
        failures.append(url_path)


async def compare_screenshots(base_dir, result_dir, ground_truth_dir, compare_dir, url_paths, browser_name, width):
    failures = []

    copy_tree(f'./{base_dir}/{ground_truth_dir}', f'./{result_dir}/{ground_truth_dir}')

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


async def process_tasks(tasks, batch_size):
    work_queue = []
    batch_count = math.ceil(len(tasks) / batch_size)
    batch = 1
    while len(tasks) > 0:
        log_info(f'[{batch}/{batch_count}] fetching URLs')
        batch = batch + 1
        work_queue = [
            asyncio.create_task(task())
            for task in tasks[:batch_size]
        ]
        tasks = tasks[batch_size:]
        await asyncio.gather(*work_queue)
        # let's see if this improves logging responsiveness in github actions
        asyncio.sleep(3000 / 1000)


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
            tasklist = []

            log_info('Setting up capture list')
            for browser_type in browsers:
                tasks = await capture_screenshots_for(
                    p,
                    browser_type,
                    page_widths,
                    urls,
                    url_paths
                )
                tasklist.extend(tasks)

            log_info('Executing captures')
            await process_tasks(tasklist, args.queue_size)

            log_info('Finished captures.')
            for browser in open_browsers:
                await browser.close()

        # TODO: we can almost certainly parallelise all diffing tasks
        if not args.update:
            log_info("comparing screenshots")
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

            if failures > 0 and args.server_hint:
                log_info(f'\nVisual diffs found in {failures} screenshots')
                log_info(f'run:\n    python -m http.server --directory {args.result_dir} 8080')
                log_info(f'then open:\n    http://localhost:8080/?reference={args.ground_truth}&compare={args.compare}')
                sys.exit(failures)


if len(url_list) == 0:
    parser.print_help()
else:
    asyncio.run(capture_screenshots(url_list))
