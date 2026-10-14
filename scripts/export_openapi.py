"""Export API contracts without connecting to a database or starting a server."""

import argparse
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))

from app.core.config import Settings  # noqa: E402 -- application path configured above
from app.main import create_app  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
arguments = parser.parse_args()
schema = create_app(Settings(name="Resume Tailor", _env_file=None)).openapi()
target = root / "frontend" / "src" / "api" / "openapi.json"
target.parent.mkdir(parents=True, exist_ok=True)
serialized = json.dumps(schema, indent=2, sort_keys=True) + "\n"
if arguments.check:
    if not target.exists() or target.read_text(encoding="utf-8") != serialized:
        raise SystemExit("OpenAPI is stale. Run python scripts/tasks.py api.")
else:
    target.write_text(serialized, encoding="utf-8")
print(f"Exported {target.name}")
