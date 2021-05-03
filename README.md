# ci-image-diff
A visual regression CI solution for web content, based on opencv and playwright

## getting set up

on unix/linux/macos/etc:

```
$ git clone https://github.com/Pomax/ci-image-diff
$ cd ci-image-diff
$ python3 -m venv venv
$ ./venv/bin/activate
(venv) $ pip install -r requirements.txt
```

on windows:

```
> git clone https://github.com/Pomax/ci-image-diff
> cd ci-image-diff
> python3 -m venv venv
> venv\Scripts\activate
(venv) > pip install -r requirements.txt
```


## getting screenshots

`>python test.py URL [--width WIDTH]`

this will create three screenshots, one for chrome, firefox,
and webkit each, with the indicated width (or 1200) in the
filename.


## diffing images

`>python diff.py original.png new.png`

Note that under no circumstances do you want to use JPG images
here, because JPG block compression _will_ show up as diff, so
you end up with a page that, to humans, looks the same, and to
the computer looks literally 100% different. Not super useful.
