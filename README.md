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

### 4. PostgreSQL 실행

Docker Desktop을 켜고 실행합니다.

```powershell
docker compose up -d
```

상태 확인:

```powershell
docker compose ps
```

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
## Claude Code 개발 도구

`.claude/` 폴더에 이 프로젝트 전용 에이전트와 스킬이 있습니다. 에이전트는 모두 Sonnet 모델로 동작합니다.

### 에이전트 (`.claude/agents/`)

| 이름 | 용도 |
| --- | --- |
| `layer-architect` | 모듈의 도메인 규칙, 테이블, 레포지토리, 서비스, API 명세 설계 (읽기 전용) |
| `layer-implementer` | 모듈 하나의 4계층 코드 구현과 검사 |
| `layer-checker` | 프로젝트 전체 4계층 규칙 점검 (읽기 전용) |

### 스킬 (`.claude/skills/`)

| 이름 | 용도 |
| --- | --- |
| `layer-implementation` | 계층별 코드 규칙과 예시 코드 |
| `layer-check` | 계층 구조·import 방향 자동 검사 |
| `fastapi-run` | DB와 서버 실행, 200/400/401/404 시나리오 확인 |
| `auth-security-check` | OAuth2, JWT 블랙리스트, 비밀번호 해싱, 권한 점검 |
| `pre-merge-check` | 머지 전 검증 순서 |

계층 규칙 검사는 Claude 없이도 실행할 수 있습니다.

```powershell
python .claude/skills/layer-check/check_layers.py
```
