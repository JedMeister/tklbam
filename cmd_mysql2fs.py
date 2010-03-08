#!/usr/bin/python
"""
Map a MySQL dump to a filesystem path.

Options:
    -D --delete             Delete contents of output dir
    --fromfile=PATH         Read mysqldump output from file (- for STDIN)
                            Requires: --all-databases --skip-extended-insert

    -v --verbose            Turn on verbosity

Supports the following subset of mysqldump(1) options:

    -u --user=USER 
    -p --password=PASS

       --defaults-file=PATH
       --host=HOST

"""
import os
from os.path import *

import sys
import getopt

import shutil

import mysql

def fatal(e):
    print >> sys.stderr, "fatal: " + str(e)
    sys.exit(1)

def usage(e=None):
    if e:
        print >> sys.stderr, e

    print >> sys.stderr, "Syntax: %s [-options] path/to/output [ -?database/table ... ] " % sys.argv[0]
    print >> sys.stderr, __doc__.strip()
    sys.exit(1)

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'Du:p:v', 
                                       ['verbose', 'delete', 'fromfile=',
                                        'user=', 'password=', 'defaults-file=', 'host='])
    except getopt.GetoptError, e:
        usage(e)

    opt_verbose = False
    opt_fromfile = None
    opt_delete = False
    myconf = {}
    for opt, val in opts:
        if opt in ('-v', '--verbose'):
            opt_verbose = True
        elif opt == '--fromfile':
            opt_fromfile = val
        elif opt in ('-D', "--delete"):
            opt_delete = True
        elif opt in ('-u', '--user'):
            myconf['user'] = val
        elif opt in ('-p', '--password'):
            myconf['password'] = val
        elif opt == "--defaults-file":
            myconf['defaults_file'] = val
        elif opt == "--host":
            myconf['host'] = val
        else:
            usage()

    if not args:
        usage()

    outdir = args[0]
    limits = args[1:]

    if opt_fromfile and myconf:
        fatal("--fromfile incompatible with mysqldump options")

    if opt_delete and isdir(outdir):
        shutil.rmtree(outdir)

    if not exists(outdir):
        os.mkdir(outdir)

    if opt_fromfile:
        if opt_fromfile == '-':
            mysqldump_fh = sys.stdin
        else:
            mysqldump_fh = file(opt_fromfile)
    else:
        mysqldump_fh = mysql.mysqldump(**myconf)

    callback = None
    if opt_verbose:
        print "source: " + mysqldump_fh.name

        def callback(val):
            if isinstance(val, mysql.MyFS.Database):
                database = val
                print "database: " + database.name
            elif isinstance(val, mysql.MyFS.Table):
                table = val
                print "table: " + join(table.database.name, table.name)

    mysql.mysql2fs(mysqldump_fh, outdir, limits, callback)

if __name__ == "__main__":
    main()

