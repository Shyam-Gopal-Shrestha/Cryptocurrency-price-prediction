#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
OUT_DIR="$ROOT_DIR/security/reports/$TIMESTAMP"
TARGET_URL="${TARGET_URL:-http://host.docker.internal:8000}"

mkdir -p "$OUT_DIR"

echo "[INFO] Output directory: $OUT_DIR"

if command -v pip-audit >/dev/null 2>&1; then
  echo "[INFO] Running pip-audit"
  pip-audit -r "$ROOT_DIR/requirements.txt" -f json -o "$OUT_DIR/pip-audit.json" || true
else
  echo "[WARN] pip-audit not installed; skipping dependency scan"
fi

if command -v bandit >/dev/null 2>&1; then
  echo "[INFO] Running bandit"
  bandit -r "$ROOT_DIR/api" -f json -o "$OUT_DIR/bandit.json" || true
else
  echo "[WARN] bandit not installed; skipping SAST bandit scan"
fi

if command -v semgrep >/dev/null 2>&1; then
  echo "[INFO] Running semgrep with OWASP rules"
  semgrep --config p/owasp-top-ten --json --output "$OUT_DIR/semgrep.json" "$ROOT_DIR/api" "$ROOT_DIR/tests" || true
else
  echo "[WARN] semgrep not installed; skipping semgrep scan"
fi

if command -v docker >/dev/null 2>&1; then
  echo "[INFO] Running OWASP ZAP baseline against $TARGET_URL"
  docker run --rm -t -v "$OUT_DIR:/zap/wrk/:rw" ghcr.io/zaproxy/zaproxy:stable \
    zap-baseline.py -t "$TARGET_URL" -J zap-baseline.json -r zap-baseline.html || true
else
  echo "[WARN] docker not available; skipping ZAP baseline scan"
fi

echo "[INFO] Scan run complete"
