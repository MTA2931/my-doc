"""MyDoc — development entry point.

Run with:  python run.py
Or use the Flask CLI:  flask --app run.py run --debug
"""

import os

from app import create_app
from app.config import get_config

app = create_app(get_config())

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(
        host=os.environ.get("FLASK_HOST", "127.0.0.1"),
        port=int(os.environ.get("FLASK_PORT", 5000)),
        debug=debug,
    )
