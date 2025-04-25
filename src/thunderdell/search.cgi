#!/usr/bin/env python3
"""CGI wrapper for thunderdell query server."""

# set shebang locally to latest
# !/usr/bin/env python3
# set the shebang on a2hosting to
# !/home/goateene/opt/bin/python3

import sys
from pathlib import Path

# Add thunderdell to sys.path if needed
TD_DIR = Path.home() / "bin" / "td"
if TD_DIR.exists():
    sys.path.append(str(TD_DIR))

try:
    from thunderdell.query_serve import handle_cgi

    handle_cgi()
except ImportError:
    print("Content-Type: text/html\n\n")
    print("<h1>Error</h1><p>Could not import thunderdell.query_serve module</p>")
    sys.exit(1)
