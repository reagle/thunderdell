import os
import sys

# Add the project's 'src' directory to the Python path
# This is necessary for a 'src' layout project
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import the Flask application instance
from thunderdell.query_busy import app as application
