#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Sets some user configuration values."""

import os

HOME = os.path.expanduser("~")
CGI_DIR = f"{HOME}/joseph/plan/cgi-bin/"  # for local server
DEFAULT_MAP = f"{HOME}/joseph/readings.mm"
DEFAULT_PRETTY_MAP = f"{HOME}/joseph/2005/ethno/field-notes.mm"
TESTS_FOLDER = Path(f"{HOME}/bin/td/tests/")
THUNDERDELL_EXE = f"{HOME}/bin/td/thunderdell.py"


TMP_DIR = f"{HOME}/tmp/.td/"
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

EDITOR = os.environ.get("EDITOR", "nano")
VISUAL = os.environ.get("VISUAL", "nano")
