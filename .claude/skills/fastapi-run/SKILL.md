---
name: fastapi-run
description: 마감 직전 프로젝트의 PostgreSQL과 FastAPI 서버를 띄우고 API 응답(200/400/401/404), Swagger, Jinja2 화면을 실제로 확인합니다. 구현한 기능이 실제로 동작하는지 확인하거나, 시연 시나리오를 점검할 때 사용합니다.
---

# 서버 실행과 동작 확인

## 1. 준비 (프로젝트 루트)
```bash
uv sync
```
```bash
test -f .env || cp .env.example .env
```
`.env`가 이미 있으면 덮어쓰지 않습니다.

## 2. PostgreSQL 실행
```bash
docker compose up -d postgres
```
`compose.yaml` 기준으로 호스트 포트는 **5433**입니다. Docker를 쓸 수 없는 환경이면 로컬 PostgreSQL을 쓰고 `.env`의 `DATABASE_URL`을 맞춥니다. DB 없이 확인할 수 있는 것은 import 검사뿐이라는 점을 보고서에 적습니다.

## 3. 서버 실행
백그라운드로 실행하고, 로그를 파일로 남깁니다.
```bash
uv run uvicorn main:app --app-dir src --port 8000 > /tmp/uvicorn.log 2>&1 &
```
기동 확인:
```bash
curl -s http://localhost:8000/ && curl -s http://localhost:8000/health/db
```
실패하면 `/tmp/uvicorn.log`의 마지막 부분을 확인합니다. `ModuleNotFoundError`는 `__init__.py` 누락이나 `--app-dir src` 누락이 흔한 원인입니다.

## 4. 확인 시나리오 (교안 시연 순서)
각 요청의 상태 코드와 응답 본문을 기록합니다.

1. **문서:** `GET /docs` 200, `GET /openapi.json`에 등록한 경로가 모두 있는지
2. **정상 처리:** 대상 기능의 정상 요청 → 200/201
3. **도메인 규칙 차단:** 재고 초과, 잘못된 상태 전이 등 → 400과 `detail` 메시지
4. **없는 리소스:** 없는 ID → 404
5. **인증:**
   - 회원가입 → `POST` 로그인(form: `username`, `password`)으로 토큰 발급
   - `Authorization: Bearer <토큰>`으로 보호된 API 호출 → 200
   - 로그아웃 → 같은 토큰으로 다시 호출 → **401**
6. **웹 화면:** Jinja2 페이지 → 200, HTML에 DB 데이터가 들어 있는지
7. **미들웨어:** 응답 헤더나 서버 로그에 처리 시간 로그, CORS 헤더(`Origin` 헤더를 넣어 요청)

화면 캡처가 필요하면 Playwright로 `/docs`와 Jinja2 페이지를 찍습니다(이 환경에는 Chromium이 설치돼 있습니다).

## 5. 정리
```bash
pkill -f "uvicorn main:app" || true
```
DB 컨테이너는 사용자가 요청하지 않으면 그대로 둡니다.

## 보고 형식
| 시나리오 | 요청 | 기대 | 실제 | 결과 |
실패한 항목은 로그 일부와 원인 추정을 함께 적습니다.
