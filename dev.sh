#!/bin/bash
# ============================================================
# dev.sh — ERM Klinik: jalankan backend + frontend sekaligus (local)
#
#   Frontend : http://localhost:5173  (browser dibuka otomatis)
#   Backend  : http://localhost:8000  (API docs: /docs)
#   Login    : admin/123456 · wigadana/123456
#   Stop     : Ctrl+C
#
# Kebutuhan: Python 3.11+, Node 18+. Tanpa PostgreSQL/Redis — pakai
# SQLite + Redis-fallback, semuanya otomatis disiapkan di run pertama.
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

echo "== ERM Klinik — dev runner =="

# ---------- 1. siapkan backend/.env (sekali saja) ----------
if [ ! -f backend/.env ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  cat > backend/.env <<EOF
DATABASE_URL=sqlite:///./erm_dev.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=${SECRET}
CORS_ORIGINS=http://localhost:5173
CLINIC_NAME="DPP dr. Ngakan Putu Wiga Kusuma Wibawa, S.Ked"
CLINIC_ADDRESS="Jalan Dewi Sartika No. 67, Kuta, Badung, Bali"
CLINIC_PHONE=021-5551234
SEED_ADMIN_PASSWORD=123456
SEED_DOKTER_PASSWORD=123456
EOF
  echo "  -> backend/.env dibuat (password login: admin/123456 · wigadana/123456)"
fi

# ---------- 2. dependency (kalau belum ada) ----------
if [ ! -d backend/.venv ]; then
  echo "  -> membuat venv backend..."
  python3 -m venv backend/.venv
fi
if ! backend/.venv/bin/python -c "import fastapi, uvicorn, sqlalchemy, redis, jwt, pydantic, reportlab" 2>/dev/null; then
  echo "  -> install dependency backend..."
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then
  echo "  -> npm install frontend..."
  (cd frontend && NODE_ENV=development npm install --no-fund --no-audit)
fi

# ---------- 3. matikan proses lama di port 8000 / 5173 ----------
for PORT in 8000 5173; do
  PIDS=$(lsof -ti tcp:$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "  -> port $PORT dipakai proses lama ($PIDS) — dimatikan"
    kill $PIDS 2>/dev/null || true
    sleep 1
  fi
done

# ---------- 4. start backend & frontend (log ke /tmp) ----------
LOG_BACKEND=/tmp/erm-backend.log
LOG_FRONTEND=/tmp/erm-frontend.log

(cd backend && exec .venv/bin/uvicorn app.main:app --port 8000) >"$LOG_BACKEND" 2>&1 &
BACKEND_PID=$!

(cd frontend && NODE_ENV=development exec npx vite --port 5173) >"$LOG_FRONTEND" 2>&1 &
FRONTEND_PID=$!

trap 'echo; echo "  -> mematikan backend & frontend..."; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0' INT TERM

# ---------- 5. tunggu sampai siap ----------
echo "  -> menunggu backend..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then echo "     OK backend  http://localhost:8000"; break; fi
  if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "     GAGAL backend — log: $LOG_BACKEND"; tail -20 "$LOG_BACKEND"; exit 1
  fi
  sleep 1
done

echo "  -> menunggu frontend..."
for _ in $(seq 1 30); do
  if curl -sf http://localhost:5173 >/dev/null 2>&1; then echo "     OK frontend http://localhost:5173"; break; fi
  if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "     GAGAL frontend — log: $LOG_FRONTEND"; tail -20 "$LOG_FRONTEND"; exit 1
  fi
  sleep 1
done

echo
echo "================================================================"
echo "  ERM Klinik jalan!"
echo "    Browser : http://localhost:5173  (dibuka otomatis)"
echo "    Login   : admin/123456 · wigadana/123456"
echo "    API docs: http://localhost:8000/docs"
echo "    Log     : $LOG_BACKEND | $LOG_FRONTEND"
echo "    Stop    : Ctrl+C"
echo "================================================================"
open http://localhost:5173 2>/dev/null || true

wait
