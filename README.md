# 마감 직전 (Last Call)

마감 시간이 가까워진 매장의 할인 음식을 고객이 예약하고,
결제 후 직접 픽업하는 서비스의 백엔드 프로젝트입니다.

## 기술 스택

- Python 3.13
- FastAPI
- PostgreSQL 17
- SQLAlchemy Async
- Docker Compose
- uv
- Alembic
- pytest

## 프로젝트 구조

- `src/auth` : 회원, 인증, 포인트
- `src/stores` : 매장, 관리자 승인
- `src/catalog` : 상품, 할인, 재고
- `src/reservations` : 예약, 취소, 픽업
- `src/payments` : 모의 결제, 환불

각 기능은 다음 4계층으로 구성합니다.

- domain
- application
- infrastructure
- presentation

## 로컬 개발 환경 실행

### 1. 사전 준비

다음 프로그램이 필요합니다.

- Python 3.13
- uv
- Docker Desktop
- Git

### 2. 라이브러리 설치

프로젝트 폴더에서 실행합니다.

```powershell
uv sync
```

### 3. 환경변수 설정

```powershell
Copy-Item .env.example .env
```

이미 `.env`가 있다면 덮어쓰지 않습니다.

복사한 뒤 `.env`의 `JWT_SECRET_KEY`를 **반드시 임의의 값으로 바꿉니다**(32자 이상). `.env.example`의 예시값(`change-me...`)을 그대로 두면 서버가 시작하지 않습니다. 임의의 값은 다음 명령으로 만들 수 있습니다.

```powershell
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

관리자 계정이 필요하면 `.env`에 `ADMIN_EMAIL`과 `ADMIN_PASSWORD`를 함께 설정합니다(선택). 서버 시작 시 관리자가 없으면 만들어집니다. 자세한 규칙은 `docs/reference/auth.md`의 "관리자 계정 생성"을 봅니다.

비밀번호 재설정 코드를 실제 메일로 받으려면 `.env`에 `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`(선택 `SMTP_PORT`, 기본 587)을 모두 채우고 서버를 시작합니다. 비워 두면 코드는 서버 로그(`auth.password_reset`)에만 남습니다. 일부만 채우면 서버가 시작하지 않습니다. Gmail 등은 앱 비밀번호가 필요합니다.

### 4. PostgreSQL 실행

Docker Desktop을 켜고 실행합니다.

```powershell
docker compose up -d
```

상태 확인:

```powershell
docker compose ps
```

**DB 스키마가 바뀐 PR을 받았을 때:** 서버는 시작할 때 DB 테이블이 모델과 맞는지 검사합니다. `create_all`은 이미 있는 테이블에 새 컬럼을 추가하지 못하므로, 컬럼이나 CHECK가 빠져 있으면 무엇이 빠졌는지 알려 주며 시작을 멈춥니다(DB를 자동으로 바꾸지 않습니다). 그때는 `docs/migrations/`의 SQL 파일을 파일명 순서대로 실행하세요(다시 실행해도 안전합니다). 예: `docker compose exec -T postgres psql -U lastcall -d lastcall < docs/migrations/<파일>.sql`. 데이터가 필요 없다면 `docker compose down -v` 후 다시 `up -d`로 DB를 새로 만드는 방법도 있습니다. 검사를 잠시 끄려면 `.env`에 `SCHEMA_CHECK=off`를 둡니다(권장하지 않음). 컬럼을 추가하는 PR은 같은 PR에 `docs/migrations/` 파일을 함께 넣습니다.

### 5. FastAPI 실행

```powershell
uv run uvicorn main:app --app-dir src --reload --port 8001
```

### 6. 실행 확인

Swagger API 문서:

http://127.0.0.1:8001/docs

DB 연결 확인:

http://127.0.0.1:8001/health/db

정상적으로 연결되면 다음과 같이 응답합니다.

```json
{
  "status": "ok",
  "database": "connected"
}
```

## 개발 방식

- GitHub 저장소 하나를 공동으로 사용합니다.
- 팀원별로 기능 브랜치를 생성합니다.
- 담당 도메인의 4계층 구조를 유지합니다.
- 기능 구현 후 테스트하고 PR로 병합합니다.

## 현재 개발 상태

공통 FastAPI 및 PostgreSQL 개발 환경 구성 완료.

실제 도메인 기능과 API는 담당별로 구현할 예정입니다.
## API 명세서

`docs/reference/`에 모듈별 API 명세가 있습니다. 전체 목록과 공통 규칙은 [docs/reference/README.md](docs/reference/README.md)를 봅니다.


## Postman으로 테스트

`docs/postman/last-call-auth.postman_collection.json`을 Postman에서 **Import**합니다. 서버를 8001 포트로 띄운 뒤 위에서부터 순서대로 실행하거나 **Run collection**으로 한 번에 실행합니다. 회원가입이 매번 새 이메일을 만들고, 로그인이 토큰을 `accessToken` 변수에 저장해 이후 요청에 자동으로 붙입니다. 주소가 다르면 컬렉션 변수 `baseUrl`을 바꿉니다.

## Claude Code 개발 도구

`.claude/` 폴더에 이 프로젝트 전용 에이전트와 스킬이 있습니다. 에이전트는 모두 Sonnet 모델, 사고 수준(effort) `low`로 동작합니다.

### 에이전트 (`.claude/agents/`)

| 이름 | 용도 |
| --- | --- |
| `layer-architect` | 모듈의 도메인 규칙, 테이블, 레포지토리, 서비스, API 명세 설계. 설계안을 `docs/design/<모듈>.md`에 저장 (코드 수정 안 함) |
| `layer-implementer` | 모듈 하나의 4계층 코드 구현과 검사 |
| `layer-checker` | 프로젝트 전체 4계층 규칙 점검 (읽기 전용) |
| `layer-reviewer` | 변경 코드의 정확성 리뷰: 동시성·원자성·불변식·명세 일치·테스트 단언 (읽기 전용) |
| `verifier` | 서버 실행, smoke·보안 점검 스크립트, 테스트, 머지 전 점검 실행과 결과 보고 (코드 수정 안 함) |

### 스킬 (`.claude/skills/`)

| 이름 | 용도 |
| --- | --- |
| `layer-implementation` | 계층별 코드 규칙과 예시 코드 |
| `db-schema` | PostgreSQL 테이블 관계도(ERD), 권장 DDL(`schema.sql`), SQLAlchemy 매핑 규칙 |
| `layer-check` | 계층 구조·import 방향 자동 검사 |
| `fastapi-run` | DB와 서버 실행, 200/400/401/404 시나리오 확인 (`scripts/run_server.sh`, `scripts/smoke_auth.sh`) |
| `auth-security-check` | OAuth2, JWT 블랙리스트, 비밀번호 해싱, 권한 점검 (`scripts/static_check.py`, `jwt_matrix.py`, `e2e_auth.py`) |
| `pre-merge-check` | 머지 전 검증 순서 |

계층 규칙 검사는 Claude 없이도 실행할 수 있습니다.

```powershell
python .claude/skills/layer-check/check_layers.py
```

서버 실행·smoke 테스트와 auth 보안 점검 스크립트도 직접 실행할 수 있습니다. 셸 스크립트는 bash(Windows는 Git Bash나 WSL)가 필요하고, 실패하면 종료코드 1을 냅니다.

```bash
bash .claude/skills/fastapi-run/scripts/run_server.sh db      # Docker 데몬 확인 후 PostgreSQL 실행
bash .claude/skills/fastapi-run/scripts/run_server.sh start   # 8001 포트로 서버 실행 (PORT, LOG로 변경)
BASE=http://localhost:8001 bash .claude/skills/fastapi-run/scripts/smoke_auth.sh
bash .claude/skills/fastapi-run/scripts/run_server.sh stop

cd src
uv run python ../.claude/skills/auth-security-check/scripts/static_check.py   # 정적 검사
uv run python ../.claude/skills/auth-security-check/scripts/jwt_matrix.py     # 위조 토큰·해싱 (DB 불필요)
uv run python ../.claude/skills/auth-security-check/scripts/e2e_auth.py       # API E2E (DB 필요)
```
