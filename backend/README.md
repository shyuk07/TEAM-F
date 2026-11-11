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

- `src/auth` : 회원, 인증, 포인트 (JWT, 블랙리스트, 비밀번호 재설정, 로그인 잠금)
- `src/stores` : 매장 등록, 위치 좌표 변환, 관리자 승인 연동, 폐점
- `src/catalog` : 메뉴 상품 등록, 당일 마감 할인(Offer), 실시간 재고 제어
- `src/reservations` : 예약 접수, 임시 재고 선점, 픽업번호 발급, 상태 전이
- `src/payments` : 포인트 복합 모의 결제, 취소 위약금 계산 및 환불
- `src/admin` : 점주 입점 심사(승인/반려), 회원/상점 제재, 토큰 블랙리스트 관리
- `src/container.py` : 전 도메인 4계층 인스턴스를 조립하는 중앙 집중식 DI 컨테이너

각 도메인은 도메인 주도 설계(DDD)와 클린 아키텍처 원칙에 따라 다음 4계층으로 엄격히 분리되어 있습니다.

- `domain` : 핵심 엔티티, 도메인 불변식, 비즈니스 규칙 (외부 의존성 없음)
- `application` : 유스케이스, 서비스, 트랜잭션 오케스트레이션, DTO 정의
- `infrastructure` : SQLAlchemy 비동기 ORM 매퍼, 데이터베이스 레포지토리 구현체
- `presentation` : FastAPI 엔드포인트 라우터, Pydantic 요청/응답 스키마, 의존성 주입

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

관리자 계정이 필요하면 `.env`에 `ADMIN_EMAIL`과 `ADMIN_PASSWORD`를 함께 설정합니다(선택). 서버 시작 시 관리자가 없으면 만들어집니다. 자세한 규칙은 `../docs/reference/auth.md`의 "관리자 계정 생성"을 봅니다.

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

**DB 스키마가 바뀐 PR을 받았을 때:** 서버는 시작할 때 DB 테이블이 모델과 맞는지 검사합니다. `create_all`은 이미 있는 테이블에 새 컬럼을 추가하지 못하므로, 컬럼이나 CHECK가 빠져 있으면 무엇이 빠졌는지 알려 주며 시작을 멈춥니다(DB를 자동으로 바꾸지 않습니다). 그때는 `../docs/migrations/`의 SQL 파일을 파일명 순서대로 실행하세요(다시 실행해도 안전합니다). 예: `docker compose exec -T postgres psql -U lastcall -d lastcall < ../docs/migrations/<파일>.sql`. 데이터가 필요 없다면 `docker compose down -v` 후 다시 `up -d`로 DB를 새로 만드는 방법도 있습니다. 검사를 잠시 끄려면 `.env`에 `SCHEMA_CHECK=off`를 둡니다(권장하지 않음). 컬럼을 추가하는 PR은 같은 PR에 `../docs/migrations/` 파일을 함께 넣습니다.

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

### 7. 샘플 데이터 넣기 (선택)

화면 확인용 상점·상품·판매 중 할인과 샘플 계정을 서버 API로 만듭니다. `.env`에 `ADMIN_EMAIL`·`ADMIN_PASSWORD`를 넣고 서버를 켠 상태에서 실행합니다. 다시 실행해도 안전합니다(있는 것은 재사용, 마감된 할인은 새로 등록).

```powershell
uv run python scripts/seed_dev.py
```

서버 주소가 다르면 `$env:SEED_BASE_URL="http://localhost:8001"`처럼 지정합니다. 끝나면 샘플 계정과 확인할 주소가 출력됩니다. 계정 정보는 `scripts/seed_dev.py` 상단 상수에 있습니다(로컬 전용).

시연용으로 **가게 3곳(망원·합정·연남)과 음식 사진 상품 6개**가 필요하면 아래 스크립트를 실행합니다. 사용법과 조건은 `seed_dev.py`와 같고, 사진은 `scripts/demo_images/`에 있습니다. 카카오 키(`KAKAO_REST_API_KEY`)가 있으면 실제 주소 좌표로, 없으면 MockGeocoder 좌표로 상점이 개설됩니다. 계정 정보는 `scripts/seed_demo.py` 상단 상수에 있습니다(로컬 전용).

```powershell
uv run python scripts/seed_demo.py
```

## 개발 방식

- GitHub 저장소 하나를 공동으로 사용합니다.
- 팀원별로 기능 브랜치를 생성합니다.
- 담당 도메인의 4계층 구조를 유지합니다.
- 기능 구현 후 테스트하고 PR로 병합합니다.

## 현재 개발 상태

전체 6개 도메인의 핵심 비즈니스 로직과 API가 모두 구현 및 검증되어 배포 가능한 상태입니다.

- [x] **공통 인프라**: FastAPI 비동기 서버, PostgreSQL 17, Docker Compose, 비동기 세션 및 DI 컨테이너(`container.py`) 구축
- [x] **인증·포인트 (`src/auth`)**: JWT(Access/Refresh), DB 기반 토큰 블랙리스트, 비밀번호 재설정(SMTP), 5회 로그인 실패 계정 잠금, 포인트 적립/차감
- [x] **매장 (`src/stores`)**: 상점 개설 신청, 카카오 로컬 주소-좌표 변환(Mock fallback 지원), 운영 정보 관리, 폐점
- [x] **상품·할인 (`src/catalog`)**: 상점 메뉴(Product) 관리, 당일 마감할인(Offer) 등록/수정/재발행, 비동기 동시성 제어 기반 실시간 재고 차감/복구
- [x] **예약·픽업 (`src/reservations`)**: 수량 및 유효시간 검증, 임시 재고 선점, 4자리 픽업번호 발급, 상태 머신(대기→확정→픽업완료/취소/만료)
- [x] **결제·환불 (`src/payments`)**: 카드+포인트 복합 모의 결제, 취소 시점별 위약금 자동 계산 및 환불, 원자적 롤백 보장
- [x] **관리자 (`src/admin`)**: 점주 입점 심사 승인/반려, 부정 사용자/상점 정지 및 강제 폐점, 만료 토큰 일괄 퍼지
- [x] **테스트 및 보안 검증**: `pytest` 단위/통합 테스트 1,300여 개 전량 통과 완료

## 테스트 실행

### 전체 테스트 실행 (인메모리 단위 테스트)

```powershell
uv run pytest
```

### PostgreSQL 연동 통합 테스트 실행

Docker DB가 실행 중인 상태에서 `-m db` 마커 또는 전체 테스트를 실행합니다.

```powershell
# DB 컨테이너 실행
docker compose up -d

# DB 연동 테스트 포함 실행
uv run pytest -m db
```
## API 명세서

`../docs/reference/`에 모듈별 API 명세가 있습니다. 전체 목록과 공통 규칙은 [../docs/reference/README.md](../docs/reference/README.md)를 봅니다.


## Postman으로 테스트

`../docs/postman/last-call-auth.postman_collection.json`을 Postman에서 **Import**합니다. 서버를 8001 포트로 띄운 뒤 위에서부터 순서대로 실행하거나 **Run collection**으로 한 번에 실행합니다. 회원가입이 매번 새 이메일을 만들고, 로그인이 토큰을 `accessToken` 변수에 저장해 이후 요청에 자동으로 붙입니다. 주소가 다르면 컬렉션 변수 `baseUrl`을 바꿉니다.

## Claude Code 개발 도구

`.claude/` 폴더에 이 프로젝트 전용 에이전트와 스킬이 있습니다. 에이전트는 모두 Sonnet 모델, 사고 수준(effort) `low`로 동작합니다.

### 에이전트 (`.claude/agents/`)

| 이름 | 용도 |
| --- | --- |
| `layer-architect` | 모듈의 도메인 규칙, 테이블, 레포지토리, 서비스, API 명세 설계. 설계안을 `../docs/design/<모듈>.md`에 저장 (코드 수정 안 함) |
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
