# Copyright (c) 2007-2020 gocept gmbh & co. kg
# See also LICENSE.txt

# Minimal shim so tools that still expect a `setup.py` (e.g. `pip install
# -e .` with very old pip, or `check-manifest`) keep working. All actual
# packaging metadata lives in `pyproject.toml`.

from setuptools import setup

setup()
