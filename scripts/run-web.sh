#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."

if [[ -x .venv-web/bin/python ]]; then
    python=.venv-web/bin/python
elif [[ -x .venv/bin/python ]]; then
    python=.venv/bin/python
else
    echo "Prepare o ambiente: UV_PROJECT_ENVIRONMENT=.venv-web uv sync --locked --extra web" >&2
    exit 1
fi

exec "$python" - <<'PY'
import os

from dotenv import dotenv_values
import uvicorn

key = os.environ.get("NVIDIA_API_KEY", "").strip()
if not key:
    key = (dotenv_values(".env", interpolate=False).get("NVIDIA_API_KEY") or "").strip()
if not key:
    raise SystemExit("Configure NVIDIA_API_KEY no ambiente ou no arquivo .env.")
os.environ["NVIDIA_API_KEY"] = key

uvicorn.run(
    "academic_assistant.web:app",
    host="127.0.0.1",
    port=int(os.environ.get("PORT", "8000")),
    access_log=False,
)
PY
