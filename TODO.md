# TODO: Flask Application Deployment Issue

**Issue:** The Flask application (`query-busy`) deployed on a2hosting via cPanel's Python App feature (at `https://reagle.org/joseph/plan/qb/`) is returning a 404 Not Found error.

**Root Cause:** The server's Phusion Passenger configuration (specifically `PassengerBaseURI "/joseph/plan/qb"` in the auto-generated `.htaccess` file) strips the base path before passing the request to the Flask application. This means Flask receives `/` as the root path, while its routes and internal links are currently hardcoded to expect `/joseph/plan/qb/`.

**Implication:** This creates a mismatch between the remote deployment environment (where Flask sees `/` as its root) and local development (where Flask expects `/joseph/plan/qb/` or similar).

**Proposed Solution (Deferred):** Implement a `BASE_PATH` configuration variable within the Flask application. This variable would be set via an environment variable (`FLASK_BASE_PATH`):
- **Remote:** `FLASK_BASE_PATH="/joseph/plan/qb/"` (set in `passenger_wsgi.py`)
- **Local:** `FLASK_BASE_PATH="/qb/"` (or `"/"` if preferred, set in local shell/run script)

All Flask routes, internal links, and form actions would then use this `BASE_PATH` variable to construct correct URLs dynamically, ensuring compatibility across environments.