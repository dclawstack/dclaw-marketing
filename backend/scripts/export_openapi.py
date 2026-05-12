"""Export the FastAPI OpenAPI schema to docs/api/openapi.json.

Run from the backend/ directory:

    cd backend
    python scripts/export_openapi.py

The script avoids spinning up the app's full lifespan (no DB, no
external services) — it just imports the FastAPI instance and asks
it for its OpenAPI dict. Output: /docs/api/openapi.json at repo root.
"""

import json
import os
import sys
from pathlib import Path


def main() -> int:
    # Make sure the backend/ package is importable.
    backend_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(backend_dir))

    # Set required env vars to harmless defaults so settings instantiate.
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x")

    from app.api.main import app

    schema = app.openapi()
    repo_root = backend_dir.parent
    out_path = repo_root / "docs" / "api" / "openapi.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
