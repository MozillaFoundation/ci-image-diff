"""
Diffing requirements:

- opencv-python
- scikit-image
- imutils
"""

import cv2
import numpy as np
import imutils
from skimage.metrics import structural_similarity

BLACK = (0,0,0)
WHITE = (255,255,255)
RED = (0,0,255)
GREEN = (0,255,0)
BLUE = (255,0,0)

def loadImage(path):
	"""
	Load an image, or explain why that wasn't possible
	"""
	try:
		image = cv2.imread(path, cv2.IMREAD_COLOR)
		if image is None:
			raise ValueError(f'{path} is not an image, or does not exist')
		return image
	except ValueError:
		raise ValueError("please use: diff.py [filename] [filename]")


def compare(how, img1, img2):
	"""
	Perform SSIM and find diff contours on the result
	"""

	# full=True gives us both the similarity score and the diff map
	score, diff = structural_similarity(img1, img2, full=True)
	diff = (diff * 255).astype("uint8")

	#cv2.namedWindow(f'{how} diff', cv2.WINDOW_NORMAL)
	#cv2.imshow(f'{how} diff', diff)
	#cv2.waitKey(0)

	return diff


def extract_contours(diff, diffs=[], tinydiffs=[]):
	# find our contours
	thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
	contours = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	contours = imutils.grab_contours(contours)

	# aggregate the contours, throwing away duplicates
	for c in contours:
		(x, y, w, h) = cv2.boundingRect(c)
		region = [x, y, x + w, y + h]
		if w <= 15 or h <= 15:
			# note: anything smaller than 7x7 is just straight up not a meaningful
			# difference, and could be JPG artifacting, text subpixel anti-aliassing,
			# or any number of other "not real diff" causes. The odds that a 5x5 or
			# smaller diff is because of a genuine change in HTML or CSS is so low that
			# the cost of evaluating every one of them is just not worth calling out.
			if w < 7 and h < 7:
				continue
			try:
				tinydiffs.index(region)
			except ValueError:
				tinydiffs.append(region)
		else:
			try:
				diffs.index(region)
			except ValueError:
				diffs.append(region)

	return diffs, tinydiffs


def filter_diffs(diffs):
	"""
	This is inefficient, but cv2.RETR_EXTERNAL should have already removed
	all contours contained by other contours... but it hasn't. So we do this.
	"""
	def not_contained(e, diffs):
		for t in diffs:
			if e[0] > t[0] and e[2] < t[2] and e[1] > t[1] and e[3] < t[3]:
				return False
		return True

	return [e for e in diffs if not_contained(e, diffs)]


def collapse_diffs(a, diffs, tolerance=1):
	"""
	draw all diffs, dilated by [tolerance], then re-compute the resulting contours
	"""
	canvas = a.copy()
	(w,h,channels) = canvas.shape
	cv2.rectangle(canvas, (0,0), (w,h), WHITE, cv2.FILLED)
	for d in diffs:
		cv2.rectangle(canvas, (d[0] - tolerance, d[1] - tolerance), (d[2] + tolerance, d[3] + tolerance), BLACK, cv2.FILLED)
	diffs, tinydiffs = extract_contours(gray(canvas))
	return filter_diffs(diffs)


def mse_similarity(a, b):
	err = np.sum((a.astype("float") - b.astype("float")) ** 2)
	err /= float(a.shape[0] * a.shape[1])
	return err


def get_distance(x1,y1,x2,y2):
	dx = x2 - x1
	dy = y2 - y1
	return (dx*dx + dy*dy) ** 0.5


def find_in_original(a, b, area):
	"""
	See if we can find a diff area in the original, because it's possible
	it simply moved around wholesale, rather than being a changed region.
	"""
	w = (area[2] - area[0])
	h = (area[3] - area[1])

	if w < 5 or h < 5:
		# There aren't any features to match with on something
		# that is either too thin or too short..
		return None

	crop = b[area[1]:area[3], area[0]:area[2]]
	result = cv2.matchTemplate(crop, a, cv2.TM_CCOEFF_NORMED)

	min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
	(startX, startY) = max_loc

	(endX, endY) = (startX + w, startY + h)
	endX = startX + w
	endY = startY + h
	ocrop = a[startY:endY, startX:endX]
	region = None

	if (w + h > 10) and mse_similarity(crop, ocrop) < w * h:
		# in order to check structural_similarity, our crops need to be
		# at least 7x7, so if they're not we'll use naive MSE instead.
		region = [startX, startY, endX, endY]

	else:
		try:
			if structural_similarity(gray(ocrop), gray(crop)) >= 0.97:
				# this basically needs to be a near-perfect match
				# for us to consider it a "moved" region rather than
				# a genuine difference between A and B.
				region = [startX, startY, endX, endY]
		except ValueError as err:
			print('SSIM error:', area)
			region = None

	if region is not None:
		# It's possible that we found something that wasn't moved at all,
		# such as an area of whitespace, in which there will not be a diff
		# between A and B for the found region. If so, we return None
		ocrop = a[startY:endY, startX:endX]
		crop = b[startY:endY, startX:endX]
		diff = mse_similarity(gray(ocrop), gray(crop))
		if diff == 0:
			# both old and new have the same data for the same crop
			# region: this isn't actually a diff at all.
			region = []

	return region


def highlight_diffs(a, b, diffs, write=False, result_path='results', match_origin=False):
	"""
	Show diff using red highlights for "true diffs", and blue highlights for relocated content.
	"""

	# If there are "relocations" we want to highlight those in the original image
	original_mask = a.copy()
	original_mask[:] = (255, 255, 255)

	# For non-relocation diffs we build a mask, instead.
	diff_mask = b.copy()
	diff_mask[:] = (255, 255, 255)

	for num, area in enumerate(diffs):
		print(f'processing diff {num+1} (bbox={area})')
		x1, y1, x2, y2 = area
		origin = None

		if match_origin:
			# is this a relocation, or an addition/deletion?
			origin = find_in_original(a, b, area)
			if origin is not None:
				if len(origin) == 0:
					# this region was effectively a "noop": it's an area that got flagged
					# as a difference, but the corresponding "original location" is the same
					# in both images, thus suggesting that we're actually looking at something
					# that's either whitespace, or something that acts similar to whitespace.
					pass
				else:
					# If we found this new content somewhere in the old content (with a high
					# enough confidence) then this is content that got moved rather than being
					# content that got changed.
					cv2.rectangle(original_mask, (origin[0], origin[1]), (origin[2], origin[3]), BLUE, cv2.FILLED)
					cv2.rectangle(diff_mask, (x1, y1), (x2, y2), BLUE, cv2.FILLED)
			else:
				# If we cannot find this new content in the old content, this
				# is a regular old "diff" in that this region of the image has
				# just changed (for whatever reason)
				cv2.rectangle(diff_mask, (x1, y1), (x2, y2), GREEN, cv2.FILLED)
		else:
			# Same case as when match_origin can't find matches:
			cv2.rectangle(diff_mask, (x1, y1), (x2, y2), GREEN, cv2.FILLED)

	print('diff pass complete')

	if (write):
		cv2.imwrite(f'{result_path}/original_mask.png', original_mask)
		cv2.imwrite(f'{result_path}/diff_mask.png', diff_mask)
	else:
		cv2.imshow("Stock", original_mask)
		cv2.imshow("Given", diff_mask)
		cv2.waitKey(0)


def gray(img):
	return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def hue(img):
	return cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:,:,0]


def perform_diffing(image_pair, write=False, result_path='results', match_origin=True, max_passes=5):
	(a, b) = image_pair

	print('Running grayscale comparison...')
	grayDiff = compare("gray", gray(a), gray(b))

	print('Running hue comparison...')
	hueDiff = compare("hue", hue(a), hue(b))

	diff = cv2.addWeighted(grayDiff, 0.5, hueDiff, 0.5, 0)
	#cv2.imshow("diff", diff)
	#cv2.waitKey(0)

	print('Extracting contours...')
	diffs, tinydiffs = extract_contours(diff)
	diffs.extend(tinydiffs)
	diff_count = len(diffs)
	print(f'found {diff_count} differences.')


	if diff_count > 0:
		passes = 0
		while match_origin and diff_count > 25 and passes < max_passes:
			# This is too many diffs. See if we can merge a bunch of them
			# based on proximity. This will make the diffs "bigger", but
			# given the number we're already dealing with, that's almost
			# certainly fine...
			passes += 1
			print(f'too many diffs, attempting to collapse (pass {passes})...')
			prev_count = diff_count
			diffs = collapse_diffs(a, diffs)
			diff_count = len(diffs)
			if diff_count == prev_count:
				break
		print(f'reduced to {len(diffs)} diffs')

		print('Starting diff highlight...')
		highlight_diffs(a, b, diffs, write, result_path, match_origin)
		return diffs

	else:
		print('no differences detected')


def make_same_size(a, b):
	(h1, w1, c1) = a.shape
	(h2, w2, c2) = b.shape
	if h1 != h2:
		if h1 < h2:
			b = b[0:h1, :]
		else:
			a = a[0:h2, :]
	if w1 != w2:
		if w1 < w2:
			b = b[:, 0:w1]
		else:
			a = a[:, 0:w2]
	return (a, b, )
