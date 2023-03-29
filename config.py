#!/usr/bin/env python3
"""Sets user configuration values.
"""

# TODO: move all paths to pathlib 2023-03-23

import os
from pathlib import Path

HOME = os.path.expanduser("~")
BIN_DIR = f"{HOME}/bin/td/"
CGI_DIR = f"{HOME}/joseph/plan/cgi-bin/"  # for local server
CLIENT_HOME = "/Users/reagle"  # for opening local results pages
DEFAULT_MAP = f"{HOME}/joseph/readings.mm"
DEFAULT_PRETTY_MAP = f"{HOME}/joseph/2005/ethno/field-notes.mm"
TESTS_FOLDER = Path(f"{HOME}/bin/td/tests/")
THUNDERDELL_EXE = f"{BIN_DIR}/thunderdell.py"


TMP_DIR = f"{HOME}/tmp/.td/"
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

EDITOR = os.environ.get("EDITOR", "nano")
VISUAL = os.environ.get("VISUAL", "nano")
