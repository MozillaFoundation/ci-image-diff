"""
In order to get meaningful diffs, do not feed this JPEG images. The block compression is going
to flag about a million differences that aren't actually there. Use a bitmap format like PNG.
"""

import sys
import argparse
import importlib
utils = importlib.import_module('utils')

parser = argparse.ArgumentParser(description='Diff two (bitmap) images.')
parser.add_argument('original', help='The path for the original image.')
parser.add_argument('new', help='The path for the new image.')
parser.add_argument('-o', '--match-origin', action='store_true', help='Try to detect relocated content.')
parser.add_argument('-p', '--max-passes', type=int, default=5, help="The maximum number of diff-merge passes. defaults to 5.")
parser.add_argument('-r', '--result-path', default='results', help="The dir to write the comparison results to. defaults to results.")
parser.add_argument('-s', '--silent', action='store_true', help="Do not log progress to stdout.")
parser.add_argument('-t', '--terse-logging', action='store_true', help="Only log diff pass/fail result.")
parser.add_argument('-w', '--write', action='store_true', help='Write the highlighted images to disk.')
args = parser.parse_args()

image_pair = utils.make_same_size(
	utils.loadImage(args.original),
	utils.loadImage(args.new)
)

if args.terse_logging is True:
	args.silent = True

diffs = utils.perform_diffing(image_pair, args.write, args.result_path, args.match_origin, args.max_passes, args.terse_logging, args.silent)

if diffs is not None:
	if args.silent is False:
		print(f'{len(diffs)} differences found.')
	sys.exit(1)
