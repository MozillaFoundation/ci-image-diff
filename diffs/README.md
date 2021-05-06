This directory will contain all diff images,
housed in dir structures of the form:

./diffs/PR_NUMBER/path/to/page

The only exception is the ground truth dir,
which gets built by invoking "test.py" with
the "--ground-truth DIRNAME" command, which
will generate your ground truth images.

You typically want to make this something
that runs as part of CI whenever code
gets merged into your main branch, so that
screenshots get automatically updated to
reflect committed changes.
