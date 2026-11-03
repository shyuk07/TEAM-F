#!/usr/bin/env bash
# 마감 직전 서버 실행 래퍼
#   run_server.sh db      Docker 데몬 확인(필요하면 dockerd 기동) 후 PostgreSQL 컨테이너 실행
#   run_server.sh start   uvicorn을 백그라운드로 띄우고 응답할 때까지 대기
#   run_server.sh stop    PID 파일의 서버(와 자식 프로세스)만 종료
#   run_server.sh status  실행 여부 확인
# 환경변수: PORT(기본 8001), LOG, PIDFILE, DOCKERD_LOG, WAIT_SECONDS(기본 30)
set -u

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
PORT="${PORT:-8001}"
TMP="${TMPDIR:-/tmp}"
LOG="${LOG:-$TMP/lastcall-uvicorn-$PORT.log}"
PIDFILE="${PIDFILE:-$TMP/lastcall-uvicorn-$PORT.pid}"
DOCKERD_LOG="${DOCKERD_LOG:-$TMP/lastcall-dockerd.log}"
WAIT_SECONDS="${WAIT_SECONDS:-30}"
BASE="http://127.0.0.1:$PORT"

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

wait_until() { # 설명 명령...
  local what=$1; shift
  for _ in $(seq "$WAIT_SECONDS"); do
    if "$@" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "[실패] $what: ${WAIT_SECONDS}초 안에 준비되지 않음" >&2
  return 1
}

cmd_db() {
  if ! docker info >/dev/null 2>&1; then
    if command -v dockerd >/dev/null 2>&1 && [ "$(id -u)" = "0" ]; then
      echo "Docker 데몬이 꺼져 있어 dockerd를 띄웁니다 (로그: $DOCKERD_LOG)"
      nohup dockerd > "$DOCKERD_LOG" 2>&1 &
      wait_until "Docker 데몬" docker info || { tail -20 "$DOCKERD_LOG" >&2; exit 1; }
    else
      echo "[실패] Docker 데몬에 연결할 수 없습니다. 로컬이면 Docker Desktop을 켠 뒤 다시 실행하세요." >&2
      exit 1
    fi
  fi
  (cd "$ROOT" && docker compose up -d postgres) || exit 1
  wait_until "PostgreSQL" bash -c "cd '$ROOT' && docker compose exec -T postgres pg_isready -U lastcall -d lastcall" || exit 1
  echo "PostgreSQL 준비 완료 (localhost:5433)"
}

cmd_start() {
  if is_running; then
    echo "이미 실행 중입니다 (PID $(cat "$PIDFILE"), $BASE)"
    return 0
  fi
  if curl -s -o /dev/null "$BASE/"; then
    echo "[실패] 포트 $PORT를 다른 프로세스가 쓰고 있습니다. PORT를 바꾸세요." >&2
    exit 1
  fi
  [ -f "$ROOT/.env" ] || echo "[주의] .env가 없습니다. .env.example을 복사하고 JWT_SECRET_KEY를 바꾸세요." >&2
  cd "$ROOT" || exit 1
  nohup uv run uvicorn main:app --app-dir src --port "$PORT" > "$LOG" 2>&1 &
  echo $! > "$PIDFILE"
  if wait_until "서버 기동" curl -sf "$BASE/"; then
    echo "서버 실행 중: $BASE (PID $(cat "$PIDFILE"), 로그 $LOG)"
  else
    echo "--- 로그 마지막 30줄 ($LOG) ---" >&2
    tail -30 "$LOG" >&2
    cmd_stop >/dev/null
    exit 1
  fi
}

cmd_stop() {
  if ! [ -f "$PIDFILE" ]; then
    echo "PID 파일이 없습니다 ($PIDFILE). 실행 중인 서버가 없습니다."
    return 0
  fi
  local pid; pid="$(cat "$PIDFILE")"
  # uv run → python(uvicorn) 자식까지 종료한다. pkill -f는 이 명령을 실행한 셸까지 죽일 수 있어 쓰지 않는다.
  pkill -TERM -P "$pid" 2>/dev/null
  kill -TERM "$pid" 2>/dev/null
  for _ in $(seq 10); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$pid" 2>/dev/null; then
    pkill -KILL -P "$pid" 2>/dev/null
    kill -KILL "$pid" 2>/dev/null
  fi
  rm -f "$PIDFILE"
  echo "서버 종료 (PID $pid)"
}

cmd_status() {
  if is_running; then
    echo "실행 중: $BASE (PID $(cat "$PIDFILE"), 로그 $LOG)"
  else
    echo "실행 중이 아님"
    return 1
  fi
}

case "${1:-}" in
  db) cmd_db ;;
  start) cmd_start ;;
  stop) cmd_stop ;;
  status) cmd_status ;;
  *) echo "사용법: $0 db|start|stop|status" >&2; exit 2 ;;
esac
