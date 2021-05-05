# ci-image-diff

A visual regression CI solution for web content, based on opencv and playwright

This project is still in progress, see https://github.com/MozillaFoundation/ci-image-diff/issues for what's left before v1.0 is ready.

## getting set up

```
$ git clone https://github.com/MozillaFoundation/ci-image-diff
$ cd ci-image-diff
$ python3 -m venv venv
```

To activate the virtual environment, on unix/linux/macos/etc.
run: `./venv/bin/activate`, on windows run: `venv\Scripts\activate`.

Then to install the dependencies:

```
(venv) > pip install -r requirements.txt
```


## getting screenshots

```
usage: test.py [-h] [-f FILE] [-w WIDTH] url

Take a screenshot of a web page.

positional arguments:
  url                   The URL for the web page.

optional arguments:
  -h, --help            show this help message and exit
  -f FILE, --file FILE  The file path to save the screenshot to, defaults to
                        "screenshot.png".
  -w WIDTH, --width WIDTH
                        The browser width in pixels, defaults to 1200.
```

this will create three screenshots, one for chrome, firefox,
and webkit each, with the indicated width (or 1200) in the
filename.


## diffing images
```
usage: diff.py [-h] [-w WRITE] original new

Diff two (bitmap) images.

positional arguments:
  original              The path for the original image.
  new                   The path for the new image.

optional arguments:
  -h, --help            show this help message and exit
  -w WRITE, --write WRITE
                        write the highlighted images to disk.
```

Note that under no circumstances do you want to use JPG images
here, because JPG block compression _will_ show up as diff, so
you end up with a page that, to humans, looks the same, and to
the computer looks literally 100% different. Not super useful.

- GREEN diff regions are "changed content", 
- RED diff regions are "new content"
- BLUE diff regions are "moved content"
