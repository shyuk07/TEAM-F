---
name: fastapi-run
description: 마감 직전 프로젝트의 PostgreSQL과 FastAPI 서버를 띄우고 API 응답(200/400/401/404), Swagger, Jinja2 화면을 실제로 확인합니다. 구현한 기능이 실제로 동작하는지 확인하거나, 시연 시나리오를 점검할 때 사용합니다.
---

# 서버 실행과 동작 확인

명령은 모두 프로젝트 루트에서 실행합니다. 포트와 로그 위치는 변수로 정합니다.
```bash
PORT=8001                          # README와 같은 기본 포트
LOG=<scratchpad>/uvicorn.log       # Claude는 scratchpad, 사람은 /tmp 등 아무 곳
```

## 1. 준비
```bash
uv sync
```
```bash
test -f .env || cp .env.example .env
```
`.env`가 이미 있으면 덮어쓰지 않습니다. 새로 복사했다면 `JWT_SECRET_KEY`를 32자 이상 임의 값으로 바꿉니다. 예시값(`change-me...`)이면 서버가 시작 시점에 거부합니다.

## 2. Docker와 PostgreSQL
```bash
docker info > /dev/null 2>&1 && echo ok
```
- **로컬(Windows·macOS):** Docker Desktop을 켜고 다시 확인합니다.
- **클라우드·컨테이너 환경:** Docker 데몬이 자동으로 뜨지 않습니다. root라면 직접 띄우고 준비될 때까지 기다립니다.
  ```bash
  dockerd > <scratchpad>/dockerd.log 2>&1 &
  for i in $(seq 30); do docker info > /dev/null 2>&1 && break; sleep 1; done
  ```

```bash
docker compose up -d postgres
```
`compose.yaml` 기준으로 호스트 포트는 **5433**입니다. Docker를 쓸 수 없는 환경이면 로컬 PostgreSQL을 쓰고 `.env`의 `DATABASE_URL`을 맞춥니다. DB 없이 확인할 수 있는 것은 import 검사뿐이라는 점을 보고서에 적습니다.

위 과정은 `scripts/run_server.sh db`가 한 번에 합니다 (데몬 확인 → 필요하면 `dockerd` 기동 → 컨테이너 실행 → `pg_isready` 대기).

## 3. 서버 실행
`scripts/run_server.sh`로 띄우고 끕니다. 백그라운드 실행, PID 파일 기록, 응답할 때까지 대기(기본 30초)를 합니다.
```bash
PORT=8001 LOG=<scratchpad>/uvicorn.log PIDFILE=<scratchpad>/uvicorn.pid \
  bash .claude/skills/fastapi-run/scripts/run_server.sh start
```
같은 변수로 `status`, `stop`을 씁니다. 기동에 실패하면 스크립트가 로그 마지막 30줄을 보여 주고 종료코드 1을 냅니다.

직접 실행할 때는 PID 파일을 남기고, 기동 대기 루프로 확인합니다.
```bash
uv run uvicorn main:app --app-dir src --port $PORT > $LOG 2>&1 &
echo $! > <scratchpad>/uvicorn.pid
for i in $(seq 30); do curl -sf http://localhost:$PORT/ > /dev/null && break; sleep 1; done
curl -s http://localhost:$PORT/ && curl -s http://localhost:$PORT/health/db
```
실패하면 `$LOG`의 마지막 부분을 확인합니다. `ModuleNotFoundError`는 `__init__.py` 누락이나 `--app-dir src` 누락이, `RuntimeError: JWT_SECRET_KEY...`는 `.env` 설정이 흔한 원인입니다.

## 4. 확인 시나리오 (교안 시연 순서)
각 요청의 상태 코드와 응답 본문을 기록합니다. 에러 응답은 공통 형식 `{"success": false, "error_code": "...", "message": "..."}`입니다(`docs/reference/README.md`).

1. **문서:** `GET /docs` 200, `GET /openapi.json`에 등록한 경로가 모두 있는지
2. **정상 처리:** 대상 기능의 정상 요청 → 200/201
3. **도메인 규칙 차단:** 재고 초과, 잘못된 상태 전이, 형식 오류 등 → 400과 `error_code`(`VALIDATION_ERROR` 등), `message`
4. **없는 리소스:** 없는 ID → 404 `NOT_FOUND`
5. **인증:**
   - 회원가입 → `POST /v1/auth/login`(JSON: `{"email", "password"}`)으로 토큰 발급 (form으로 보내면 400)
   - `Authorization: Bearer <토큰>`으로 보호된 API 호출 → 200
   - 토큰 없이 호출 → **401** `UNAUTHORIZED`와 `WWW-Authenticate: Bearer` 헤더
   - 로그아웃(204) → 같은 토큰으로 다시 호출 → **401** `TOKEN_REVOKED`와 `WWW-Authenticate: Bearer`
6. **웹 화면:** Jinja2 페이지 → 200, HTML에 DB 데이터가 들어 있는지
7. **미들웨어:** 응답 헤더나 서버 로그에 처리 시간 로그, CORS 헤더(`Origin` 헤더를 넣어 요청)

아직 만들지 않은 기능(라우터 없음, 페이지 없음, 미들웨어 없음)은 실패가 아니라 **미구현**으로 표기합니다. `/openapi.json`의 경로 목록으로 구분합니다.

auth와 공통 동작(시나리오 1, 3~5)은 smoke 스크립트로 자동 확인합니다. 매번 새 이메일로 가입하므로 반복 실행해도 되고, 기대 상태 코드·`error_code`·`WWW-Authenticate`를 비교해 PASS/FAIL을 출력합니다. 하나라도 FAIL이면 종료코드 1입니다. 다른 모듈은 구현/미구현만 `INFO`로 알려 줍니다.
```bash
BASE=http://localhost:$PORT bash .claude/skills/fastapi-run/scripts/smoke_auth.sh
```

화면 캡처가 필요하면 Playwright로 `/docs`와 Jinja2 페이지를 찍습니다(이 환경에는 Chromium이 설치돼 있습니다).

## 5. 정리
```bash
PIDFILE=<scratchpad>/uvicorn.pid bash .claude/skills/fastapi-run/scripts/run_server.sh stop
```
직접 띄웠다면 `kill $(cat <scratchpad>/uvicorn.pid)`로 끕니다. `pkill -f "uvicorn main:app"`은 그 문자열이 든 현재 셸 명령까지 죽여(exit 144) 쓰지 않습니다. DB 컨테이너는 사용자가 요청하지 않으면 그대로 둡니다.

## 보고 형식
| 시나리오 | 요청 | 기대 | 실제 | 결과 |

결과는 **통과 / 실패 / 미구현** 중 하나로 적습니다. 실패한 항목은 로그 일부와 원인 추정을 함께 적습니다.
