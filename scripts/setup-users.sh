#!/bin/sh
set -eu

echo "Shared user setup is retired. Starting interactive administrator onboarding."
exec "${PYTHON:-python}" manage.py create-admin
