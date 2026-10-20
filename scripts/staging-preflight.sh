#!/usr/bin/env bash
# ES: Ejecuta el flujo operativo «staging preflight» con fallos controlados y sin ocultar errores.
# EN: Runs the «staging preflight» operational flow with controlled failures and visible errors.
set -euo pipefail

ENV_FILE="${1:-.env.staging}"
BASE_URL="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

fail() { echo "ERROR: $*" >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || fail "No existe $ENV_FILE."
command -v python >/dev/null 2>&1 || fail "Python no esta disponible."
command -v docker >/dev/null 2>&1 || fail "Docker no esta disponible."
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 no esta disponible."

python "$SCRIPT_DIR/check_staging_env.py" --env-file "$ENV_FILE"
python "$SCRIPT_DIR/check_frontend_dependencies.py"
docker compose --env-file "$ENV_FILE" -f docker-compose.prod.yml -f docker-compose.staging.yml config --quiet

if [[ -n "$BASE_URL" ]]; then
  python - "$BASE_URL" <<'PYURL'
from urllib.parse import urlparse
import sys
url = urlparse(sys.argv[1])
if url.scheme != "https" or not url.hostname:
    raise SystemExit("BaseUrl debe ser HTTPS y contener hostname.")
PYURL
fi

echo "Preflight de staging aprobado para $ENV_FILE."
