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