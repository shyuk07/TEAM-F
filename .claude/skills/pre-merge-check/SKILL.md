---
name: pre-merge-check
description: 마감 직전 프로젝트에서 브랜치나 PR을 main에 머지하기 전에 실행하는 개발 검증 순서입니다. 계층 규칙, import, 테스트, 실제 실행, 코드 리뷰를 차례로 확인하고 머지 가능 여부를 판단합니다. "머지 전 점검", "PR 검증"을 요청받았을 때 사용합니다.
---

# 머지 전 점검

아래 순서대로 실행하고, 앞 단계가 실패하면 원인을 먼저 보고합니다. 검사를 통과시키려고 규칙이나 테스트를 끄지 않습니다.

## 1. 변경 범위 파악
```bash
git fetch origin main && git diff --stat origin/main...HEAD
```
변경된 모듈과 계층을 정리합니다. `.env`, `.venv`, `__pycache__`가 변경 목록에 있으면 바로 위반입니다.

## 2. 계층 규칙
```bash
python3 .claude/skills/layer-check/check_layers.py
```
위반이 0건이어야 합니다. 변경한 모듈은 `layer-checker` 에이전트로 빈약한 도메인 모델, 레포지토리 변환, 서비스·라우터 책임도 확인합니다.

## 3. 의존성과 import
```bash
uv sync
```
```bash
(cd src && uv run python -c "import main")
```
`main.py`를 import하면 등록된 모든 라우터와 모델이 함께 불러와집니다. 실제 DB 연결 없이도 `DATABASE_URL`만 있으면 됩니다.

## 4. 테스트
```bash
uv run pytest -q -rs
```
`-rs`는 건너뛴 테스트와 이유를 출력합니다. 결과에 `skipped`가 있으면 개수와 이유를 보고서에 적습니다. DB 연결 실패로 건너뛴 테스트는 통과가 아니므로 PostgreSQL(5433)을 띄우고 다시 실행합니다(`fastapi-run` 스킬 2장).

도메인 규칙을 바꿨는데 테스트가 없으면 "테스트 없음"으로 표시하고, 필요한 테스트 목록을 제안합니다.

## 5. 실제 동작
`fastapi-run` 스킬로 서버를 띄우고 smoke 스크립트를 실행합니다. 끝나면 서버를 반드시 끕니다.
```bash
export PORT=8001 LOG=<scratchpad>/uvicorn.log PIDFILE=<scratchpad>/uvicorn.pid
bash .claude/skills/fastapi-run/scripts/run_server.sh db
bash .claude/skills/fastapi-run/scripts/run_server.sh start
BASE=http://localhost:$PORT bash .claude/skills/fastapi-run/scripts/smoke_auth.sh
bash .claude/skills/fastapi-run/scripts/run_server.sh stop
```
smoke 스크립트는 auth와 공통 에러 형식을 확인합니다. 변경한 다른 모듈은 `fastapi-run` 스킬 4장의 시나리오를 직접 실행하고, 아직 없는 기능은 **미구현**으로 적습니다.

auth나 인증 의존성, 미들웨어를 바꿨다면 `auth-security-check` 스킬의 스크립트도 실행합니다(서버 불필요, `e2e_auth.py`는 DB 필요).
```bash
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/static_check.py)
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/jwt_matrix.py)
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/e2e_auth.py)
```
세 스크립트와 smoke 스크립트는 실패하면 종료코드 1을 냅니다.

## 6. 코드 리뷰
내장 `code-review` 스킬로 버그를, 필요하면 `simplify` 스킬로 중복과 복잡도를 확인합니다. auth를 바꿨다면 내장 `security-review`도 실행합니다.

내장 리뷰 스킬은 `origin/HEAD`를 기준으로 diff를 만드는데, 이 ref가 없으면 `unknown revision`으로 실패합니다. 먼저 확인하고 없으면 만듭니다.
```bash
git rev-parse --verify -q origin/HEAD || git remote set-head origin -a
```
그래도 안 되면 `git remote set-head origin main`으로 지정하거나, `git diff origin/main...HEAD`를 직접 읽어 리뷰합니다.

## 보고 형식
| 단계 | 결과 | 비고 |
| --- | --- | --- |
| 변경 범위 | | |
| 계층 규칙 | | |
| import | | |
| 테스트 | | 통과·실패·skip 개수 |
| 실제 동작 | | smoke PASS/FAIL 수, 미구현 모듈 |
| 보안 점검 | | 스크립트별 위반·주의 수 (auth 변경 시) |
| 코드 리뷰 | | |

마지막 줄에 **머지 가능 / 수정 후 머지 / 머지 불가** 중 하나와 그 이유를 적습니다.
