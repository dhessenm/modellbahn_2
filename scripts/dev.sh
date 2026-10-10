#!/usr/bin/env bash
#
# Start-/Stop-Helfer fuer die Dev-Umgebung (Backend + Frontend).
#
#   scripts/dev.sh start    Startet Backend (uvicorn:8000) und Frontend (vite:5173)
#   scripts/dev.sh stop     Stoppt beide (inkl. verwaister uvicorn-Prozesse auf 8000)
#   scripts/dev.sh status   Zeigt, was laeuft
#
# Hintergrund: uvicorn --reload kann verwaiste Worker hinterlassen, die den
# UDP-Socket zur Z21 blockieren. Dieses Skript startet das Backend bewusst
# OHNE --reload und raeumt beim Stop alle Prozesse auf Port 8000/5173 ab.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT=8000
FRONTEND_PORT=5173
LOG_DIR="$ROOT/.dev-logs"
mkdir -p "$LOG_DIR"

pids_on_port() {
  lsof -ti "tcp:$1" 2>/dev/null || true
}

kill_port() {
  local port="$1"
  local pids
  pids="$(pids_on_port "$port")"
  if [ -n "$pids" ]; then
    echo "Beende Prozess(e) auf Port $port: $pids"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 2
    pids="$(pids_on_port "$port")"
    if [ -n "$pids" ]; then
      echo "Erzwinge Beenden auf Port $port: $pids"
      # shellcheck disable=SC2086
      kill -9 $pids 2>/dev/null || true
    fi
  fi
}

start() {
  if [ ! -x "$ROOT/.venv/bin/uvicorn" ]; then
    echo "FEHLER: .venv nicht gefunden. Zuerst: python3 -m venv .venv && .venv/bin/python -m pip install -e '.[dev]'" >&2
    exit 1
  fi
  if [ ! -d "$ROOT/frontend/node_modules" ]; then
    echo "FEHLER: frontend/node_modules fehlt. Zuerst: (cd frontend && npm install)" >&2
    exit 1
  fi

  if [ -n "$(pids_on_port "$BACKEND_PORT")" ]; then
    echo "Backend-Port $BACKEND_PORT ist belegt. Erst 'stop' ausfuehren." >&2
    exit 1
  fi

  echo "Starte Backend (uvicorn, Port $BACKEND_PORT) ..."
  nohup "$ROOT/.venv/bin/uvicorn" modellbahn.main:app \
    --host 127.0.0.1 --port "$BACKEND_PORT" \
    > "$LOG_DIR/backend.log" 2>&1 &
  echo "  Backend-PID $!   Log: $LOG_DIR/backend.log"

  echo "Starte Frontend (vite, Port $FRONTEND_PORT) ..."
  ( cd "$ROOT/frontend" && nohup npm run dev > "$LOG_DIR/frontend.log" 2>&1 & )
  echo "  Frontend-Log: $LOG_DIR/frontend.log"

  echo "Fertig. UI: http://localhost:$FRONTEND_PORT/   API: http://127.0.0.1:$BACKEND_PORT/"
}

stop() {
  kill_port "$BACKEND_PORT"
  kill_port "$FRONTEND_PORT"
  echo "Gestoppt."
}

status() {
  local b f
  b="$(pids_on_port "$BACKEND_PORT")"
  f="$(pids_on_port "$FRONTEND_PORT")"
  echo "Backend (Port $BACKEND_PORT): ${b:-nicht aktiv}"
  echo "Frontend (Port $FRONTEND_PORT): ${f:-nicht aktiv}"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  *)
    echo "Verwendung: scripts/dev.sh {start|stop|restart|status}" >&2
    exit 1
    ;;
esac
