"""Aurora Core configuration."""

import os

API_KEY = os.environ.get("AURORA_API_KEY", "")
DB_PASSWORD = os.environ.get("AURORA_DB_PASSWORD", "")
JWT_SECRET = os.environ.get("AURORA_JWT_SECRET", "")

DB_URL = f"postgresql://aurora:{DB_PASSWORD}@db.internal.aurora-bank.example:5432/core"

ARCHIVE_DIR = "archives"
