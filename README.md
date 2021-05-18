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
usage: compare.py [-h] [-b BASE_DIR] [-c COMPARE] [-co] [-m] [-g GROUND_TRUTH]
                  [-l LIST] [-o] [-p] [-r RESULT_DIR] [-u] [-v] [-vx]
                  [-w WIDTH] [-z]
                  [url]

Take a screenshot of a web page.

positional arguments:
  url                   The URL for the web page.

optional arguments:
  -h, --help            show this help message and exit
  -b BASE_DIR, --base-dir BASE_DIR
                        Directory for diffs. Defaults to diffs.
  -c COMPARE, --compare COMPARE
                        Save screenshots to the indicated dir. Defaults to
                        compare.
  -co, --compare-only   Do not (re)fetch screenshots.
  -m, --missing-error   Treat missing ground truth screenshot as error.
  -g GROUND_TRUTH, --ground-truth GROUND_TRUTH
                        Set the ground truth dir. Defaults to main.
  -l LIST, --list LIST  Read list of URLs to test from a plain text, newline
                        delimited file.
  -o, --match-origin    Try to detect relocated content when analysing diffs.
  -p, --log-path-only   Only log which path is being compared, rather than
                        image locations.
  -r RESULT_DIR, --result-dir RESULT_DIR
                        Directory for comparison results. Defaults to results.
  -u, --update          Update the ground truth screenshots.
  -v, --verbose         Log progress to stdout.
  -vx, --verbose-exclusive
                        Log progress, but skip logging of each diff process.
  -w WIDTH, --width WIDTH
                        The browser width in pixels. Defaults to 1200.
  -z, --server-hint     Print the diff viewer instructions at the end of the
                        run.
```


## diffing images

Use `diff.py`. Its help documentation is listed here for convenience, but documentation may go out of date: run `python diff.py -h` for its most up to date documentation.

```
usage: diff.py [-h] [-o] [-p MAX_PASSES] [-r RESULT_PATH] [-s] [-t] [-w]
               original new

Diff two (bitmap) images.

positional arguments:
  original              The path for the original image.
  new                   The path for the new image.

optional arguments:
  -h, --help            show this help message and exit
  -o, --match-origin    Try to detect relocated content.
  -p MAX_PASSES, --max-passes MAX_PASSES
                        The maximum number of diff-merge passes. defaults to
                        5.
  -r RESULT_PATH, --result-path RESULT_PATH
                        The dir to write the comparison results to. defaults
                        to results.
  -s, --silent          Do not log progress to stdout.
  -t, --terse-logging   Only log diff pass/fail result.
  -w, --write           Write the highlighted images to disk.
```

Note that under no circumstances do you want to use JPG images here, because JPG block compression _will_ show up as diff, so you end up with a page that, to humans, looks the same, and to the computer looks literally 100% different. Not super useful.


## Working on the code

See https://github.com/MozillaFoundation/ci-image-diff/projects/1 for the MVP-triaged kanban and https://github.com/MozillaFoundation/ci-image-diff/issues for the full issue list


## Using ci-image-diff in Github Actions

Github actions are rather useful. We recommend creating two new `.github/workflows` task files,

1. one task for ensuring your baseline images are always up to date, tied to code getting merged into `main`, and
2. one task for performing visual diffing against `main` as part of your PR review process.

### (1) Keeping your baseline up to date

The following example assumes you use AWS S3 as the place to house your baseline images, as well as any PR-associated diff sets for inspection.

Remember that this really is an example: you're going to have to tailor it to your own use until such time as we turn this into its own github-action that can be referenced via a `uses`/`with` section.

```
name: Visual Diff Sync

on:
  push:
    branches: [ 'main' ]

jobs:
  update-baseline:
    name: CI Image Diff
    runs-on: ubuntu-latest
    steps:

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_FOR_VISUAL_CI }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_FOR_VISUAL_CI }}
        aws-region: your-aws-s3-region-indicator

    - uses: actions/checkout@v2

    - uses: actions/setup-python@v2
      with:
        python-version: 3.7 or higher

    - name: Installing git
      run: sudo apt-get install git

    - name: Fetching ci-image-diff
      run: git clone https://github.com/MozillaFoundation/ci-image-diff

    - name: Installing ci-image-diff dependencies
      run: |
        cd ci-image-diff
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        playwright install

    - name: Starting your build and server etc
      run: |
        ...
        ...
        ...

    - name: Establish or update the baseline
      run: |
        cd ci-image-diff
        source venv/bin/activate
        python compare.py --update --list ../testing/urls.txt

    - name: Upload baseline to AWS S3
      run: |
        cd ci-image-diff
        aws s3 sync ./diffs/main s3://your-bucket-name/baseline --acl public-read --delete
```

### (2) Performing visual diffing against your baseline for incoming PRs

With a baseline established, we can run visual diffing as part of the PR process:

```
name: Visual Regression Testing

on:
  pull_request:
    branches: [ 'main' ]

jobs:
  ci_image_diff:
    name: CI Image Diff
    runs-on: ubuntu-latest
    steps:

    - name: Extract branch name for upload step
      shell: bash
      run: echo "##[set-output name=branch;]$(echo ${GITHUB_REF#refs/})"
      id: extract_branch

    - name: Configure AWS Credentials
      uses: aws-actions/configure-aws-credentials@v1
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID_FOR_VISUAL_CI }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY_FOR_VISUAL_CI }}

    - uses: actions/checkout@v2

    - uses: actions/setup-python@v2
      with:
        python-version: 3.7 or higher

    - name: Installing git
      run: sudo apt-get install git

    - name: Fetching ci-image-diff
      run: git clone https://github.com/MozillaFoundation/ci-image-diff

    - name: Installing ci-image-diff dependencies
      run: |
        cd ci-image-diff
        python -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        playwright install

    - name: Starting your build and server etc
      run: |
        ...
        ...
        ...

    - name: Downloading the visual diffing baseline
      run: aws s3 sync s3://your-bucket-name/baseline ./diffs/main

    - name: Testing for visual regressions
      run: |
        cd ci-image-diff
        source venv/bin/activate
        python compare.py --match-origin --list ../testing/urls.txt --verbose-exclusive --log-path-only

    - name: Uploading diffs to AWS S3
      if: ${{ failure() }}
      run: aws s3 sync ./results/ s3://your-bucket-name/${{ steps.extract_branch.outputs.branch }} --acl public-read --delete

    - uses: actions/github-script@v3
      if: ${{ failure() }}
      with:
        github-token: ${{secrets.GITHUB_TOKEN}}
        script: |
          github.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: 'This PR introduces visual differences. Click [here](https://your-bucket-name.s3.your-aws-region.amazonaws.com/${{ steps.extract_branch.outputs.branch }}/index.html?reference=main&compare=compare) to inspect the diffs.'
          })
```

This will download the baseline we established earlier, and compare it to this PR's codebase results, then upload it to S3 so that any diffs can be inspected on the URL that the "what is the diff viewer URL" task echos.
