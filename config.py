#!/usr/bin/env python3
"""Sets user configuration values."""

import os
from pathlib import Path

HOME = Path.home()
BIN_DIR = HOME / "bin" / "td"
CGI_DIR = HOME / "joseph" / "plan" / "cgi-bin"  # for local server
CLIENT_HOME = Path("/Users/reagle")  # for opening local results pages
DEFAULT_MAP = HOME / "joseph" / "readings.mm"
DEFAULT_PRETTY_MAP = HOME / "joseph" / "2005" / "ethno" / "field-notes.mm"
TESTS_FOLDER = HOME / "bin" / "td" / "tests"
THUNDERDELL_EXE = BIN_DIR / "thunderdell.py"

TMP_DIR = HOME / "tmp" / ".td"
TMP_DIR.mkdir(parents=True, exist_ok=True)

EDITOR = Path(os.environ.get("EDITOR", "nano"))
VISUAL = Path(os.environ.get("VISUAL", "nano"))
