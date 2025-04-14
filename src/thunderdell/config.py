#!/usr/bin/env python3
"""Sets user configuration values."""

import importlib.resources
import os
from pathlib import Path

HOME = Path.home()
PROJECT_ROOT = Path(
    __file__
).parent.parent.parent  # Adjusted to point to the actual project root
TESTS_FOLDER = PROJECT_ROOT / "tests"
CGI_DIR = HOME / "joseph" / "plan" / "cgi-bin"  # for local server
CLIENT_HOME = Path("/Users/reagle")  # for opening local results pages
DEFAULT_MAP = HOME / "joseph" / "readings.mm"
DEFAULT_PRETTY_MAP = HOME / "joseph" / "2005" / "ethno" / "field-notes.mm"
TMP_DIR = HOME / "tmp" / ".td"
TMP_DIR.mkdir(parents=True, exist_ok=True)
EDITOR = Path(os.environ.get("EDITOR", "nano"))
VISUAL = Path(os.environ.get("VISUAL", "nano"))

# Get wordlist paths using importlib.resources - correct way for type checking
try:
    # Get the resource as a file path string and convert to Path
    resource_path = importlib.resources.files("thunderdell.biblio")
    WORD_LIST_FN = Path(str(resource_path / "wordlist-american.txt"))
    PROPER_NOUNS_FN = Path(str(resource_path / "wordlist-proper-nouns.txt"))
except (ImportError, ModuleNotFoundError, TypeError):
    # Fallback for when resources can't be found
    module_dir = Path(__file__).parent
    WORD_LIST_FN = module_dir / "biblio" / "wordlist-american.txt"
    PROPER_NOUNS_FN = module_dir / "biblio" / "wordlist-proper-nouns.txt"
