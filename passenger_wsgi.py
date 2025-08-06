#!/usr/bin/env python3
"""Passenger WSGI entry point for thunderdell Flask app."""

import sys
from pathlib import Path

# Add the src directory to Python path for the src layout
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))
sys.path.insert(0, str(project_root))

# Import the Flask app
from thunderdell.query_busy import app

# Passenger expects 'application'
application = app

# Optional: Enable debugging (remove in production)
application.debug = False

