#!/usr/bin/env python

'''
program: sortbibtex.py
created: Wed Feb  1 12:03:40 CET 2017
author: tc
'''

import argparse
import os
import shutil
import sys
import time
import subprocess


def ask_confirmation(prompt='Confirm', default_response=False):
    '''
    Prompts for yes/no response from the user, and returns True/False.
    Based on:
    http://code.activestate.com/recipes/541096-prompt-the-user-for-confirmation
    Input:
      + prompt        : the message to show (string)
      + default_resp  : default answer, if user types 'enter' (boolean)
    '''

    default_yesno = 'yes' if default_response else 'no'
    prompt = '%s yes/no (default: %s): ' % (prompt, default_yesno)
    while True:
        ans = raw_input(prompt)
        if not ans:
            return default_response
        if ans in ['y', 'Y', 'yes', 'Yes']:
            return True
        elif ans in['n', 'N', 'no', 'No']:
            return False
        else:
            print 'Not a valid answer, please enter y or n.'
            continue


def temporary_backup(filename):
    '''
    Stores a time-stamped copy of filename in a temporary folder.
    '''
    tmpdir = '/tmp/tmp_backups_bibtex/'
    try:
        assert os.path.isdir(tmpdir)
    except AssertionError:
        os.makedirs(tmpdir)
    tmpcopy = tmpdir + time.strftime("%Y%m%d-%H_%M_%S") + '_' + filename
    shutil.copy(filename, tmpcopy)
    print 'Copied %s to %s.' % (filename, tmpcopy)
    return tmpcopy


def recognize_line(_line, _iline):
    ''' Classifies a line as start/mid/end line of a bibtex item. '''
    condition_start_1 = _line[0] == '@' and _line[-1] == ','
    condition_start_2 = '{' in _line and '}' not in _line
    if condition_start_1 and condition_start_2:
        return 'start_line'
    elif _line.replace(' ', '') == '}':
        return 'end_line'
    elif '=' in _line:
        return 'mid_line'
    elif _line[0] == '#':
        return 'comment'
    else:
        errmsg = 'ERROR: could not recognize line %i: "%s"\n' % (_iline, _line)
        errmsg += '(possible explanation: comments should start with #)'
        sys.exit(errmsg)


def call_bash_command(cmdlist, Verbose=False):
    '''
    Calls a bash command, catching its returncode, stdout, and stderr.
    '''
    p = subprocess.Popen(cmdlist, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if Verbose:
        print '_' * 80 + '\n[call_bash_command] start'
        print 'returncode:\n', p.returncode
        print 'stdout:\n', stdout
        print 'stderr:\n', stderr
        print '[call_bash_command] end\n' + '*' * 80
    return p.returncode, stdout, stderr


def write_git_revision_hash(output):
    '''
    Looks for the current git hash, and writes it (if found) in a
    comment on output.
    '''
    commands = ['git', 'rev-parse', 'HEAD']
    returncode, stdout, stderr = call_bash_command(commands, Verbose=False)
    if returncode == 0:
        git_hash = stdout.replace('\n', '')
        output.write('# Current git hash %s\n' % git_hash)
    else:
        print 'WARNING: could not find a git hash.'


def store_bibtex(_db, _file_output, _backup, list_of_keys=False):
    '''
    Saves the bibtex entries of _db (+ some general info) on _file_output.
    Optional (if list_of_keys=True): It stores a list of the item
    keys, on a different file.
    '''
    out = open(_file_output, 'w')
    if list_of_keys:
        out_keys = open('list_of_keys.tex', 'w')
        out_keys.write('\\cite{')
    out.write('# Automatically generated (%s)' %
              time.strftime("%Y-%m-%d - %H:%M:%S"))
    out.write(' using sortbibtex.py.\n')
    write_git_revision_hash(out)
    out.write('# Temporary backup of the original file: %s.\n' % _backup)
    out.write('# Number of items:\n')
    for itemtype in sorted(db.keys()):
        out.write('#   %i %s\n' % (len(db[itemtype]), itemtype))
    out.write('\n')
    for itemtype in sorted(_db.keys()):
        out.write('#' * 80 + '\n')
        out.write('# %s section:\n\n' % itemtype)
        sorted_IDs = sorted(_db[itemtype].keys())
        for ID in sorted_IDs:
            out.write('@%s{%s,\n' % (itemtype, ID))
            assert ID in _db[itemtype].keys()
            for line in _db[itemtype][ID]:
                out.write(line + '\n')
            out.write('}\n')
            out.write('\n')
            if list_of_keys:
                out_keys.write(ID + ', ')
    if list_of_keys:
        out_keys.write('\n')
        out_keys.close()
    out.close()


# Parse arguments
parser = argparse.ArgumentParser(description='Clean and sort a bibtex file.')
parser.add_argument('refs', type=str, help='bibtex file to be cleaned/sorted')
parser.add_argument('--subset', dest='subset', type=str,
                    help='only use items listed in the file SUBSET' +
                         ' (default: use all)')
parser.add_argument('-d', dest='dry_run', action='store_true',
                    help='dry run (only parse, do not write any file)')
args = parser.parse_args()
file_input = args.refs
file_subset = args.subset
dry_run = args.dry_run

# Check input file, and create backup
assert os.path.isfile(file_input)
assert file_input.endswith('.bib')
backup_file = temporary_backup(file_input)

# Read file
with open(file_input) as f:
    lines = f.read().splitlines()

# Load key subset
if file_subset is not None:
    assert os.path.isfile(file_subset)
    keys_subset = []
    with open(file_subset, 'r') as read_keys_subset:
        for line in read_keys_subset:
            keys_subset += line.rstrip().split(' ')
    print 'Loaded a subset of %i keys from %s' % (len(keys_subset),
                                                  file_subset)

# Set output file
if file_subset is None:
    file_output = file_input
else:
    file_output = file_subset.replace('.', '_') + '.bib'

# Initialize db
db = {}
allowed_items = {'article', 'book', 'phdthesis', 'incollection', 'unpublished',
                 'misc', 'inproceedings', 'inbook', 'mastersthesis'}
comment_lines = []

# Parse the input file
InsideItemLock = False
print 'Parsing %s - start' % file_input
for iline, line in enumerate(lines):

    # Preliminary checks (filter empty lines, enforce no-tabs rule)
    if len(line.replace(' ', '').replace('\t', '')) == 0:
        continue
    if '\t' in line:
        sys.exit('ERROR: tab in line %i, please fix it.' % iline)

    line_type = recognize_line(line, iline)
    # Treat starting line of a bibtex item
    if line_type == 'start_line':
        # Set InsideItem lock
        if InsideItemLock:
            sys.exit('ERROR (line %i): start_line in previous item.' %
                     line_type)
        InsideItemLock = True
        # Get itemtype and ID
        type_and_ID = line.replace(' ', '').replace('@', '').replace(',', '')
        itemtype, ID = type_and_ID.split('{')
        if itemtype != itemtype.lower():
            sys.exit('FIXME: non lower-case itemtype, line %i.' % (iline + 1))
        if itemtype not in allowed_items:
            sys.exit('ERROR (%i): unknown itemtype %s.' % (iline + 1,
                     itemtype))
        # Update database
        if itemtype not in db.keys():
            db[itemtype] = {}
        if ID in db[itemtype].keys():
            sys.exit('FIXME: duplicate item at line %i.' % (iline + 1))
        db[itemtype][ID] = []

    # Treat middle line of a bibtex item
    elif line_type == 'mid_line':
        # Check for number of { and }
        if line.count('{') != line.count('}'):
            sys.exit('ERROR: Strange number of { and } in'
                     ' in line %i:\n>> %s' % (iline + 1, line))
        # Check for {{ or "{ in title lines
        titleline = line.replace(' ', '').lower().startswith('title')
        if titleline and not ('{{' in line or '\"{' in line):
            sys.exit('ERROR: No {{ or "{' +
                     ' in title line %i:\n>> %s' % (iline + 1, line))
        # Check that month field is not used (mmonth is OK)
        if 'month' in line and 'mmonth' not in line:
            sys.exit('ERROR: month in line %i:\n>> %s.' % (iline + 1, line) +
                     'Please remove it.')
        # Add commas at the end of the line
        if not line.replace(' ', '').endswith(','):
            line += ','
        # Check arxiv style
        linelow = line.replace(' ', '').lower()
        if linelow.startswith('journal') and 'arxiv' in linelow:
            sys.exit('ERROR: arxiv ID should be in note, not journal,' +
                     'at line %i:\n>> %s' % (iline + 1, line))
        # Update database
        db[itemtype][ID].append(line)
    # Treat last line of a bibtex item
    elif line_type == 'end_line':
        # Release InsideItem lock
        InsideItemLock = False
    # Treat comment line
    elif line_type == 'comment':
        comment_lines.append(line)
    # Treat unrecognized line
    else:
        sys.exit('ERROR: something wrong with line %i.' % iline)
num_items = sum(len(sub_db.keys()) for sub_db in db.values())
print 'Parsing %s - end (total number of keys: %i)' % (file_input, num_items)

if file_subset is not None:
    # Select keys from keys_subset
    keys_included = []
    for itemtype in db.keys():
        for k in db[itemtype].keys():
            if k not in keys_subset:
                del db[itemtype][k]
            else:
                keys_included.append(k)
    # Check that all keys from keys_subset are included
    for k in keys_subset:
        if k not in keys_included:
            err = 'ERROR:'
            err += ' Item \'%s\' is requested in %s' % (k, file_subset)
            err += ' but missing in %s. Exit.' % file_input
            sys.exit(err)
    print 'All %i keys from %s have been found.' % (len(keys_subset),
                                                    file_subset)
print 'Output file: %s' % file_output
print 'Proposed changes affect the number of items as follows:'
for itemtype in sorted(db.keys()):
    print '  %s' % itemtype
    cmd = 'var=`grep -i "%s{" %s ' % (itemtype, file_input)
    cmd += ' | grep -v in%s | wc -l`;' % itemtype
    cmd += 'echo "    "%s: $var' % file_input
    os.system(cmd)
    print '    %s: %i' % (file_output, len(db[itemtype]))

if dry_run:
    sys.exit('This is a dry run. Exit')

if not os.path.isfile(file_output):
    writefile = True
else:
    message = '\nWARNING: %s exists, shall I overwrite it?' % file_output
    writefile = ask_confirmation(message, default_response=False)
if writefile:
    print 'Writing on %s (temporary backup: %s).' % (file_output, backup_file)
    store_bibtex(db, file_output, backup_file)
else:
    print 'Not doing anything. Bye.'
