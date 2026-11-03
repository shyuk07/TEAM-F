# auth 모듈 설계안 (리팩터링: 추상화 + 의존성 주입)

- 대상: `src/auth` (users, point_log, token_blacklist). 이미 구현·테스트 완료(84 passed)된 모듈을 `backend-invariants` R8·R9·R10, `layer-architecture` §5·§6 구조로 옮긴다.
- 작성: 2026-11-03, `layer-architect`
- **외부 동작 불변.** 엔드포인트, 요청·응답 형식, 에러 코드는 바꾸지 않는다. (`docs/reference/auth.md`와 현재 코드가 일치함을 전제로 한다.)
- 제외: 다른 모듈 설계, `src/error_handlers.py`의 넓은 예외 핸들러 정리.
- 읽은 정본: `AGENTS.md`, `docs/operations/orchestration.md`, `backend-invariants`, `layer-architecture`, `layer-implementation`, `db-schema`, `docs/reference/auth.md`, 현재 `src/auth/**`, `src/main.py`, `src/error_handlers.py`, `src/database.py`, `tests/**`.

---

## 0. 차단 이슈 (실행으로 확인)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-1 | `(cd src && uv run python -c "import main")` | `import main ok` | 현재 코드는 불러와짐. 차단 아님 |
| B-2 | `uv run python -c "import jwt, passlib, dotenv, httpx"` | 성공. `bcrypt 4.3.0`, `passlib 1.7.4` | 의존성 추가 없음. `pyproject.toml` 변경 불필요 |
| B-3 | `uv run python -c "import ... multipart"` | `ModuleNotFoundError: multipart` | 이번 설계는 `Form`·`File`·`OAuth2PasswordRequestForm`을 쓰지 않으므로(D-로그인형식 = JSON) **필요 없음**. 차단 아님 |
| B-4 | `uv run pytest -rs -q` | `84 passed` (DB 테스트 포함, skip 0) | 리팩터링 전 기준선. 구현 후 같은 수 이상 통과해야 함 |
| B-5 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 없음, 경고 3건(`[넓은예외]` error_handlers.py:45·49·53, 범위 밖) | 기준선 |
| B-6 | `ls src/container.py` | 없음 | 신규 생성 대상(차단 아님). `check_layers.py`는 `container.py`를 import 제한에서 이미 제외함 |
| B-7 | `.env.example`의 `JWT_SECRET_KEY` | 있음(`change-me-...` 예시값). `settings.py`가 예시값을 거부하므로 실제 `.env`에 임의 값 필요 | 새 키 없음. 변경 불필요 |
| B-8 | 다른 모듈이 auth 서비스를 쓰는 곳 `Grep AuthApplicationService` | `src/` 안에서는 `auth` 자신과 `main.py`뿐. catalog·stores·reservations·payments는 전부 빈 파일(0줄) | 지금 깨질 외부 호출자 없음. 새 사용법(§6)만 문서화하면 됨 |
| **B-9** | 작은 FastAPI 앱 실험(scratchpad `exp.py`): `dependency_overrides.update({provide: create})` 후 `dependency_overrides.clear()` | 1) `get_db`를 override하면 `create_*`의 하위 `Depends(get_db)`에도 적용되어 서비스·레포가 같은 세션(`True`)을 받음. 2) `.clear()` 뒤 호출은 `NotImplementedError` | **현재 테스트가 깨진다.** `tests/auth/test_api_db.py:77`의 fixture 정리 코드 `app.dependency_overrides.clear()`가 `wire_dependencies(app)`가 넣은 매핑까지 지운다 -> 첫 API 테스트 이후 모든 API 테스트가 `NotImplementedError`. 해결: `.clear()`를 `pop(get_db, None)`으로 바꾼다(§9). `testing.md` 190행도 같은 지시라서 정합 이슈 C-3 |

차단 이슈는 없다. B-9는 구현자가 반드시 처리해야 하는 함정이다.

---

## 1. 결정 표

| ID | 내용 | 상태 | 출처 / 근거 |
| --- | --- | --- | --- |
| D-로그인형식 | 로그인은 JSON 본문 `{"email","password"}`. form 본문은 400 `VALIDATION_ERROR` | **확정** (사용자, 2026-11-02) | `docs/reference/auth.md` §2 |
| D-토큰추출 | `HTTPBearer(auto_error=False)`로 추출, 없거나 비면 `AuthenticationError`(401 `UNAUTHORIZED`) | **확정** | 현재 `dependencies.py` |
| D-에러형식 | `{success, error_code, message}`, 401은 `WWW-Authenticate: Bearer` | **확정** (명세) | `docs/reference/README.md`, R7 |
| D-포인트트랜잭션 | 포인트 메서드(`use/earn/restore/revoke_points`)는 `commit: bool = True` 키워드 인자를 받고, 다른 모듈은 `commit=False`로 호출자 트랜잭션에 참여 | **확정** (현 구현 유지) | R13 |
| D-서비스생성자 | `AuthApplicationService.__init__(session, users, point_logs, blacklist, hasher, tokens)` 전부 필수, 추상 타입만. 기본 생성 제거 | 정본 규칙 적용 | R8, `layer-architecture` §5.4 |
| D-레포구조 | 애그리거트가 3개(User, PointLog, BlacklistedToken)이므로 `domain/repository/` 패키지로 나눈다 | 정본 규칙 적용 | `layer-architecture` §5.1 |
| D-구현체이름 | `SqlAlchemy<추상명>`, `BcryptPasswordHasher`, `JwtTokenProvider` | 정본 규칙 적용 | `layer-architecture` §5.3 |
| D-추상메서드명 | 추상 메서드 이름·시그니처는 **현재 구현과 동일하게 유지**(`add`, `exists`, `exists_by_email`, `count_by_user`, `delete_expired` 포함). `find_*/save/delete` 규칙과 다른 이름은 이번에 바꾸지 않음 | **임시** | 외부 동작·테스트 변경 최소화. 이름 정리는 별도 작업 |
| D-세션이름 | 서비스의 `db` 속성·인자를 `session`으로 바꾼다 | 정본 규칙 적용(제안) | `layer-architecture` §5.4. 테스트는 `build()`가 첫 인자를 위치로 넘겨서 영향 없음 |
| D-해셔싱글턴 | `BcryptPasswordHasher`, `JwtTokenProvider`는 container의 모듈 전역 싱글턴. 더미 해시는 첫 `dummy_verify` 때 만든다(import 시점 bcrypt 비용 제거) | 제안 | `layer-architecture` §6.2 |
| D-토큰설정지연 | `JwtTokenProvider()`는 설정을 지연 로딩(현재와 동일). 서버 시작 시 검증은 `main.py` lifespan의 `get_auth_settings()` 유지 | 확정(현 구현 유지) | `main.py:18` |
| D-타모듈주입 | 다른 모듈은 `AuthApplicationService`를 **생성자 인자로 주입**받는다. 자기 서비스 안에서 `AuthApplicationService(db)`를 만들지 않는다 | 정본 규칙 적용 | `layer-architecture` §3.4 3행, R11·R12 |
| D-인증의존성 | 다른 모듈의 router는 계속 `from auth.presentation.dependencies import CurrentUser, OwnerUser, ...` 별칭을 쓴다 | 확정(현 구현 유지) | `layer-implementation` §6 |
| D-wire위치 | `wire_dependencies(app)`은 `register_exception_handlers(app)` 다음, `include_router` 앞 | 정본 규칙 적용 | `layer-architecture` §6.3 |
| D-상점주role | 상점주 role 값 `OWNER` | **임시** | 명세 "확인 필요", 건드리지 않음 |
| D-사업자번호 | 가입 시 `business_number` 미수집(컬럼은 NULL 허용으로 존재) | **임시** | 명세 "확인 필요", 건드리지 않음 |
| D-상점주승인 | 상점주 승인 대기 상태 미구현(`users`에 컬럼 없음) | **임시/미해결** | `db-schema` §5 항목 7, 건드리지 않음 |
| D-형식오류400 | 형식 오류는 400 `VALIDATION_ERROR`로 통일 | **임시** | 명세는 400, 건드리지 않음 |
| D-로그인제한 | 로그인 시도 횟수 제한 없음 | **임시/미해결** | 건드리지 않음 |
| D-블랙리스트정리 | 블랙리스트 자동 정리 없음. `purge_expired_tokens`는 수동 호출용으로만 존재 | **임시/미해결** | 건드리지 않음 |

---

## 2. 변경 요약 (파일별)

### 2.1 신규
| 파일 | 내용 |
| --- | --- |
| `src/auth/domain/repository/__init__.py` | 빈 파일 |
| `src/auth/domain/repository/user_repository.py` | `UserRepository(ABC)` |
| `src/auth/domain/repository/point_log_repository.py` | `PointLogRepository(ABC)` |
| `src/auth/domain/repository/token_blacklist_repository.py` | `TokenBlacklistRepository(ABC)` |
| `src/auth/domain/service.py` | `PasswordHasher(ABC)`, `TokenProvider(ABC)` |
| `src/container.py` | `create_*` 팩토리, 싱글턴, `wire_dependencies(app)` |
| `tests/test_container.py` | 배선 점검 (§9) |
| `tests/auth/test_api_fake.py` | DB 없이 `provide_auth_service`를 fake로 바꿔 보는 API 테스트 (§9, 선택 권장) |

### 2.2 변경
| 파일 | 변경 |
| --- | --- |
| `src/auth/infrastructure/repositories.py` | 클래스 이름을 `SqlAlchemyUserRepository`, `SqlAlchemyPointLogRepository`, `SqlAlchemyTokenBlacklistRepository`로 바꾸고 각 추상을 상속. 메서드 본문 불변 |
| `src/auth/infrastructure/security.py` | `PasswordHasher` -> `BcryptPasswordHasher(domain.service.PasswordHasher)`로 이름 변경, 더미 해시 지연 생성. `JwtTokenProvider`는 `TokenProvider` 상속 |
| `src/auth/application/service.py` | infrastructure import 전부 제거, 기본 구현체·`_default_hasher`·`_hasher` 삭제, 생성자 필수 인자화, `db` -> `session`, docstring 갱신 |
| `src/auth/presentation/dependencies.py` | `get_auth_service` 삭제, `provide_auth_service()` 플레이스홀더 추가, `get_current_principal`이 `Depends(provide_auth_service)` 사용, `database` import 제거 |
| `src/auth/presentation/router.py` | `Service = Annotated[AuthApplicationService, Depends(provide_auth_service)]` |
| `src/main.py` | `from container import wire_dependencies` 추가, `wire_dependencies(app)` 호출 (라우터 등록 전) |
| `tests/auth/test_security.py` | `PasswordHasher` import를 `BcryptPasswordHasher`로 |
| `tests/auth/test_service.py` | fake가 추상을 상속, 필수 인자 확인 테스트 추가 |
| `tests/auth/test_api_db.py` | 서비스 직접 생성 6곳을 헬퍼로, fixture 정리를 `pop(get_db)`로 (B-9) |

### 2.3 삭제
- `src/auth/presentation/dependencies.py`의 `get_auth_service`
- `src/auth/application/service.py`의 `_hasher`, `_default_hasher`, 기본 인자(`users or UserRepository(db)` 등)
- infrastructure의 `PasswordHasher` 이름(이름은 domain 추상이 가져감)

### 2.4 변경하지 않음
`domain/user.py`, `point_log.py`, `token_blacklist.py`, `token_claims.py`, `exceptions.py`, `infrastructure/models.py`, `settings.py`, `presentation/schemas.py`, `src/error_handlers.py`, `src/database.py`, DB 스키마. **스키마 변경 제안: 없음.**

---

## 3. 도메인 (domain/)

엔티티·VO·규칙(생성자 검증, `User.register`, `Role.for_signup`, 포인트 메서드, `PointLog` 불변, `BlacklistedToken.is_expired`, `TokenClaims.to_blacklist_entry`)은 **그대로**다. 추가되는 것은 추상 두 묶음뿐이다. 모두 순수 파이썬(`abc`, `uuid`, `datetime`)이며 R1을 지킨다.

### 3.1 `domain/repository/user_repository.py`
```python
import uuid
from abc import ABC, abstractmethod

from auth.domain.user import User


class UserRepository(ABC):
    @abstractmethod
    async def find_by_id(self, user_id: uuid.UUID, for_update: bool = False) -> User | None: ...

    @abstractmethod
    async def find_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def save(self, user: User) -> User:
        """신규(id None)는 INSERT, 기존은 UPDATE. flush까지만. 이메일 중복이면 EmailDuplicatedError."""
```

### 3.2 `domain/repository/point_log_repository.py`
```python
class PointLogRepository(ABC):
    @abstractmethod
    async def add(self, log: PointLog) -> PointLog: ...

    @abstractmethod
    async def find_by_user(
        self, user_id: uuid.UUID, *, point_type: PointType | None = None,
        offset: int = 0, limit: int = 20,
    ) -> list[PointLog]:
        """최신순(created_at desc, id desc)."""

    @abstractmethod
    async def count_by_user(self, user_id: uuid.UUID, *, point_type: PointType | None = None) -> int: ...
```

### 3.3 `domain/repository/token_blacklist_repository.py`
```python
class TokenBlacklistRepository(ABC):
    @abstractmethod
    async def add(self, token: BlacklistedToken) -> None:
        """같은 jti가 이미 있으면 무시(멱등)."""

    @abstractmethod
    async def exists(self, jti: str) -> bool: ...

    @abstractmethod
    async def delete_expired(self, now: datetime | None = None) -> int: ...
```

### 3.4 `domain/service.py` (기술 의존 기능의 추상)
```python
import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from auth.domain.token_claims import TokenClaims


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, raw_password: str) -> str: ...

    @abstractmethod
    def verify(self, raw_password: str, hashed_password: str) -> bool:
        """형식이 깨진 해시도 예외 없이 False."""

    @abstractmethod
    def dummy_verify(self, raw_password: str) -> None:
        """사용자가 없을 때도 verify와 같은 비용을 쓰게 하는 타이밍 방어. 결과는 버린다."""


class TokenProvider(ABC):
    @abstractmethod
    def issue(
        self, user_id: uuid.UUID, role: str, now: datetime | None = None
    ) -> tuple[str, TokenClaims]: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """만료·위조·필수 클레임 누락은 AuthenticationError."""
```
- 서비스가 호출하는 메서드(`hash`, `verify`, `dummy_verify`, `issue`, `decode`, 레포 메서드 전부)는 위 추상에 모두 선언되어 있다 -> R10. 구현체 전용 멤버(`JwtTokenProvider.settings` 프로퍼티, `_dummy_hash`)는 서비스·테스트가 접근하지 않는다.

### 3.5 도메인 예외 / 상태 전이
- 예외: 변경 없음(`AuthenticationError` 계열 401, `EmailDuplicatedError` 409).
- 상태 값(`Role`)은 전이가 없다. 포인트 `PointType` 4종(EARN, USE, RESTORE, REVOKE)은 `point_log`의 CHECK와 일치한다(`db-schema` §4).

---

## 4. 인프라 (infrastructure/)

테이블·컬럼·제약·FK는 `models.py` 그대로(users, point_log, token_blacklist; `db-schema`와 일치, 변경 없음).

### 4.1 `repositories.py`
```python
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession): self.session = session
    ...
class SqlAlchemyPointLogRepository(PointLogRepository): ...
class SqlAlchemyTokenBlacklistRepository(TokenBlacklistRepository): ...
```
- 생성자 인자 이름을 `db`에서 `session`으로 바꾼다(`self.db` -> `self.session`, 본문 치환만). 컨테이너에서 위치 인자로 넘기므로 외부 영향 없음.
- `find_*`는 도메인 객체만 반환, `*Model`을 노출하지 않음(R4). `commit()`은 호출하지 않음(R5).
- 동시성: `find_by_id(for_update=True)` -> `SELECT ... FOR UPDATE`(포인트 변경 4개 메서드가 `_locked_user`로 사용). 유지. `token_blacklist.add`는 `ON CONFLICT DO NOTHING`으로 멱등. 가입 경쟁은 `users.email` UNIQUE + `IntegrityError -> EmailDuplicatedError`. 모두 현행 유지.

### 4.2 `security.py`
```python
class BcryptPasswordHasher(PasswordHasher):
    def __init__(self):
        self._dummy_hash: str | None = None   # 첫 dummy_verify 때 생성 (import 시점 비용 제거)

    def hash(self, raw_password: str) -> str: ...
    def verify(self, raw_password: str, hashed_password: str) -> bool: ...   # ValueError/TypeError -> False
    def dummy_verify(self, raw_password: str) -> None: ...


class JwtTokenProvider(TokenProvider):
    def __init__(self, settings: AuthSettings | None = None): ...   # 설정 지연 로딩 유지
    def issue(...) -> tuple[str, TokenClaims]: ...
    def decode(self, token: str) -> TokenClaims: ...
```
- 본문 로직(알고리즘 HS256 고정, `require: exp, sub, jti, role`, 예외 매핑)은 불변. 인자 이름만 추상과 맞춘다(`raw` -> `raw_password`, `hashed` -> `hashed_password`). 이름 변경은 위치 인자 호출만 있어 영향 없음(테스트 `test_security.py`도 위치 인자).

---

## 5. 응용 (application/)

### 5.1 생성자 (R8)
```python
from sqlalchemy.ext.asyncio import AsyncSession

from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import PasswordHasher, TokenProvider
# (infrastructure import 없음)


class AuthApplicationService:
    """다른 모듈은 이 서비스를 생성자 인자로 주입받아 commit=False로 호출한다 (src/container.py에서 연결)."""

    def __init__(
        self,
        session: AsyncSession,
        users: UserRepository,
        point_logs: PointLogRepository,
        blacklist: TokenBlacklistRepository,
        hasher: PasswordHasher,
        tokens: TokenProvider,
    ):
        self.session = session
        self.users = users
        self.point_logs = point_logs
        self.blacklist = blacklist
        self.hasher = hasher
        self.tokens = tokens
```
- 인자 이름 `users, point_logs, blacklist, hasher, tokens`는 **현재와 같다.** 그래서 `tests/auth/test_service.py`의 `AuthApplicationService(db, **parts)`가 그대로 동작한다.
- 모든 인자 필수. 기본값·`or` 기본 생성·모듈 전역 해셔 없음.

### 5.2 메서드 시그니처 (변경 없음, `self.db` -> `self.session`만)
| 메서드 | 시나리오 | commit |
| --- | --- | --- |
| `signup(email, password, role, name=None, phone=None) -> User` | `User.validate_raw_password` -> `Role.for_signup`(해싱 전 ADMIN 거부) -> `hasher.hash` -> `User.register` -> `exists_by_email`(중복이면 `EmailDuplicatedError`) -> `users.save`(경쟁 중복이면 `rollback` 후 재raise) | 성공 시 1회 |
| `login(email, password) -> str` | `find_by_email`(정규화) -> 없으면 `hasher.dummy_verify` 후 `InvalidCredentialsError`, 있으면 `verify` 실패 시 같은 예외 -> `tokens.issue` | 없음(읽기) |
| `authenticate(token) -> AuthenticatedPrincipal` | `tokens.decode` -> `blacklist.exists` -> `TokenRevokedError` -> `users.find_by_id` -> 없으면 `AuthenticationError` | 없음 |
| `logout(claims) -> None` | `blacklist.add(claims.to_blacklist_entry())` | 1회 |
| `get_user(user_id) -> User` | `find_by_id`, 없으면 `LookupError` | 없음 |
| `list_point_logs(user, point_type, page, size) -> PointLogPage` | 범위 검증(page>=0, 1<=size<=100) -> `find_by_user` + `count_by_user` | 없음 |
| `use_points / earn_points / restore_points(user_id, amount, *, commit=True) -> User` | `_locked_user`(FOR UPDATE) -> 도메인 메서드 -> `users.save` -> `point_logs.add` -> `commit` 인자가 True면 commit | 호출자 선택 |
| `revoke_points(user_id, amount, *, commit=True) -> int` | 위와 같음, 실제 회수액 반환, 0이면 로그 없음 | 호출자 선택 |
| `purge_expired_tokens(now=None) -> int` | `blacklist.delete_expired` | 1회 |

- 공용 DTO `AuthenticatedPrincipal`, `PointLogPage`, `MAX_PAGE_SIZE`는 `service.py`에 그대로 둔다.
- 트랜잭션 경계: 단독 유스케이스(signup, logout, purge)는 서비스가 commit. 포인트 4종은 D-포인트트랜잭션대로 `commit=False`로 호출자 트랜잭션에 참여한다. 요청 세션이 닫힐 때 미커밋분은 롤백된다(R13).

---

## 6. 다른 모듈이 auth를 쓰는 방법 (이전 메모와 달라지는 점)

| 이전 사용법 (`layer-implementation` §4, §6) | 새 사용법 |
| --- | --- |
| router: `from auth.presentation.dependencies import CurrentUser, OwnerUser` | **그대로.** `CurrentUser`, `CustomerUser`, `OwnerUser`, `AdminUser`, `CurrentPrincipal`, `require_roles`의 이름·의미·실패 코드(401/403) 불변. 내부가 `provide_auth_service`를 거칠 뿐이다 |
| 서비스 안에서 `self.auth = AuthApplicationService(db)` (같은 세션으로 직접 생성) | **생성자 주입.** 서비스는 `auth: AuthApplicationService`를 인자로 받는다. 서비스 생성자 안에서 다른 서비스를 만들지 않는다(R12). 연결은 `src/container.py`에서만 |
| `commit=False`로 호출, 마지막에 호출자가 한 번 `commit()` | **그대로**(R13, D-포인트트랜잭션) |

새 사용 예 (reservations/payments 구현자 참고; 각 모듈 설계안에서 확정):
```python
# src/reservations/application/service.py
from auth.application.service import AuthApplicationService   # 상대 application 서비스 타입 (R11 허용)

class ReservationApplicationService:
    def __init__(self, session: AsyncSession, reservations: ReservationRepository,
                 catalog: CatalogApplicationService, auth: AuthApplicationService): ...

    async def reserve(self, user_id, offer_id, quantity, points):
        await self.catalog.deduct_stock(offer_id, quantity, commit=False)
        if points:
            await self.auth.use_points(user_id, points, commit=False)
        await self.reservations.save(...)
        await self.session.commit()          # 한 번만
```
```python
# src/container.py (reservations 구역)
def create_reservation_service(
    session: AsyncSession = Depends(get_db),
    reservations: ReservationRepository = Depends(create_reservation_repository),
    catalog: CatalogApplicationService = Depends(create_catalog_service),
    auth: AuthApplicationService = Depends(create_auth_service),
) -> ReservationApplicationService: ...
```
- 같은 세션 보장: 한 요청 안에서 `Depends(get_db)`와 `Depends(create_auth_service)`는 캐시되어 같은 인스턴스를 돌려준다. B-9 실험에서 서비스·레포 세션 동일(`True`) 확인.
- 테스트에서는 fake를 `auth` 인자로 직접 넣거나(서비스 단위 테스트), `app.dependency_overrides[create_auth_service] = ...`로 바꾼다.
- 다른 모듈이 auth의 일부 속성만 필요하면 쓰는 쪽이 포트를 정의하고 container가 어댑터를 주입하는 방법(`layer-architecture` §3.4 2행)도 있다. 현재 필요한 호출(`use/earn/restore/revoke_points`, `get_user`)은 서비스 주입으로 충분하므로 포트는 만들지 않는다.
- auth가 노출하는 메서드(다른 모듈용): `use_points`, `earn_points`, `restore_points`, `revoke_points`(실제 차감액 반환), `get_user`.

---

## 7. 표현 (presentation/)

엔드포인트·스키마·에러 코드는 **변경 없음**(R15). 참고용 현재 표:

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| POST | `/v1/auth/signup` | `SignupRequest` | `UserResponse` | 201 | 400, 409 |
| POST | `/v1/auth/login` | `LoginRequest`(JSON) | `TokenResponse` | 200 | 400(form 포함), 401 |
| POST | `/v1/auth/logout` | Bearer | 본문 없음 | 204 | 401(`UNAUTHORIZED`, `TOKEN_REVOKED`) |
| GET | `/v1/users/me` | Bearer | `UserResponse` | 200 | 401 |
| GET | `/v1/users/me/points` | Bearer, `type`, `page>=0`, `size 1..100` | `PointLogListResponse` | 200 | 400, 401 |

### 7.1 `presentation/dependencies.py`
```python
bearer_scheme = HTTPBearer(auto_error=False)


def provide_auth_service() -> AuthApplicationService:
    """FastAPI Depends 플레이스홀더 (src/container.py에서 바인딩)"""
    raise NotImplementedError("AuthApplicationService 의존성이 주입되지 않았습니다.")


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> AuthenticatedPrincipal: ...   # 본문 동일

# get_current_user, require_roles, CurrentPrincipal/CurrentUser/CustomerUser/OwnerUser/AdminUser: 변경 없음
```
- `from database import get_db`, `AsyncSession` import 삭제. presentation은 infrastructure·database를 모른다(R2, R9).
- `provide_*`는 이 모듈에서 **`provide_auth_service` 하나**다. 다른 모듈이 auth 레포 추상을 직접 주입받을 계획이 없으므로 `provide_user_repository` 등은 만들지 않는다(필요해지면 추가하고 `wire_dependencies`에도 같이 매핑).

### 7.2 `presentation/router.py`
`Service = Annotated[AuthApplicationService, Depends(provide_auth_service)]`로 교체, `get_auth_service` import 삭제. 나머지 동일.

---

## 8. 조립 (`src/container.py`) 와 `main.py`

### 8.1 container 매핑 표

| 플레이스홀더 (`provide_*`) | 팩토리 (`create_*`) | 반환(추상 타입) | 구현체 | 하위 의존 |
| --- | --- | --- | --- | --- |
| `provide_auth_service` | `create_auth_service` | `AuthApplicationService` | (서비스 자체) | `get_db`, 아래 3개 레포, `_password_hasher`, `_token_provider` |
| (없음, 내부용) | `create_user_repository` | `UserRepository` | `SqlAlchemyUserRepository(session)` | `get_db` |
| (없음, 내부용) | `create_point_log_repository` | `PointLogRepository` | `SqlAlchemyPointLogRepository(session)` | `get_db` |
| (없음, 내부용) | `create_token_blacklist_repository` | `TokenBlacklistRepository` | `SqlAlchemyTokenBlacklistRepository(session)` | `get_db` |
| (싱글턴) | `_password_hasher` | `PasswordHasher` | `BcryptPasswordHasher()` | 없음 |
| (싱글턴) | `_token_provider` | `TokenProvider` | `JwtTokenProvider()` (설정 지연 로딩) | 없음 |

### 8.2 코드
```python
# src/container.py
from fastapi import Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from auth.application.service import AuthApplicationService
from auth.domain.repository.point_log_repository import PointLogRepository
from auth.domain.repository.token_blacklist_repository import TokenBlacklistRepository
from auth.domain.repository.user_repository import UserRepository
from auth.domain.service import PasswordHasher, TokenProvider
from auth.infrastructure.repositories import (
    SqlAlchemyPointLogRepository,
    SqlAlchemyTokenBlacklistRepository,
    SqlAlchemyUserRepository,
)
from auth.infrastructure.security import BcryptPasswordHasher, JwtTokenProvider
from auth.presentation.dependencies import provide_auth_service
from database import get_db

# 상태 없는 유틸은 싱글턴 (세션을 가진 객체는 요청마다 만든다)
_password_hasher: PasswordHasher = BcryptPasswordHasher()
_token_provider: TokenProvider = JwtTokenProvider()


# ── auth ─────────────────────────────
def create_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def create_point_log_repository(session: AsyncSession = Depends(get_db)) -> PointLogRepository:
    return SqlAlchemyPointLogRepository(session)


def create_token_blacklist_repository(
    session: AsyncSession = Depends(get_db),
) -> TokenBlacklistRepository:
    return SqlAlchemyTokenBlacklistRepository(session)


def create_auth_service(
    session: AsyncSession = Depends(get_db),
    users: UserRepository = Depends(create_user_repository),
    point_logs: PointLogRepository = Depends(create_point_log_repository),
    blacklist: TokenBlacklistRepository = Depends(create_token_blacklist_repository),
) -> AuthApplicationService:
    return AuthApplicationService(
        session=session, users=users, point_logs=point_logs, blacklist=blacklist,
        hasher=_password_hasher, tokens=_token_provider,
    )


def wire_dependencies(app: FastAPI) -> None:
    app.dependency_overrides.update(
        {
            provide_auth_service: create_auth_service,
        }
    )
```
- 다른 모듈(stores, catalog, reservations, payments)은 같은 파일에 **자기 구역**(`# ── <모듈> ──`)과 매핑을 추가한다. 이 설계안에서는 auth 구역만 다룬다.
- `container.py`는 `main.py`와 함께 모든 모듈을 import할 수 있는 조립 지점이다(`check_layers.py` 제외 대상).
- 순환 없음: container -> (auth.presentation.dependencies -> auth.application.service -> auth.domain) 및 container -> auth.infrastructure -> auth.domain. 서비스 생성자 안에서 다른 서비스를 만들지 않는다(R12).

### 8.3 `main.py`
```python
from container import wire_dependencies
...
register_exception_handlers(app)
wire_dependencies(app)          # 라우터 등록 전에
app.include_router(auth_router)
```
- `auth_models` import(lifespan `create_all`용)와 `get_auth_settings()` 시작 시 검증은 유지.

---

## 9. 테스트 영향과 방침

기준선: `84 passed`. 구현 후 같은 수 이상이 통과해야 하고 `-rs`에서 db 마커 skip이 0이어야 한다(R16).

| 파일 | 영향 | 변경 |
| --- | --- | --- |
| `tests/auth/test_domain.py` | 없음 | 없음 |
| `tests/test_error_handlers.py` | 없음 | 없음 |
| `tests/auth/test_security.py` | `PasswordHasher` import가 깨짐 | `BcryptPasswordHasher`로 교체. 더미 지연 생성 확인 테스트 1건 추가(`dummy_verify`가 예외 없이 동작, 첫 호출 전 `_dummy_hash is None`은 구현 세부라 단언하지 말고 "호출해도 False/None 반환·예외 없음"만 확인) |
| `tests/auth/test_service.py` | 생성자 인자 이름이 같아 그대로 통과. 그러나 R10을 강제하려고 fake가 **추상을 상속**하도록 바꾼다 | `FakeUsers(UserRepository)`, `FakeLogs(PointLogRepository)`, `FakeBlacklist(TokenBlacklistRepository)`, `FakeHasher(PasswordHasher)`. 추상 메서드를 하나라도 빠뜨리면 인스턴스 생성에서 `TypeError`가 나서 서비스가 추상 밖 메서드를 부르는 변경을 잡는다. `tokens`는 `JwtTokenProvider(AuthSettings(...))` 그대로 사용 가능. 추가: `AuthApplicationService(FakeSession())`(필수 인자 누락)이 `TypeError`인지 확인(R8 기본 구현체 금지 회귀 방지) |
| `tests/auth/test_api_db.py` | (1) fixture 정리 `app.dependency_overrides.clear()`(77행)가 배선을 지움(B-9) (2) `AuthApplicationService(db)` 6곳(239, 323, 328, 337, 347행 등)이 인자 부족으로 실패 | (1) `app.dependency_overrides.pop(get_db, None)`으로 교체 (2) 파일 안에 헬퍼 `auth_service(db)`를 둔다: `AuthApplicationService(db, SqlAlchemyUserRepository(db), SqlAlchemyPointLogRepository(db), SqlAlchemyTokenBlacklistRepository(db), BcryptPasswordHasher(), JwtTokenProvider())`. 테스트가 `container`의 비공개 싱글턴(`_password_hasher`)을 import하지 않게 한다. HTTP 경로 테스트는 `main.app`의 실제 배선을 그대로 통과하므로 수정 불필요 |
| `tests/test_container.py` (신규) | R9 실행 검증 | (a) `dependencies` 모듈에서 이름이 `provide_`로 시작하는 함수를 모아(지금은 `auth.presentation.dependencies`; 새 모듈이 생기면 목록에 추가) `wire_dependencies(FastAPI())`의 `dependency_overrides` 키에 모두 있는지 확인 (b) `provide_auth_service()`를 직접 호출하면 `NotImplementedError` (c) `create_auth_service(session, users, point_logs, blacklist)`에 fake를 넘기면 `AuthApplicationService`가 만들어지고 `hasher`가 `PasswordHasher`, `tokens`가 `TokenProvider` 인스턴스. 소유자는 오케스트레이터가 정함(C-4) |
| `tests/auth/test_api_fake.py` (신규, 선택 권장) | DB 없이 router·핸들러·의존성 점검 | `app.dependency_overrides[provide_auth_service] = lambda: AuthApplicationService(FakeSession(), FakeUsers(), ...)`. 로그인 JSON 성공, form 본문 400, 토큰 없음 401 + `WWW-Authenticate: Bearer`, 블랙리스트 후 `TOKEN_REVOKED`를 확인. `finally`에서 **`pop(provide_auth_service)` 후 `wire_dependencies(app)`로 복구**(`clear()` 금지). fake 클래스는 `tests/auth/fakes.py`로 빼서 `test_service.py`와 공유(권장) |

방침 요약: 서비스 테스트는 fake 주입, API 테스트는 `dependency_overrides`(`get_db` 또는 `provide_auth_service`)만 건드리고 **`clear()`하지 않는다**.

---

## 10. 구현 순서 (`layer-implementer`용)

1. domain: `domain/repository/` 패키지 3개 파일 + `domain/service.py`. 이 시점에 `python3 .claude/skills/layer-check/check_layers.py` 통과 확인.
2. infrastructure: `repositories.py` 클래스 이름 변경 + 추상 상속, `security.py`(`BcryptPasswordHasher` 지연 더미, `JwtTokenProvider(TokenProvider)`).
3. application: `service.py` 생성자 필수화, infrastructure import 제거, `db` -> `session`.
4. presentation: `dependencies.py`(`provide_auth_service`), `router.py`.
5. `src/container.py` 작성, `src/main.py`에 `wire_dependencies(app)` 추가.
6. 테스트 수정·추가(§9). 3~5단계가 끝나기 전에는 테스트가 import에서 깨지므로 1~5를 한 번에 진행한다.
7. 완료 게이트(`backend-invariants` §7):
   ```bash
   python3 .claude/skills/layer-check/check_layers.py
   (cd src && uv run python -c "import main")
   uv run pytest -rs
   ```
   추가 확인(정독 규칙용 자가 점검, 판정은 `layer-checker`): `grep -rn "infrastructure" src/auth/application src/auth/presentation`이 0건이어야 하고, `grep -rn "AuthApplicationService(" src`가 `container.py` 외에는 0건이어야 한다.

---

## 11. R1~R16 해소 / 잔여 현황

범례: 해소 = 이 설계로 충족, 유지 = 이미 충족하며 변경 없음, **잔존** = 위반이 남음(범위 밖이라 건드리지 않음).

| 규칙 | 현재 | 이 설계 후 | 비고 |
| --- | --- | --- | --- |
| R1 domain 순수 | 유지 | 유지 | 새 추상은 `abc`/`uuid`/`datetime`만 |
| R2 의존 방향 | **위반**: `application/service.py`가 `auth.infrastructure`를 import(`check_layers.py`가 application->infrastructure를 금지 목록에 두지 않아 자동 검사는 통과) | **해소** | `presentation/dependencies.py`의 `database` import도 제거 |
| R3 도메인 규칙 위치 | 대체로 유지 | **잔존(경미)** | 서비스의 `list_point_logs` 범위 검증(page/size), `revoke_points`의 `if actual > 0`, 로그인 분기는 서비스에 있음. 가입 검증은 도메인 정적 메서드를 호출해 규칙 자체는 도메인에 있음. `User.create(..., hasher)`로 옮기는 안은 `layer-architecture` §3.2에 있으나 이번 범위가 아니므로 미적용(D-임시, C-5) |
| R4 레포 반환 | 유지 | 유지 | |
| R5 commit 위치 | 유지 | 유지 | 레포는 flush까지 |
| R6 예외 | **잔존**: `service.py`의 `LookupError("회원을 찾을 수 없습니다.")`, `repositories.py`의 `LookupError`, `User.require_role`의 `PermissionError`를 그대로 raise | **잔존** | `UserNotFoundError(LookupError)`, `RoleForbiddenError(PermissionError)` 도입은 응답 코드가 같아 안전하지만 범위 밖(C-6) |
| R7 에러 형식 | 유지 | 유지 | 핸들러 불변, 회귀는 기존 테스트가 확인 |
| R8 추상 + 구현체 분리 | **위반** | **해소** | 레포 3종·해셔·토큰이 domain 추상, 서비스는 추상만 필수 인자로 받음 |
| R9 container 조립 | **위반**(container 없음, `get_auth_service`가 서비스 생성) | **해소** | `provide_auth_service` + `wire_dependencies`, `test_container.py`로 매핑 검증 |
| R10 추상 메서드만 호출 | 해당 없음 | **해소** | 서비스가 쓰는 메서드를 모두 추상에 선언, fake가 추상을 상속해 회귀를 잡음 |
| R11 바운디드 컨텍스트 | 유지 | 유지 | 다른 모듈은 `AuthApplicationService`만 주입받음(§6) |
| R12 순환·서비스 내 생성 금지 | 유지(서비스 생성자에서 레포를 만들기는 함) | **해소** | 서비스 생성자에 생성 코드 없음 |
| R13 트랜잭션 | 유지 | 유지 | `commit=False` 관례 + 같은 요청 세션 캐시(B-9로 확인) |
| R14 스키마 일치 | 유지 | 유지 | `models.py` 불변 |
| R15 명세 일치 | 유지 | 유지 | 응답에 `password_hash` 없음 |
| R16 시크릿·테스트 | 유지 | 유지 | skip 0 요구, 신규 의존성 없음 |

참고: `[넓은예외]` 경고 3건(`error_handlers.py`)은 범위 밖이다. 관련 R6 잔존 항목(C-6)을 처리한 뒤 핸들러를 줄일 수 있다.

---

## 12. 정합 이슈 (C-번호)

설계안 작성자는 아래 파일을 고치지 않는다. 오케스트레이터가 사용자 승인 후 처리한다.

| ID | 위치 | 내용 | 제안 |
| --- | --- | --- | --- |
| C-1 | `.claude/skills/layer-implementation/SKILL.md` §4 "여러 모듈이 얽힌 흐름", §4 서비스 예시, 상단 안내 | `self.auth = AuthApplicationService(db)`, `offers or DiscountOfferRepository(db)`가 R8·R12와 충돌. 상단 안내문이 "이전 방식"이라고만 하고 코드는 그대로 남아 있음 | 예시를 §6과 같은 생성자 주입 + `provide_*`/container 방식으로 교체. "auth 코드를 따르고 이 문서를 고친다"는 문장은 auth 리팩터링 후 성립하므로 유지 가능 |
| C-2 | `.claude/skills/layer-implementation/SKILL.md` §6 `get_catalog_service(db=Depends(get_db))`, `AGENTS.md` 문서 맵 "정답 예시 코드 ... (DI·조립은 제외)" | 서비스를 router 모듈에서 직접 생성하는 예시. auth 리팩터링 후에는 DI·조립도 auth가 정답 예시가 됨 | 예시를 `Depends(provide_catalog_service)`로 교체하고, AuthApplicationService 사용 안내를 §6 표로 갱신. AGENTS.md의 "(DI·조립은 제외)" 삭제(리팩터링 완료 후) |
| C-3 | `.claude/skills/layer-implementation/testing.md` 130~190행 (`client` fixture의 `app.dependency_overrides.clear()`, "dependency_overrides도 fixture에서 비웁니다") | `wire_dependencies(app)`이 `main` import 시점에 넣은 매핑을 `clear()`가 지워 이후 테스트가 `NotImplementedError`로 실패(B-9에서 재현) | `clear()` 대신 `pop(get_db, None)` 또는 "건드린 키만 원복"으로 수정. fake 주입 API 테스트 패턴(`provide_*` override 후 `wire_dependencies(app)`로 복구) 추가 |
| C-4 | `docs/operations/orchestration.md` §4 소유권 표 | `tests/test_container.py`(루트)의 소유자가 정해져 있지 않음. `src/container.py`는 "자기 모듈 구역만" 규칙이 있어 이번 신규 생성(파일 최초 작성)의 소유자도 불명확 | 발주서에 "auth implementer가 `src/container.py` 최초 생성과 `tests/test_container.py` 작성"을 명시하거나 소유권 표에 한 줄 추가 |
| C-5 | `.claude/skills/layer-check/check_layers.py` `FORBIDDEN_LAYERS["application"]` | `application -> infrastructure`를 금지하지 않아 R2를 자동 검사하지 못함(`backend-invariants`는 R2를 자동 + 정독으로 표기). 현재 auth가 그 위반인데도 "위반 없음" | auth 리팩터링 완료 후 `"application": {"presentation", "infrastructure"}`로 강화. 다른 모듈도 같은 규칙으로 구현되는 중이므로 시점은 사용자 결정 |
| C-6 | `src/auth/domain/user.py`(`PermissionError`), `src/auth/application/service.py`·`infrastructure/repositories.py`(`LookupError`) | R6 잔존. 이번 범위 밖이라 설계에서 제외 | 별도 작업: `domain/exceptions.py`에 `UserNotFoundError(LookupError)`, `RoleForbiddenError(PermissionError)` 추가(응답 코드 동일, 기존 `pytest.raises(LookupError)`도 통과) |
| C-7 | `src/auth/application/service.py` 클래스 docstring | "payments 등 다른 모듈은 같은 세션으로 이 서비스를 만들어..." 문구가 새 구조와 반대 | §5.1의 docstring으로 교체(구현 시 반영) |
| C-8 | 이 설계가 요청 범위를 넘어 추가한 부분 | (a) `tests/auth/test_api_fake.py` 신규(선택), (b) `db` -> `session` 이름 변경(D-세션이름), (c) `BcryptPasswordHasher` 더미 해시 지연 생성(D-해셔싱글턴), (d) `domain/repository/` 패키지 구조(D-레포구조) | 사용자 확인 필요. 미승인 시 (a)는 건너뛰고 (b)~(d)는 각각 `db` 유지 / 즉시 생성 / 단일 `domain/repository.py`로 대체해도 나머지 설계는 변하지 않음 |

---

## 13. 질문 목록과 임시 기본값

이번 리팩터링은 외부 동작을 바꾸지 않으므로 아래는 **건드리지 않는 기존 미해결 항목**이다. 임시 기본값은 확정이 아니라 현재 구현값이다.

| # | 확인 필요 항목 | 출처 | 임시 기본값 (제안, 미확정) | 근거 | 코드상 위치(바꾸기 쉬운 곳) |
| --- | --- | --- | --- | --- | --- |
| 1 | 상점주 `role` 값 이름 | `docs/reference/auth.md` §1, `db-schema` §5-3 | `OWNER` | 명세 예시 | `auth/domain/user.py` `Role` enum 한 곳 |
| 2 | 상점주 가입 시 `business_number` 입력 여부 | `docs/reference/auth.md` §1 | 미수집(NULL) | `SignupRequest`에 필드 없음 | `presentation/schemas.py`, `User.register` |
| 3 | 상점주 승인 대기 상태 저장 위치 | `db-schema` §5-7, 명세 | 미구현(승인 검사 없음) | 컬럼 없음 | 스키마 변경 필요(stores 설계와 함께 결정) |
| 4 | 잘못된 형식 요청의 상태 코드 | `docs/operations/orchestration.md` §6 | 400 `VALIDATION_ERROR` 통일 | 명세 | `error_handlers.py` |
| 5 | 로그인 시도 제한 | - | 없음 | 명세에 없음 | `AuthApplicationService.login` |
| 6 | 블랙리스트 만료 행 정리 방식 | `db-schema` §2 "만료가 지난 행은 지워도 됨" | 수동 호출(`purge_expired_tokens`)만 | 현 구현 | 스케줄러·lifespan 도입 시 결정 |
| 7 | 추상 메서드 이름 정리(`add/exists/count_by_user/delete_expired` vs `find_*/save/delete`) | `layer-architecture` §5.1 | 현재 이름 유지 | D-추상메서드명, 변경 범위 최소화 | `domain/repository/*.py`와 구현체·fake 동시 변경 필요 |

사용자 결정이 필요한 항목: C-8의 (a)~(d) 승인 여부, C-5(`check_layers.py` 강화 시점), C-6(R6 정리 시점). 나머지는 위 임시 기본값으로 구현을 진행할 수 있다.
