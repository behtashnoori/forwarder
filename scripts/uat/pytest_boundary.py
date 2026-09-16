"""Pytest's explicitly loaded plugin rejects unsafe runs before plugin autoload."""
from scripts.uat.test_boundary import INSTALLED, deny

if not INSTALLED:
    deny("direct pytest has no approved bootstrap/owned manifest")
