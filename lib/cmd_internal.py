#!/usr/lib/tklbam-pypy2/bin/pypy
#
# Copyright (c) 2010-2012 Liraz Siri <liraz@turnkeylinux.org>
#
# This file is part of TKLBAM (TurnKey GNU/Linux BAckup and Migration).
#
# TKLBAM is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 3 of
# the License, or (at your option) any later version.
#
"""
Execute an internal command
"""
import _init_sys_path

import os
from os.path import realpath
from cliwrapper import CliWrapper

import cmd_internals
from pylib.executil import fmt_command

class CliWrapper(CliWrapper):
    DESCRIPTION = __doc__
    PATH = cmd_internals.__path__

main = CliWrapper.main

def fmt_internal_command(command, *args):
    internal_command = [ realpath(__file__), command ] + list(args)
    return fmt_command("/usr/lib/tklbam-pypy2/bin/pypy", *internal_command)

if __name__ == "__main__":
    CliWrapper.main()


