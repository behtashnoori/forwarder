# RB-01 — Bounded Release-Build Execution

## Regression memory

An unbounded external release-build command can stall qualification without
attributable process evidence or a safe recovery path.

`scripts/build_release_package.py` therefore runs every external command in an
isolated process group with explicit timeouts.  It captures the root PID,
executable, command, working directory, timestamps, exit result, and bounded
stdout/stderr tails.  On timeout it terminates only the tree rooted at that
owned PID; it never terminates by image name.

`npm ci` is limited to 600 seconds and `npm run build` to 300 seconds. Other
external release commands have a 900-second default. A timeout raises a
diagnostic `BuildError`, preventing candidate freezing.

## Gate

M6/M7 release qualification requires the bounded command tests in
`scripts/tests/test_release_package_builder.py` and
`backend/tests/test_release_publication_contract.py`.
