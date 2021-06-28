#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Sets some user configuration values."""

import os

# HOME for path of mindmaps on webhost
HOME = os.path.expanduser("~")
# CLIENT_HOME for path on the client to open mindmaps there
# as f'file://{CLIENT_HOME}/...'
CGI_DIR = f"{HOME}/joseph/plan/cgi-bin/"  # for local server
CLIENT_HOME = "/Users/reagle"
DEFAULT_MAP = f"{HOME}/joseph/readings.mm"
DEFAULT_PRETTY_MAP = f"{HOME}/joseph/2005/ethno/field-notes.mm"
TMP_DIR = f"{HOME}/tmp/.td/"
