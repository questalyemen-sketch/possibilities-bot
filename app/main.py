from __future__ import annotations

import os

from dotenv import load_dotenv

from api.index import app

load_dotenv()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
