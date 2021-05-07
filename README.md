# ci-image-diff

A visual regression CI solution for web content, based on [opencv](https://opencv.org/) and [playwright](https://playwright.dev/)

This project is still in progress, see https://github.com/MozillaFoundation/ci-image-diff/projects/1 for what's left before v1.0 is ready.

## getting set up

The following assumes that `python` is Python 3.6 or later (which is the [oldest supported version of Python](https://endoflife.date/python) at the time of writing this README). If you still have a dual Python 2.x/3.x setup, you will want to use `python3` as executable command instead.

```
$ git clone https://github.com/MozillaFoundation/ci-image-diff
$ cd ci-image-diff
$ python -m venv venv
```

To activate the virtual environment, on unix/linux/macos/etc.
run: `./venv/bin/activate`, on windows run: `venv\Scripts\activate`.

Then to install the dependencies:

```
(venv) pip install -r requirements.txt
```


## Running a test

1. Create a file called `urls.txt` and put some URLs in it, one URL per line.
2. To establish your baseline images: `(venv) python compare.py -l urls.txt --update`
3. To run subsequent comparisons: `(venv) python compare.py -l urls.txt`


## Comparing web pages

Use `compare.py`. Its help documentation is listed here for convenience, but documentation may go out of date: run `python compare.py -h` for its most up to date documentation.

```
usage: compare.py [-h] [-c COMPARE] [-co] [-g GROUND_TRUTH] [-l LIST] [-u]
               [-w WIDTH]
               [url]

Take a screenshot of a web page.

positional arguments:
  url                   The URL for the web page.

optional arguments:
  -h, --help            show this help message and exit
  -c COMPARE, --compare COMPARE
                        Save screenshots to the indicated dir. Defaults to
                        compare.
  -co, --compare-only   Do not (re)fetch screenshots.
  -g GROUND_TRUTH, --ground-truth GROUND_TRUTH
                        Set the ground truth dir. Defaults to main.
  -l LIST, --list LIST  Read list of URLs to test from a plain text, newline
                        delimited file.
  -u, --update          Update the ground truth screenshots.
  -w WIDTH, --width WIDTH
                        The browser width in pixels. Defaults to 1200.
```


## diffing images

Use `diff.py`. Its help documentation is listed here for convenience, but documentation may go out of date: run `python diff.py -h` for its most up to date documentation.

```
usage: diff.py [-h] [-o] [-p MAX_PASSES] [-r RESULT_PATH] [-w] original new

Diff two (bitmap) images.

positional arguments:
  original              The path for the original image.
  new                   The path for the new image.

optional arguments:
  -h, --help            show this help message and exit
  -o, --match-origin    try to detect relocated content.
  -p MAX_PASSES, --max-passes MAX_PASSES
                        the maximum number of diff-merge passes.
  -r RESULT_PATH, --result-path RESULT_PATH
                        the maximum number of diff-merge passes.
  -w, --write           write the highlighted images to disk.
```

Note that under no circumstances do you want to use JPG images here, because JPG block compression _will_ show up as diff, so you end up with a page that, to humans, looks the same, and to the computer looks literally 100% different. Not super useful.


## Working on the code

See https://github.com/MozillaFoundation/ci-image-diff/projects/1 for the MVP-triaged kanban and https://github.com/MozillaFoundation/ci-image-diff/issues for the full issue list
