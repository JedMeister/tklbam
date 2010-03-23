#!/usr/bin/python
"""
Restore backup

Arguments:
    <limit> := -?( /path/to/add/or/remove | mysql:database[/table] )

Options:
    --skip-files                Don't restore filesystem
    --skip-database             Don't restore databases
    --skip-packages             Don't restore new packages

    --no-rollback               Disable rollback

"""

import os
from os.path import *

import sys
import getopt

import shutil
import tempfile
import commands

import userdb
from paths import Paths
from changes import Changes
from pathmap import PathMap
from dirindex import DirIndex
from pkgman import Installer

import backup
import mysql

def fatal(e):
    print >> sys.stderr, "error: " + str(e)
    sys.exit(1)

def usage(e=None):
    if e:
        print >> sys.stderr, "error: " + str(e)

    print >> sys.stderr, "Syntax: %s [ -options ] <address> <keyfile> [ limit ... ]" % sys.argv[0]
    print >> sys.stderr, __doc__.strip()
    sys.exit(1)

class DontWriteIfNone:
    def __init__(self, fh=None):
        self.fh = fh

    def write(self, s):
        if self.fh:
            self.fh.write(str(s))

def remove_any(path):
    """Remove a path whether it is a file or a directory. 
       Return: True if removed, False if nothing to remove"""

    if not exists(path):
        return False

    if not islink(path) and isdir(path):
        shutil.rmtree(path)
    else:
        os.remove(path)

    return True

class Error(Exception):
    pass

class Rollback:
    PATH = "/var/backups/tklbam-rollback"

    class Paths(Paths):
        files = [ 'etc', 'etc/mysql', 
                  'fsdelta', 'dirindex', 'overlay', 
                  'newpkgs', 'myfs' ]

    def __init__(self, path=PATH):
        """deletes path if it exists and creates it if it doesn't"""
        if exists(path):
            shutil.rmtree(path)
        os.makedirs(path)
        os.chmod(path, 0700)
        self.paths = paths = self.Paths(path)
        os.mkdir(paths.etc)
        os.mkdir(paths.etc.mysql)
        os.mkdir(paths.overlay)
        os.mkdir(paths.myfs)

    def move_to_overlay(self, source):
        if not exists(source):
            raise Error("no such file or directory: " + source)

        dest = join(self.paths.overlay, source.strip('/'))
        if not exists(dirname(dest)):
            os.makedirs(dirname(dest))

        remove_any(dest)
        shutil.move(source, dest)

def section_title(title):
    return title + "\n" + "=" * len(title) + "\n"

def indent_lines(s, indent):
    return "\n".join([ " " * indent + line 
                       for line in str(s).splitlines() ])

def restore_newpkgs(newpkgs_file, rollback=None, log=None):
    log = DontWriteIfNone(log)
    print >> log, "\n" + section_title("Restoring new packages")

    # apt-get update, otherwise installer may skip everything
    print >> log, "apt-get update"
    output = commands.getoutput("apt-get update")

    print >> log, "\n" + indent_lines(output, 4) + "\n"

    packages = file(newpkgs_file).read().strip().split('\n')
    installer = Installer(packages)

    if rollback:
        fh = file(rollback.paths.newpkgs, "w")
        for package in installer.installable:
            print >> fh, package
        fh.close()

    if installer.skipping:
        print >> log, "SKIPPING: " + " ".join(installer.skipping) + "\n"

    if installer.command:
        print >> log, installer.command
    else:
        print >> log, "NO NEW INSTALLABLE PACKAGES"

    try:
        exitcode, output = installer()
        print >> log, "\n" + indent_lines(output, 4)
        if exitcode != 0:
            print >> log, "# WARNING: non-zero exitcode (%d)" % exitcode

    except installer.Error:
        pass

def restore_db(extras, limits=[], rollback=None, log=None):
    log = DontWriteIfNone(log)
    print >> log, "\n" + section_title("Restoring databases")

    if rollback:
        mysql.mysql2fs(mysql.mysqldump(), rollback.paths.myfs)
        shutil.copy("/etc/mysql/debian.cnf", rollback.paths.etc.mysql)

    mysql.fs2mysql(mysql.mysql(), extras.myfs, limits, mysql.cb_print(log))

    shutil.copy(join(extras.etc.mysql, "debian.cnf"), "/etc/mysql/debian.cnf")
    os.system("killall -HUP mysqld > /dev/null 2>&1")

def restore_fs(overlay, extras, limits=[], rollback=None, log=None):
    log = DontWriteIfNone(log)
    print >> log, "\n" + section_title("Restoring filesystem")

    def userdb_merge(old_etc, new_etc):
        old_passwd = join(old_etc, "passwd")
        new_passwd = join(new_etc, "passwd")
        
        old_group = join(old_etc, "group")
        new_group = join(new_etc, "group")

        def r(path):
            return file(path).read()

        return userdb.merge(r(old_passwd), r(old_group), 
                            r(new_passwd), r(new_group))

    print >> log, "MERGING USERS AND GROUPS\n"
    passwd, group, uidmap, gidmap = userdb_merge(extras.etc, "/etc")

    for olduid in uidmap:
        print >> log, "UID %d => %d" % (olduid, uidmap[olduid])
    for oldgid in gidmap:
        print >> log, "GID %d => %d" % (oldgid, gidmap[oldgid])

    changes = Changes.fromfile(extras.fsdelta, limits)

    if rollback:
        shutil.copy("/etc/passwd", rollback.paths.etc)
        shutil.copy("/etc/group", rollback.paths.etc)

        changes.tofile(rollback.paths.fsdelta)

        di = DirIndex()
        for change in changes:
            if exists(change.path):
                di.add_path(change.path)
                if change.OP == 'o':
                    rollback.move_to_overlay(change.path)
        di.save(rollback.paths.dirindex)

    def iter_apply_overlay(overlay, root, limits=[]):
        def walk(dir):
            fnames = []
            subdirs = []

            for dentry in os.listdir(dir):
                path = join(dir, dentry)

                if not islink(path) and isdir(path):
                    subdirs.append(path)
                else:
                    fnames.append(dentry)

            yield dir, fnames

            for subdir in subdirs:
                for val in walk(subdir):
                    yield val

        class OverlayError:
            def __init__(self, path, exc):
                self.path = path
                self.exc = exc

            def __str__(self):
                return "OVERLAY ERROR @ %s: %s" % (self.path, self.exc)

        pathmap = PathMap(limits)
        overlay = overlay.rstrip('/')
        for overlay_dpath, fnames in walk(overlay):
            root_dpath = root + overlay_dpath[len(overlay) + 1:]
            if exists(root_dpath) and not isdir(root_dpath):
                os.remove(root_dpath)

            for fname in fnames:
                overlay_fpath = join(overlay_dpath, fname)
                root_fpath = join(root_dpath, fname)

                if root_fpath not in pathmap:
                    continue

                try:
                    if exists(root_fpath):
                        remove_any(root_fpath)

                    root_fpath_parent = dirname(root_fpath)
                    if not exists(root_fpath_parent):
                        os.makedirs(root_fpath_parent)

                    shutil.move(overlay_fpath, root_fpath)
                    yield root_fpath
                except Exception, e:
                    yield OverlayError(root_fpath, e)

    print >> log, "\nAPPLY OVERLAY\n"

    for val in iter_apply_overlay(overlay, "/", limits):
        print >> log, val

    print >> log, "\nAPPLYING POST-OVERLAY FIXES\n"
    for action in changes.statfixes(uidmap, gidmap):
        print >> log, action
        action()

    for action in changes.deleted():
        print >> log, action

        path, = action.args
        if rollback:
            rollback.move_to_overlay(path)
        else:
            action()

    def w(path, s):
        file(path, "w").write(str(s))

    w("/etc/passwd", passwd)
    w("/etc/group", group)

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'h', 
                                       ['skip-files', 'skip-database', 'skip-packages',
                                        'no-rollback'])
                                        
    except getopt.GetoptError, e:
        usage(e)

    skip_files = False
    skip_database = False
    skip_packages = False
    no_rollback = False
    for opt, val in opts:
        if opt == '--skip-files':
            skip_files = True
        elif opt == '--skip-database':
            skip_database = True
        elif opt == '--skip-packages':
            skip_packages = True
        elif opt == '--no-rollback':
            no_rollback = True
        elif opt == '-h':
            usage()

    if len(args) < 2:
        usage()

    address, keyfile = args[:2]
    limits = args[2:]

    if not exists(keyfile):
        fatal("keyfile %s does not exist" % `keyfile`)

    os.environ['PASSPHRASE'] = file(keyfile).read().strip()

    log = sys.stdout

    tmpdir1 = tempfile.mkdtemp(prefix="tklbam-")
    os.chmod(tmpdir1, 0700)

    try:
        command = "duplicity %s %s" % (commands.mkarg(address), tmpdir1)
        status, output = commands.getstatusoutput(command)

        del os.environ['PASSPHRASE']
        if status != 0:
            if "No backup chains found" in output:
                raise Error("Valid backup not found at " + `address`)
            else:
                raise Error("Error restoring backup (bad key?):\n" + output)

        backup_path = tmpdir1
        limits = backup.Limits(limits)

        tmpdir2 = tempfile.mkdtemp(prefix="tklbam-extras-")
        os.rename(backup_path + backup.Backup.EXTRAS_PATH, tmpdir2)

        overlay = backup_path
        extras = backup.ExtrasPaths(tmpdir2)

        if no_rollback:
            rollback = None
        else:
            rollback = Rollback()

        try:
            if not skip_packages:
                restore_newpkgs(extras.newpkgs, rollback, log)

            if not skip_files:
                restore_fs(overlay, extras, limits.fs, rollback, log)

            if not skip_database:
                restore_db(extras, limits.db, rollback, log)
        finally:
            shutil.rmtree(tmpdir2)
    finally:
        shutil.rmtree(tmpdir1)

if __name__=="__main__":
    main()
