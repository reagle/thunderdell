This is a suite of python scripts for bibliographic management using [Freeplane mindmapper](https://www.freeplane.org/wiki/index.php/Main_Page). 
`busy.py` is a command-line Web scraper that extracts (bibliographic) information from Web pages and store it in varied formats, such as a mindmap, blog, log file, and twitter.
It has general heuristics, modular site-specific heuristics, and can use DOI and ISBN Web services. 
`map2bib.py` is used to create bibtex/biblatex bibliographies from such mindmaps.

See the online [documentation](http://reagle.org/joseph/2009/01/thunderdell.html) for more.

## Installation

Install using [uv](https://github.com/astral-sh/uv):

```bash
uv venv # Create a virtual environment
uv pip install -e . # Install in editable mode
```

This will install the package in development mode, allowing you to modify the code and see changes immediately.

