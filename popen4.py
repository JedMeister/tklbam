# Copyright (c) 2007-2011 Liraz Siri <liraz@turnkeylinux.org>
#               2019-2024 TurnKey GNU/Linux <admin@turnkeylinux.org>
#
# turnkey-popen4 is open source software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of the
# License, or (at your option) any later version.

import os
import termios
import pty
import pwd
import grp
from io import TextIOWrapper
from typing import Optional

try:
    MAXFD = os.sysconf('SC_OPEN_MAX')
except (AttributeError, ValueError):
    MAXFD = 256

SHELL = os.environ.get('SHELL', '/bin/sh')


class CatchIOErrorWrapper:
    """wraps around a file handler and catches IOError exceptions"""

    fh: TextIOWrapper

    def __init__(self, fh: TextIOWrapper) -> None:
        self.fh = fh

    def __del__(self) -> None:
        try:
            self.fh.close()
        except IOError:
            pass

    def __getattr__(self, attr: str) -> str:
        return getattr(self.fh, attr)

    def fileno(self) -> int:
        return self.fh.fileno()

    def read(self, size: int = -1) -> str:
        try:
            return self.fh.read(size)
        except IOError:
            return ''

    def readline(self, size: int = -1) -> str:
        try:
            return self.fh.readline(size)
        except IOError:
            return ''

    def readlines(self, size: int = -1) -> list[str]:
        try:
            return self.fh.readlines(size)
        except IOError:
            return []

    def xreadlines(self):
        # should be reundant in py3 - included for now but should be removed
        return self.fh

    def close(self) -> None:
        self.__del__()


class Error(Exception):
    pass


class Popen4:
    """An implementation of popen2.Popen4 in which the output from stdut and
    stderr is combined.

    Features:

    - Supports pty allocation (this may work around issues with Unix buffering)
    - Supports setting process group.
    - Supports privilege dropping.

    """

    sts = -1

    def __init__(self,
                 cmd: list[str],
                 bufsize: int = 0,
                 pty: bool = False,
                 runas: Optional[str | int] = None,
                 setpgrp: bool = False
                 ) -> None:
        """
        Argument notes:

        - 'cmd' can be a string (passed to a shell) or a tuple/array.
        - 'runas' can be uid or username.
        """
        runas_user = ''
        if isinstance(runas, str):
            # assume username
            runas_user = runas
        if isinstance(runas, int):
            # assume uid
            runas_user = pwd.getpwuid(runas)[0]

        if pty is True and setpgrp is False:
            raise Error("pty=True incompatible with setpgrp=False")

        self.pid: Optional[int] = None
        self.childerr: Optional[int] = None
        if pty:
            self._init_pty(cmd, bufsize, runas_user)
        else:
            self._init_pipe(cmd, bufsize, runas_user, setpgrp)

        self.pty = pty

    def _init_pty(self, cmd: list[str], bufsize: int,
                  runas: Optional[int | str]
                  ) -> None:
        def tty_echo_off(fd):
            new = termios.tcgetattr(fd)
            new[3] = new[3] & ~termios.ECHO          # lflags
            termios.tcsetattr(fd, termios.TCSANOW, new)

        (pid, fd) = pty.fork()
        if not pid:
            # Child
            if runas is not None:
                self._drop_privileges(runas)

            self._run_child(cmd)

        tty_echo_off(fd)

        self.pid = pid
        self.fromchild = CatchIOErrorWrapper(os.fdopen(fd, "r+", bufsize))
        self.tochild = self.fromchild

    def _init_pipe(self, cmd: list[str], bufsize: int, runas: int | str,
                   setpgrp: bool = False
                   ) -> None:
        p2cread, p2cwrite = os.pipe()
        c2pread, c2pwrite = os.pipe()
        self.pid = os.fork()
        if self.pid == 0:
            # Child
            if setpgrp:
                os.setpgrp()
            if runas is not None:
                self._drop_privileges(runas)
            os.dup2(p2cread, 0)
            os.dup2(c2pwrite, 1)
            os.dup2(c2pwrite, 2)

            self._run_child(cmd)
        os.close(p2cread)
        self.tochild = CatchIOErrorWrapper(os.fdopen(p2cwrite, 'w', bufsize))
        os.close(c2pwrite)
        self.fromchild = CatchIOErrorWrapper(os.fdopen(c2pread, 'r', bufsize))

    def _run_child(self, cmd: str | list[str]) -> None:
        if isinstance(cmd, str):
            cmd = [SHELL, '-c', cmd]
        for i in range(3, MAXFD):
            try:
                os.close(i)
            except OSError:
                pass
        try:
            os.execvp(cmd[0], cmd)
        finally:
            os._exit(1)

    def __del__(self) -> None:
        if not self.pid:
            return None

        try:
            self.poll()
        except OSError:
            pass

        try:
            self.fromchild.close()
            self.tochild.close()
        except:  # TODO bare except
            pass

    def _drop_privileges(self, user):
        pwent = pwd.getpwnam(user)
        uid, gid, home = pwent[2], pwent[3], pwent[5]
        os.unsetenv("XAUTHORITY")
        os.putenv("USER", user)
        os.putenv("HOME", home)

        usergroups = []
        groups = grp.getgrall()
        for group in groups:
            if user in group[3]:
                usergroups.append(group[2])

        os.setgroups(usergroups)
        os.setgid(gid)
        os.setuid(uid)

    def poll(self) -> int:
        """Return the exit status of the child process if it has finished,
        or -1 if it hasn't finished yet."""

        assert self.pid
        if self.sts < 0:
            pid, sts = os.waitpid(self.pid, os.WNOHANG)
            if pid == self.pid:
                self.sts = sts

        return self.sts

    def wait(self) -> int:
        """Wait for and return the exit status of the child process."""
        assert self.pid
        pid, sts = os.waitpid(self.pid, 0)
        if pid == self.pid:
            self.sts = sts
        return self.sts