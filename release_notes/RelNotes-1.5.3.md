## v1.5.3 Release notes

* Bugfixes:
    - Ensure squid is always killed.
    - Ensure temp restore data and other temp files are always cleaned up.
    - Remove profile archives, but only when relevant.
    - Fix duplicity switch use.
    - Fixes for modern boto usage.
    - Fix non-s3 backup target handling.
    - Actually fix AWS_REGION handling - noted as fixed in 1.5.2 (5d3bdef) but
      wasn't!
    - Ensure library chain no longer drags in a CLI entrypoint.
    - Remove dead code.
