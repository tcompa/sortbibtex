# sortbibtex
Python2 script that loads a bibtex file, validates its content (see [Bibtex style](#bibtex-style)), and saves a clean version of it.  
When used with option '--subset' (see [Usage](#usage) and [Example_subset](Example_subset)), it creates a new bibtex file only including a subset of the original items (this may be useful to create a project-specific file out of a master bibtex file).

### Usage

    usage: sort_bibtex.py [-h] [--subset SUBSET] [-d] refs_file

    Sort a bibtex file in-place.

    positional arguments:
      refs_file        file to be sorted

    optional arguments:
      -h, --help       show this help message and exit
      --subset SUBSET  only use items listed in the file SUBSET (default: use all)
      -d               dry run (only parse, do not write any file

### Bibtex style
The script requires enforcement of a set of style properties in the bibtex file:
 - 'month' field should not be included ('mmonth', which is not recognized by bibtex, is accepted).
 - Do not use URL's from doi.dx (this often requires changes from the bibtex information provided by journals).
 - Titles should be enclosed in double curly brackets.
 - Tabs should be replaced by spaces.
 - Item types (article, book, ..) should be in lower case.
 - Do not break long lines (e.g. a long authors list).
 - arXiv ID should be in the 'note' field.
 - Comments should start with '#'.

These choices are as of my taste. To modify them, look at this code block:

    print 'Parsing %s - start' % file_input
    ...
    ...
    print 'Parsing %s - end (total number of keys: %i)' % (file_input, num_items)


