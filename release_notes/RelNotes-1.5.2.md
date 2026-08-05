## v1.5.2 Release notes

Code cleanup and bugfixes.

* Bugfixes:
    - Fix incorrect fetch of AWS_REGION env var.
    - Fix failing 'tklbam-backup --dump=dir/path'.
    - Fix incorrect mysqldump file handle name. 'fh' => 'mysqldump_fh'.
    - Ensure log() func is passed between functions/classes as intended.
    - Fix misplaced ')' which caused DB backup to inadvertently be skipped
      if/when backup run with '-q/--quiet' switch.
    - Always explicitly close open mysql db files. On a big enough DB the
      backup would fail because of exhausted file descriptors.
    - Fix edge case in conf.py where regex may match partial string rather than
      explicit string.
    - Check that backup.conf exists before reading. Ensures 'None' is returned
      if it doesn't, rather than raising an IOError.

* Code cleanup/improvement:
    - Explicitly import 'os' in cmd_escrow.py. Original code relied on '*'
      import of other tklbam module.
    - Use subprocess for apt/dpkg; using a cmd list ensures package lists are
      properly included in the command. (Improves robustness of code).
    - Lint maria-db-changes-hook & disable by default.
    - Hardcode duplicity path.
