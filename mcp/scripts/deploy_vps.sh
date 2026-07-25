#!/usr/bin/env bash
# Deploy do MCP FinanPy para a VPS via rsync + restart Hermes.
# Uso: bash mcp/scripts/deploy_vps.sh

set -euo pipefail

VPS_HOST="${VPS_HOST:-root@38.52.128.62}"
SRC="$(git rev-parse --show-toplevel)/mcp/"
DST="/opt/finanpy-mcp/"

echo "=== 1. Validação local — testes ==="
cd "$(git rev-parse --show-toplevel)/mcp"
.venv/bin/python -m pytest tests/ -q

echo "=== 2. Sincronia — rsync ==="
rsync -avz --delete \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  "$SRC" "$VPS_HOST:$DST"

echo "=== 3. Reinstala deps ==="
ssh "$VPS_HOST" "cd /opt/finanpy-mcp && .venv/bin/pip install -e . -q"

echo "=== 4. Restart Hermes ==="
ssh "$VPS_HOST" 'systemctl restart hermes-gateway'

echo "=== 5. Smoke ==="
ssh "$VPS_HOST" '/opt/finanpy-mcp/.venv/bin/python -m finanpy_mcp.smoke' \
  || { echo "FAIL: smoke falhou — verifique FINANPY_API_TOKEN no config.yaml do Hermes"; exit 1; }

echo "=== Deploy OK ==="