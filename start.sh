#!/usr/bin/env bash
# Arranca la demo (frontend Next.js + backend FastAPI) leyendo la
# OPENAI_API_KEY desde el macOS Keychain en runtime — nunca se escribe a disco.
set -euo pipefail

KEY="$(security find-generic-password -s OPENAI_API_KEY -w 2>/dev/null || true)"
if [ -z "$KEY" ]; then
  echo "ERROR: no encontré OPENAI_API_KEY en el Keychain (servicio 'OPENAI_API_KEY')." >&2
  echo "Agrégala con la skill add-secret o exporta OPENAI_API_KEY manualmente." >&2
  exit 1
fi
export OPENAI_API_KEY="$KEY"

cd "$(dirname "$0")/ui"
echo "Frontend → http://localhost:3000   ·   Backend → http://localhost:8000"
exec npm run dev
