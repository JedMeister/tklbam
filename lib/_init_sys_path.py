"""Pin sys.path to tklbam's own bundled pypy and its deps.

IMPORT THIS ONLY FROM AN EXECUTABLE - i.e. the cmd_*.py entrypoints.

It *assigns* sys.path rather than appending to it. That is deliberate: it
isolates tklbam from system python packages. But it also means that importing
this module as a side effect of a library import silently repoints every
subsequent import at the installed /usr/lib/tklbam, discarding whatever path
the caller had set up - so code running from a checkout would quietly start
loading the installed copy instead, and edits would appear to have no effect.

That is not hypothetical: py2_duplicity used to reach this module transitively
(hub -> conf -> py2_duplicity -> cmd_internal -> here) through an import of
fmt_internal_command that had outlived its only caller.

If a library module ever needs a helper that currently lives in a cmd_*.py,
move the helper into a side-effect-free module rather than importing the
entrypoint.
"""
import sys
sys.path = [
    '',
    '/usr/lib/tklbam',
    '/usr/lib/tklbam/deps/lib',
    '/usr/lib/tklbam-pypy2/lib_pypy',
    '/usr/lib/tklbam-pypy2/lib-python/2.7',
    '/usr/lib/tklbam-pypy2/site-packages',
]
