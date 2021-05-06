"""
In order to get meaningful diffs, do not feed this JPEG images. The block compression is going
to flag about a million differences that aren't actually there. Use a bitmap format like PNG.
"""

import argparse
import importlib
utils = importlib.import_module('utils')

parser = argparse.ArgumentParser(description='Diff two (bitmap) images.')
parser.add_argument('original', help='The path for the original image.')
parser.add_argument('new', help='The path for the new image.')
parser.add_argument('-w', '--write', default='diff', help='write the highlighted images to disk.')
args = parser.parse_args()

imageA, imageB = utils.make_same_size(
	utils.loadImage(args.original),
	utils.loadImage(args.new)
)

utils.perform_diffing(imageA, imageB, args.write)
