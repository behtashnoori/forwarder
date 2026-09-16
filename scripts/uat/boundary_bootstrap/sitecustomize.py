"""Installed through the controlled child PYTHONPATH before pytest plugins."""
import sys
try:
    from scripts.uat.test_boundary import install
    install()
except BaseException:
    # sitecustomize exceptions otherwise only print and Python continues!
    sys.stderr.write("TEST_BOUNDARY_REJECTED: bootstrap failed\n")
    sys.exit(78)
