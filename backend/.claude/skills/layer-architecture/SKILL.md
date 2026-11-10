---
name: layer-architecture
description: 마감 직전 프로젝트의 4계층(표현·응용·도메인·인프라) 책임, 의존 방향, DDD 원칙(유비쿼터스 언어, 애그리거트, 바운디드 컨텍스트, 도메인 이벤트)과 의존성 주입 구조(domain 추상 레포지토리·도메인 서비스, infrastructure 구현체, presentation `provide_*` 플레이스홀더, `src/container.py` 조립)를 정합니다. 모듈을 설계하거나, 레포지토리·외부 기능의 추상화와 주입을 만들거나, 모듈 간 의존·순환 의존을 판단하거나, container.py에 의존성을 연결할 때 사용합니다. 계층별 코드 패턴은 layer-implementation, 자동 검사는 layer-check 스킬을 씁니다.
---

# 4계층 아키텍처와 의존성 주입

이 스킬은 **무엇을 어디에 두고 왜 그렇게 하는가**를 정합니다. 계층별 코드 작성 패턴은 `layer-implementation`, import 방향 자동 검사는 `layer-check`가 정본입니다.

**의존성 주입(§5)과 조립(§6)은 이 스킬이 정본입니다.** `layer-implementation`의 예시나 기존 `src/auth`가 "서비스가 레포지토리를 직접 생성하는" 방식이면 이전 방식이며, 새 코드와 수정 코드는 이 스킬을 따릅니다.

## 1. 계층 책임

| 계층 | 책임 | 파일 |
| --- | --- | --- |
| 표현 (Presentation) | 요청·응답 검증(Pydantic), 인증 의존성, 주입 지점 선언(`provide_*`) | `presentation/schemas.py`, `router.py`, `dependencies.py` |
| 응용 서비스 (Application) | 유스케이스 흐름, 트랜잭션 경계(`commit`), 다른 컨텍스트 조합 | `application/service.py` |
| 도메인 (Domain) | 엔티티·VO·애그리거트, 도메인 규칙, 도메인 예외, **추상 레포지토리, 추상 도메인 서비스** | `domain/<엔티티>.py`, `domain/exceptions.py`, `domain/repository.py`, `domain/service.py` |
| 인프라 (Infrastructure) | ORM 모델, **레포지토리 구현체, 도메인 서비스 구현체**(해싱·토큰·외부 API) | `infrastructure/models.py`, `repositories.py`, `security.py` 등 |
| 조립 (Container) | 추상 ↔ 구현체 연결, 싱글턴 유틸 생성 | `src/container.py` (모듈 밖, 하나) |

## 2. 의존 방향

```text
presentation ──▶ application ──▶ domain ◀── infrastructure
      ▲                                          ▲
      └──────────── src/container.py ────────────┘  (조립 지점만 양쪽을 안다)
```

- domain은 순수 파이썬이다. fastapi, sqlalchemy, pydantic, `database`, 다른 계층을 import하지 않는다.
- application은 domain의 **추상 타입**에만 의존한다. infrastructure 구현체를 import하지 않는다.
- presentation은 infrastructure를 import하지 않는다. 서비스는 `provide_*` 플레이스홀더로 받는다.
- 구현체를 아는 곳은 `src/container.py`와 `src/main.py`뿐이다.

## 3. 도메인 설계 원칙

### 3.1 유비쿼터스 언어
- 코드·문서·대화에서 같은 용어를 쓴다. 정본은 `../docs/reference/<모듈>.md`(API 명세)와 `db-schema` 스킬의 테이블·컬럼명이다.
- 새 용어는 설계안(`../docs/design/<모듈>.md`)에 정의하고 명세와 맞춘다.

### 3.2 도메인 모델
- 도메인 규칙은 엔티티의 메서드와 생성 팩토리(`create`)에 둔다. 서비스에 비즈니스 if-else를 두지 않는다.
- 규칙 위반은 모듈 전용 도메인 예외로 낸다. HTTP 변환은 전역 예외 핸들러가 한다.
- 규칙에 외부 기능이 필요하면(예: 해싱) **추상 도메인 서비스를 메서드 인자로 받는다**. 엔티티는 구현체를 모른다.

```python
# <모듈>/domain/user.py
@classmethod
def create(cls, email: str, raw_password: str, hasher: PasswordHasher) -> "User":
    cls._validate_password(raw_password)
    return cls(email=email, password_hash=hasher.hash(raw_password), ...)
```

### 3.3 애그리거트
- 같은 책임과 일관성을 보장하는 객체 묶음이다. 루트 엔티티 + 값 객체(VO).
- 내부 VO는 루트를 통해서만 읽고 바꾼다. 레포지토리는 **애그리거트 루트 단위**로 만든다.
- 한 트랜잭션은 원칙적으로 한 애그리거트만 바꾼다. 여러 개를 바꾸면 설계안에 트랜잭션 경계와 잠금 순서를 적는다.

### 3.4 바운디드 컨텍스트
- 모듈 하나가 하나의 컨텍스트다. 같은 실체도 컨텍스트마다 필요한 속성과 이름이 다르다(회원 / 상점주 / 예약자).
- 다른 컨텍스트의 **ORM 모델·레포지토리 구현체·application 서비스 내부**를 쓰지 않는다.
- 다른 컨텍스트의 데이터가 필요할 때:
  | 상황 | 방법 |
  | --- | --- |
  | 상대 컨텍스트의 조회 규약을 그대로 써도 될 때 | 상대 `domain/repository.py`의 **추상 레포지토리**를 생성자로 받고, container에서 구현체를 주입 |
  | 상대에게 일부 속성만 필요하거나, 서로를 필요로 할 때 | **쓰는 쪽** `domain/`(또는 `application/ports.py`)에 포트(ABC/Protocol)를 정의하고, container에서 상대 모듈 기반 어댑터를 주입 |
  | 상대 상태를 바꿔야 할 때(재고 차감 등) | 상대 application 서비스를 생성자로 받아 호출(같은 요청 세션), 호출자가 마지막에 한 번 `commit()` |

### 3.5 도메인 이벤트
- 단일 책임 원칙에 따라 자기 책임 밖의 일은 해당 컨텍스트에 요청한다.
- 현재 요청 수단은 §3.4의 동기 호출이다. 비동기 이벤트 버스는 설계안에서 결정한 뒤 도입한다.

## 4. 순환 의존 금지
- 두 컨텍스트가 서로를 필요로 하면 양쪽 모두 포트를 정의하고, 연결은 `src/container.py`에서만 한다.
- 서비스 생성자 안에서 다른 서비스를 만들지 않는다(무한 재귀). 생성은 container의 팩토리만 한다.

## 5. 추상화 규칙

### 5.1 추상 레포지토리 — `domain/repository.py`
```python
import uuid
from abc import ABC, abstractmethod

from user.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID) -> User | None: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...
```
- 메서드는 도메인 객체만 주고받는다. 이름은 `find_*`, `save`, `delete`.
- 애그리거트가 여럿이면 `domain/repository/<애그리거트>_repository.py`로 나눈다.

### 5.2 추상 도메인 서비스 — `domain/service.py`
```python
from abc import ABC, abstractmethod


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, raw_password: str) -> str: ...

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool: ...
```
- 해싱, 토큰, 시계, 외부 API처럼 **도메인 규칙이 필요로 하지만 기술에 의존하는 기능**을 추상화한다.

### 5.3 구현체 — `infrastructure/`
```python
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        model = await self.session.scalar(select(UserModel).where(UserModel.id == user_id))
        return self._to_domain(model) if model else None
```
- 이름은 `<기술><추상명>`(예: `SqlAlchemyUserRepository`, `BcryptPasswordHasher`, `JwtTokenProvider`).
- 레포지토리는 `flush()`까지만 한다. **`commit()`은 application 서비스가 한다**(여러 레포·컨텍스트를 한 트랜잭션으로 묶기 위해).

### 5.4 응용 서비스 — 추상만 받는다
```python
class UserService:
    def __init__(self, session: AsyncSession, repository: UserRepository, hasher: PasswordHasher):
        self.session = session
        self.repository = repository
        self.hasher = hasher
```
- 생성자 인자는 모두 **필수**다. `repository or SqlAlchemyUserRepository(db)` 같은 기본 생성을 두지 않는다.
- 테스트는 fake 구현체를 넘겨 DB 없이 검증한다.

## 6. 조립 — `presentation/dependencies.py` + `src/container.py`

### 6.1 플레이스홀더 (`<모듈>/presentation/dependencies.py`)
```python
from user.application.service import UserService


def provide_user_service() -> UserService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("UserService 의존성이 주입되지 않았습니다.")
```
- router와 인증 의존성은 `Depends(provide_*)`만 쓴다. 구현체를 만들지 않는다.
- 다른 컨텍스트가 쓸 추상(예: `UserRepository`)도 `provide_*`로 선언할 수 있다.

### 6.2 컨테이너 (`src/container.py`)
```python
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from user.application.service import UserService
from user.domain.repository import UserRepository
from user.infrastructure.repositories import SqlAlchemyUserRepository
from user.infrastructure.security import BcryptPasswordHasher
from user.presentation.dependencies import provide_user_repository, provide_user_service

# 상태 없는 유틸은 싱글턴
_password_hasher = BcryptPasswordHasher()


# ── user ─────────────────────────────
def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_user_service(
    session: AsyncSession = Depends(get_db),
    repository: UserRepository = Depends(create_user_repository),
) -> UserService:
    return UserService(session=session, repository=repository, hasher=_password_hasher)


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_user_repository: create_user_repository,
            provide_user_service: create_user_service,
        }
    )
```
- 팩토리 이름은 `create_<대상>`, 모듈별 구역 주석으로 나눈다.
- 한 요청 안에서 `Depends(get_db)`는 같은 세션을 돌려준다. 그래서 여러 컨텍스트의 레포·서비스가 한 트랜잭션을 공유한다.
- 상태 없는 유틸(해셔·토큰 발급기)만 모듈 전역 싱글턴으로 둔다. 세션을 가진 객체는 요청마다 만든다.
- 테스트는 `app.dependency_overrides`로 팩토리를 fake로 바꾼다.

### 6.3 등록 (`src/main.py`)
```python
from container import wire_dependencies

register_exception_handlers(app)
wire_dependencies(app)          # 라우터 등록 전에
app.include_router(user_router)
```
- `container.py`와 `main.py`는 모든 모듈을 import할 수 있는 **조립 지점**이다(`layer-check` 제외 대상).

## 7. 새 모듈 체크리스트
1. `domain/`: 엔티티(규칙 메서드), `exceptions.py`, `repository.py`(ABC), 필요 시 `service.py`(ABC)
2. `infrastructure/`: `models.py`, `repositories.py`(ABC 구현, `_to_domain`), 외부 기능 구현체
3. `application/service.py`: 추상만 받는 생성자, 흐름 조율, `commit()`
4. `presentation/`: `schemas.py`, `dependencies.py`(`provide_*`), `router.py`(`Depends(provide_*)`)
5. `src/container.py`: `create_*` 팩토리와 `wire_dependencies` 매핑 추가
6. `src/main.py`: 모델 import(FK 대상 모듈 먼저), 라우터 등록
7. `python3 .claude/skills/layer-check/check_layers.py`, `(cd src && uv run python -c "import main")`

## 8. 규칙
이 스킬의 금지 사항은 `backend-invariants`의 R5(commit 위치), R8(추상만 받기), R9(container 매핑), R10(추상 메서드만 호출), R11~R12(컨텍스트·순환)가 정본입니다.
