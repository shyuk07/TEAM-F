# auth 모듈 현재 설계 (구현 완료: 추상화 + 의존성 주입)

- 상태: **구현 완료.** 이 문서는 리팩터링 계획으로 쓰였고, 그 구현은 `main`에 머지됐다(`a7e5c39 refactor(auth): inject abstractions via src/container.py`, `0554aed chore(claude): forbid application->infrastructure in layer check`, PR #8 머지 `e36bd21`). 현재는 `main`(HEAD `671d457`)의 auth 모듈의 정본 설계다.
- 대상: `src/auth` (users, point_log, token_blacklist), 조립 `src/container.py`. `backend-invariants` R8·R9·R10, `layer-architecture` §5·§6 구조.
- 작성: 2026-11-03 `layer-architect`. 같은 날 사용자 결정 반영. **2026-11-03 최신화:** 구현 후 코드(`src/auth/**`, `src/container.py`, `src/main.py`, `src/error_handlers.py`, `tests/auth/**`, `tests/test_container.py`)와 대조해 갱신. 계획과 다르게 구현된 부분은 "구현 메모"로 파일:줄과 함께 표시했다.
- **외부 동작 불변.** 엔드포인트, 요청·응답 형식, 에러 코드는 바뀌지 않았다. `schemas.py`·`router.py`를 `docs/reference/auth.md`와 대조해 일치함을 확인했다(§7, §14).
- 제외: 다른 모듈 설계, `src/error_handlers.py`의 넓은 예외 핸들러 정리, R6 잔존분 정리(후속 작업으로 확정).
- 읽은 정본: `AGENTS.md`, `docs/operations/orchestration.md`, `backend-invariants`, `layer-architecture`, `layer-implementation`, `db-schema`(`SKILL.md`, `schema.sql`), `docs/reference/auth.md`, `docs/reference/README.md`, `src/auth/**`, `src/container.py`, `src/main.py`, `src/error_handlers.py`, `src/database.py`, `tests/**`, `docs/design/stores.md`(읽기만, 정합 확인용).
- **2026-11-04 추가 범위(관리자 기능, worktree `claude/auth-admin`, `origin/main` `fbe5ecc`):** (1) ADMIN 계정 생성 방법 (2) 관리자 회원 조회 EP (3) 블랙리스트 만료 토큰 정리 (4) 포인트 연동 가이드(EP 없음). 설계는 §0.2, §1(D-관리자생성·D-관리자조회·D-블랙리스트정리·D-포인트비공개·D-포인트연동), §6.1, §7.5, §12.5(C-16~C-19), §13(질문 14~19). **사용자가 2026-11-04에 확정했다**(질문 14~18, C-19 허용, D-포인트 2건). 질문 19(관리자 포인트 수동 조정 API)만 이번 범위 아님. 기존 확정 결정(§1)은 바꾸지 않았다.
- 현재 상태 확인(2026-11-03, HEAD `671d457`): `python3 .claude/skills/layer-check/check_layers.py` -> 위반 없음(경고 3건), `(cd src && uv run python -c "import main")` -> 성공, `uv run pytest -rs -q` -> `89 passed`(skip 0, DB 테스트 포함).

---

## 0. 차단 이슈 (실행으로 확인)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-1 | `(cd src && uv run python -c "import main")` | `import main ok` | 현재 코드는 불러와짐. 차단 아님 |
| B-2 | `uv run python -c "import jwt, passlib, dotenv, httpx"` | 성공. `bcrypt 4.3.0`, `passlib 1.7.4` | 의존성 추가 없음. `pyproject.toml` 변경 불필요 |
| B-3 | `uv run python -c "import ... multipart"` | `ModuleNotFoundError: multipart` | 이번 설계는 `Form`·`File`·`OAuth2PasswordRequestForm`을 쓰지 않으므로(D-로그인형식 = JSON) **필요 없음**. 차단 아님 |
| B-4 | `uv run pytest -rs -q` | 리팩터링 전 `84 passed`. **현재 `89 passed`**(skip 0). 파일별 수집: test_api_db 24, test_domain 19, test_security 13, test_service 15, test_container 3, test_error_handlers 15 | 해소. 증가분 5 = `test_container.py` 3 + `test_security.py` 더미 해시 1 + `test_service.py` 필수 인자 1 |
| B-5 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 없음, 경고 3건(`[넓은예외]` error_handlers.py:45·49·53, 범위 밖). 검사 파일 70개 | 현재도 같음. application->infrastructure 금지가 `check_layers.py:41`에 반영된 판으로 통과(C-5) |
| B-6 | `ls src/container.py` | 계획 시점 없음. **현재 있음**(59줄, `container.py:1-59`) | 해소. `check_layers.py`는 `container.py`를 import 제한에서 제외 |
| B-7 | `.env.example`의 `JWT_SECRET_KEY` | 있음(`change-me-...` 예시값). `settings.py`가 예시값을 거부하므로 실제 `.env`에 임의 값 필요 | 새 키 없음. 변경 불필요 |
| B-8 | 다른 모듈이 auth 서비스를 쓰는 곳 `Grep AuthApplicationService` | `src/` 안에서는 `auth` 자신과 `container.py`뿐(`Grep "provide_|AuthApplicationService" src`). catalog·stores·reservations·payments는 아직 전부 빈 파일(0줄) | 지금 깨질 외부 호출자 없음. 새 사용법(§6)만 문서화하면 됨 |
| **B-9** | 작은 FastAPI 앱 실험(scratchpad `exp.py`): `dependency_overrides.update({provide: create})` 후 `dependency_overrides.clear()` | 1) `get_db`를 override하면 `create_*`의 하위 `Depends(get_db)`에도 적용되어 서비스·레포가 같은 세션(`True`)을 받음. 2) `.clear()` 뒤 호출은 `NotImplementedError` | 계획 시점의 함정. `tests/auth/test_api_db.py`의 fixture 정리 `clear()`가 배선까지 지우는 문제. **구현에서 해소:** `tests/auth/test_api_db.py:94`가 `app.dependency_overrides.pop(get_db, None)`을 쓴다. 그러나 같은 지시가 남은 `testing.md:186`은 아직 `clear()`다(C-3 미해결) |
| B-10 | (신규, 2026-11-03) `Grep "infrastructure\|database" src/auth/application src/auth/presentation` | 일치 0건(종료 코드 1) | R2·R9 자가 확인 통과(§10 7단계 조건) |
| B-11 | (신규) `uv run python -c "import multipart"` | `ModuleNotFoundError`. `pyproject.toml`에 `python-multipart` 없음 | 변함없음. auth는 `Form`·`File`을 쓰지 않으므로 차단 아님(D-로그인형식 JSON). form 본문 거부는 `tests/auth/test_api_db.py`의 `test_login_form_rejected`가 확인 |

차단 이슈는 없다.

### 0.1 `OptionalUser` 추가 작업 확인 (2026-11-04, worktree `claude/auth-optional-user`, HEAD `30f549c` = auth 커밋 2개 + `origin/main` `3fe2389` 병합)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-12 | `(cd src && uv run python -c "import main")` | `import main ok` | 차단 아님 |
| B-13 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 2건: `payments/application/service.py:19`, `:20` (application -> payments.infrastructure). 경고 3건(`[넓은예외]`) | **기준선**(이미 main에 있음, 이번 작업과 무관). 구현 후 위반이 이 2건에서 늘지 않아야 함 |
| B-14 | 환경 | Docker가 꺼져 DB 테스트 skip. 기준선 `332 passed, 90 skipped` (오케스트레이터 제공값, 이번에 실행하지 않음) | 차단 아님(환경). R16: skip은 통과가 아니므로 구현 단계에서 오케스트레이터가 DB를 켜고 `skip 0`으로 다시 확인. 설계자는 DB를 띄우지 않았음 |
| B-15 | 새 패키지 필요 여부 | 설계는 `fastapi.Request`(이미 설치)만 추가로 씀. `pyproject.toml` 변경 없음. `.env.example` 새 키 없음 | 차단 아님 |
| B-16 | `Grep "OptionalUser\|get_optional_user\|bearer_scheme" src tests` | 정의는 `src/catalog/presentation/dependencies.py:37-46`뿐. 사용은 `src/catalog/presentation/router.py:10`(import), `:54`(#2 목록), `:100`(#4 상세). `tests/**`에서 직접 import 0건 | catalog 교체 시 영향 범위(§6.2) |
| **B-17** | 실험(scratchpad `probe.py`): `HTTPBearer(auto_error=False)`에 `Authorization` 헤더 값별로 `credentials` 확인 | 헤더 없음 `None`, `Basic abc` **`None`**, `Bearer`(값 없음) `None`, `Bearer ` `None`, `Token tok` `None`, `Bearer tok`/`bearer tok` -> `credentials="tok"` | **핵심 사실.** `HTTPBearer(auto_error=False)`는 "헤더 없음"과 "Bearer가 아닌 헤더"를 구분하지 못한다. 현재 catalog `get_optional_user`는 `credentials is None`이면 `None`을 돌려주므로 `Basic ...`·`Bearer`(토큰 없음) 헤더를 **조용히 비로그인으로 처리한다**. 필수 인증(`get_current_principal`)은 같은 입력에서 401(`test_basic_scheme_is_unauthorized`). 구분하려면 raw 헤더를 읽어야 한다(§7.3) |
| B-18 | `src/catalog/presentation/dependencies.py:37-46`, `tests/catalog/test_api_db.py:166-170` | 현재 구현: 헤더 없음/빈 토큰 `None`, 토큰이 있으면 `authenticate()` 결과 `.user`(위조·만료·로그아웃·없는 사용자는 `AuthenticationError`/`TokenRevokedError` -> 401). 테스트가 `Bearer bad.token`으로 `GET /v1/stores/{id}/products` -> 401을 고정 | 무효 토큰 -> 401은 **이미 테스트로 고정된 현재 동작**(D-선택인증-무효토큰의 근거) |

### 0.2 관리자 기능 설계 확인 (2026-11-04, worktree `claude/auth-admin`, `origin/main` `fbe5ecc`)

| # | 확인 명령 | 결과 | 판정 / 해결 |
| --- | --- | --- | --- |
| B-19 | `(cd src && uv run python -c "import main")` | `ok` | 차단 아님 |
| B-20 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 2건: `payments/application/service.py:19`, `:20` (application -> payments.infrastructure). 경고 3건(`[넓은예외]`) | **기준선**(auth 무관). 구현 후 위반이 이 2건에서 늘지 않아야 하고 auth 신규 위반 0 |
| B-21 | `uv run python -c "import dotenv, getpass"` | `ok`. 새 패키지 필요 없음. `pyproject.toml` 변경 없음 | 차단 아님 |
| B-22 | `check_layers.py:35` `ROOT_EXEMPT_FILES = {"main.py", "container.py"}`, `:162-163` | `src/` 루트의 다른 `.py`는 `common` 취급이라 다른 모듈의 application·presentation·infrastructure를 import하면 위반 | **관리자 생성 후보 (B) 스크립트를 `src/create_admin.py` 같은 루트 파일로 두면 `check_layers.py` 위반**이 된다. (B)를 채택하면 `.claude/**`의 `ROOT_EXEMPT_FILES` 수정이 필요(C-19, 오케스트레이터 소유). (A)는 `main.py` 안이라 해당 없음 |
| B-23 | 실험(inline `uv run python`, 파일 쓰기 없음): `GET /v1/admin/users/not-a-uuid`에 `AdminUser` 의존성, 토큰 없음 | `401 UNAUTHORIZED` | 인증·권한 의존성이 경로 UUID 검증보다 먼저 실행된다. 토큰 없이 잘못된 UUID는 400이 아니라 **401**. 테스트에서 이 순서를 고정(§7.5 T-A6) |
| B-24 | 환경 | 이번 작업에서 DB·`pytest` db 마커를 실행하지 않았다(지시). 기준선 skip 수·통과 수는 확인하지 않았다 | 구현 단계에서 오케스트레이터가 DB를 켜고 `skip 0`을 확인해야 함(R16) |
| B-25 | `Grep "/v1/admin" src`, `.env.example` | `/v1/admin` 경로를 쓰는 코드 없음. `.env.example`에 `ADMIN_*` 키 없음(`DATABASE_URL`, `JWT_*`, `ACCESS_TOKEN_EXPIRE_MINUTES`만) | 키 추가가 필요(C-18) |

차단 이슈 없음(B-22는 후보 (B) 선택 시에만 발생하는 조건부 이슈).

---

## 1. 결정 표

| ID | 내용 | 상태 | 출처 / 근거 |
| --- | --- | --- | --- |
| D-로그인형식 | 로그인은 JSON 본문 `{"email","password"}`. form 본문은 400 `VALIDATION_ERROR` | **확정** (사용자, 2026-11-02) | `docs/reference/auth.md` §2 |
| D-토큰추출 | `HTTPBearer(auto_error=False)`로 추출, 없거나 비면 `AuthenticationError`(401 `UNAUTHORIZED`) | **확정** | 현재 `dependencies.py` |
| D-에러형식 | `{success, error_code, message}`, 401은 `WWW-Authenticate: Bearer` | **확정** (명세) | `docs/reference/README.md`, R7 |
| D-포인트트랜잭션 | 포인트 메서드(`use/earn/restore/revoke_points`)는 `commit: bool = True` 키워드 인자를 받고, 다른 모듈은 `commit=False`로 호출자 트랜잭션에 참여 | **확정** (현 구현 유지) | R13 |
| D-서비스생성자 | `AuthApplicationService.__init__(session, users, point_logs, blacklist, hasher, tokens)` 전부 필수, 추상 타입만. 기본 생성 제거 | 정본 규칙 적용 | R8, `layer-architecture` §5.4 |
| D-레포구조 | 애그리거트가 3개(User, PointLog, BlacklistedToken)이므로 `domain/repository/` 패키지 3개 파일로 나눈다 | **확정** (사용자, 2026-11-03) | `layer-architecture` §5.1 (C-8 d) |
| D-구현체이름 | `SqlAlchemy<추상명>`, `BcryptPasswordHasher`, `JwtTokenProvider` | 정본 규칙 적용 | `layer-architecture` §5.3 |
| D-추상메서드명 | 추상 메서드 이름·시그니처는 **현재 구현과 동일하게 유지**(`add`, `exists`, `exists_by_email`, `count_by_user`, `delete_expired` 포함). `find_*/save/delete` 규칙과 다른 이름은 이번에 바꾸지 않음 | **임시** | 외부 동작·테스트 변경 최소화. 이름 정리는 별도 작업 |
| D-세션이름 | 서비스·레포 구현체의 `db` 속성·인자를 `session`으로 바꾼다 | **확정** (사용자, 2026-11-03) | `layer-architecture` §5.4 (C-8 b). 테스트는 `build()`가 첫 인자를 위치로 넘겨서 영향 없음 |
| D-해셔싱글턴 | `BcryptPasswordHasher`, `JwtTokenProvider`는 container의 모듈 전역 싱글턴. 더미 해시는 첫 `dummy_verify` 때 만든다(import 시점 bcrypt 비용 제거) | **확정** (사용자, 2026-11-03) | `layer-architecture` §6.2 (C-8 c) |
| D-fake API테스트 | `tests/auth/test_api_fake.py`(DB 없이 `provide_auth_service`를 fake로 바꾸는 API 테스트) | **미채택** (사용자, 2026-11-03). 구현하지 않음 | C-8 a |
| D-R2검사강화 | `check_layers.py`가 application→infrastructure import를 금지하도록 강화하는 것을 **이번 작업에 포함** | **확정** (사용자, 2026-11-03) | C-5. 단 `.claude/**`는 오케스트레이터 소유라 구현자 범위가 아님. 구현자의 완료 조건은 §10 7단계 참고 |
| D-R6후속 | R6 잔존분(`LookupError`·`PermissionError`를 그대로 raise) 정리는 이번 범위 **제외**, 후속 작업 | **확정** (사용자, 2026-11-03) | C-6 |
| D-작업소유권 | 이번 발주에서 `src/container.py` 최초 생성과 `tests/test_container.py`는 `layer-implementer`가 맡는다 | **확정** (사용자, 2026-11-03) | C-4. 이후 다른 모듈 구역 추가는 `orchestration.md` §4 표를 따름 |
| D-토큰설정지연 | `JwtTokenProvider()`는 설정을 지연 로딩(현재와 동일). 서버 시작 시 검증은 `main.py` lifespan의 `get_auth_settings()` 유지 | 확정(현 구현 유지) | `main.py:18` |
| D-타모듈주입 | 다른 모듈은 `AuthApplicationService`를 **생성자 인자로 주입**받는다. 자기 서비스 안에서 `AuthApplicationService(db)`를 만들지 않는다 | 정본 규칙 적용 | `layer-architecture` §3.4 3행, R11·R12 |
| D-인증의존성 | 다른 모듈의 router는 계속 `from auth.presentation.dependencies import CurrentUser, OwnerUser, ...` 별칭을 쓴다 | 확정(현 구현 유지) | `layer-implementation` §6 |
| D-wire위치 | `wire_dependencies(app)`은 `register_exception_handlers(app)` 다음, `include_router` 앞 | 정본 규칙 적용 | `layer-architecture` §6.3 |
| D-선택인증 | auth가 `get_optional_user`와 `OptionalUser = Annotated[User \| None, Depends(get_optional_user)]`를 `auth/presentation/dependencies.py`에서 공식 제공한다. 다른 모듈은 자체 선택 인증을 만들지 않고 이 별칭을 쓴다(D-인증의존성 확장). `provide_*` 추가 없음(기존 `provide_auth_service` 재사용, 매핑 변경 없음). 서비스 메서드·도메인 변경 없음(`authenticate` 재사용) | **확정** (사용자, 2026-11-04) | 중복 방지 요청. §7.3 |
| D-선택인증-무효토큰 | `Authorization: Bearer <토큰>`이 **있는데** 위조·만료·로그아웃(블랙리스트)·존재하지 않는 회원이면 `None`이 아니라 **401**(`CurrentUser`와 같은 예외·코드: `UNAUTHORIZED`/`TOKEN_REVOKED`, `WWW-Authenticate: Bearer`). `None`은 "인증 정보를 보내지 않음"일 때만 | **확정** (사용자, 2026-11-04, 질문 11) | 근거 3가지: (1) 현재 catalog 구현과 `tests/catalog/test_api_db.py:168-170`이 이미 이 동작을 고정(교체해도 테스트 불변). (2) 보안: 조용히 `None`으로 보면 만료·로그아웃·위조 토큰을 쓰는 클라이언트가 오류를 모른 채 비로그인으로 계속 동작해 "로그인했는데 내 정보가 안 보임" 같은 문제를 숨기고, 이후 로그인 여부로 분기하는 코드(예: 본인 예약 표시, 가격 혜택)가 토큰 상태에 따라 말없이 달라진다. 거절하면 토큰 문제가 즉시 드러나고 인증 실패 응답이 `CurrentUser`와 한 가지로 통일된다. (3) 명세: `docs/reference/README.md` 상태 코드 표 "401 = 토큰 없음, 만료, 로그아웃된 토큰, 로그인 실패", 인증 절 "로그인이 필요한 모든 API는 토큰 검증 후 블랙리스트 조회, 로그아웃 토큰이면 401 TOKEN_REVOKED". `docs/reference/catalog.md` #2·#4는 권한 "공개"이며 토큰이 잘못됐을 때의 규칙은 적혀 있지 않음(명세 공백, 질문 11) |
| D-선택인증-스킴 | `Authorization` 헤더 값이 **있고** 공백이 아닌데 Bearer 토큰으로 읽히지 않으면(`Basic ...`, `Token ...`, `Bearer`만 있고 토큰 없음) **401 `UNAUTHORIZED` "로그인이 필요합니다."**(`CurrentUser`의 토큰 없음과 같은 메시지). 헤더가 없거나 값이 비었으면 `None`. 스킴 이름은 대소문자 무시(`bearer tok` 허용, `HTTPBearer` 동작 그대로) | **확정** (사용자, 2026-11-04, 질문 12) | 근거: B-17. 현재 catalog는 이 경우 `None`(비로그인)이지만 필수 인증은 401(`tests/auth/test_api_db.py:106` `test_basic_scheme_is_unauthorized`). 같은 헤더가 필수 인증과 선택 인증에서 다르게 해석되면 안 됨. **catalog 현재 동작과 다른 유일한 지점**이다(기존 catalog 테스트 중 Basic 헤더를 쓰는 것은 없음, B-16 `Grep`). 이 동작 변경은 catalog 교체 시 함께 들어간다(§6.3) |
| D-선택인증-범위 | 이번 작업은 **auth 쪽만 구현**하고 catalog 교체는 "변경 제안"(C-13)으로만 적는다. 교체를 같은 PR에 포함할지는 사용자·catalog 담당자 결정 | **확정** (사용자, 2026-11-04, 질문 13): auth만 구현 | `catalog/**`는 catalog 담당자 소유(`orchestration.md` 쓰기 소유권). 교체 전에는 catalog의 자체 `OptionalUser`가 남아 중복이지만 동작은 변하지 않음 |
| D-상점주role | 상점주 role 값 `OWNER` | **임시** | 명세 "확인 필요", 건드리지 않음 |
| D-사업자번호 | 가입 시 `business_number` 미수집(컬럼은 NULL 허용으로 존재) | **임시** | 명세 "확인 필요", 건드리지 않음 |
| D-상점주승인 | 상점주 승인 대기 상태 미구현(`users`에 컬럼 없음) | **임시/미해결** | `db-schema` §5 항목 7, 건드리지 않음 |
| D-형식오류400 | 형식 오류는 400 `VALIDATION_ERROR`로 통일 | **임시** | 명세는 400, 건드리지 않음 |
| D-로그인제한 | 로그인 시도 횟수 제한 없음 | **임시/미해결** | 건드리지 않음 |
| D-블랙리스트정리 | **(2026-11-05 갱신, 복원)** 정리 기능 `purge_expired_tokens()`와 이를 호출하는 관리자 API `POST /v1/admin/token-blacklist/purge`가 **auth에 다시 있다**(admin.md D42와 일치, C-20. 같은 날 먼저 철회했다가 복원). 서버 시작 시 자동 정리 없음은 유지. 관리자 API `POST /v1/admin/token-blacklist/purge`(200, `{"deleted_count": n}`, `AdminUser`)로 `purge_expired_tokens()`를 호출한다. 서버 시작 시 자동 실행은 하지 않는다. 이전 값 "자동 정리 없음, 수동 호출용만"은 호출처가 없다는 점이 바뀐 것 | **확정** (사용자, 2026-11-04, 질문 18 = (A) 관리자 API, 서버 시작 시 자동 정리 없음) | §7.5.3 비교. 정리는 정확성이 아니라 저장 공간 문제(만료 토큰은 `decode`에서 이미 거부) |
| D-관리자생성 | **(2026-11-05 유지)** auth에 남는다. `docs/design/admin.md` B-7·D29의 "관리자 만들 방법 없음"은 이 결정으로 해소된다. ADMIN 계정은 서버 시작(lifespan) 시 `.env`의 `ADMIN_EMAIL`·`ADMIN_PASSWORD`로 **없으면 생성(멱등)**한다. 두 값이 모두 없으면 건너뜀, 하나만 있으면 시작 실패, 비밀번호가 예시값(`change-me` 접두사)이면 시작 실패. 도메인은 `User.register_admin`, 서비스는 `ensure_admin`. 회원가입으로 ADMIN 생성 불가(`Role.for_signup`)는 **그대로 확정 유지** | **확정** (사용자, 2026-11-04, 질문 14~16 = (A)) | §7.5.1 비교. 후보 (B) 관리 스크립트는 `check_layers.py` 루트 파일 제약(B-22) 때문에 `.claude/**` 수정이 필요해 탈락 |
| D-관리자조회 | **복원** (사용자, 2026-11-05): `docs/design/admin.md` D42("두 EP는 auth 라우터에 유지")와 일치하도록 auth 라우터에 다시 둠. 응답 `UserResponse`(태환 님 PR #25로 `status` 포함). (같은 날 먼저 철회했다가 복원함, C-20.) `GET /v1/admin/users/{user_id}` (`AdminUser`). 응답은 기존 `UserResponse` 재사용(id, email, name, phone, role, users_point, status, created_at). `password_hash`·`business_number` 제외. 없는 회원 404 `NOT_FOUND`, 비로그인 401, 관리자 아님 403, 잘못된 UUID 400 `VALIDATION_ERROR`. 서비스는 기존 `get_user` 재사용 | **확정** (사용자, 2026-11-04, 질문 17. 명세 반영은 C-16) | §7.5.2. R15: 명세 반영은 C-16 |
| D-포인트비공개 | **(2026-11-05 갱신 제안, 상태: 사용자 확정 요구조건 반영 — `docs/requirements/auth.md` B-4, REQ-52)** 공개 API 없음은 유지한다. 단 관리자 지급(REQ-52)은 **admin 모듈이 auth 서비스 메서드(`earn_points`류, 사유·관리자 기록은 REQ-53·55)로 수행하도록 허용**하고, 관리자 차감은 없다. 아래는 이전 결정 원문: `use/earn/restore/revoke_points`는 **공개 엔드포인트로 만들지 않는다.** 이유: 이 메서드들은 호출자를 신뢰하고 권한·멱등성 검사가 없다. 공개하면 로그인한 사용자가 자기 `earn_points`를 호출해 포인트를 늘릴 수 있다. 내부 호출(payments)만 허용. 관리자 수동 조정 API도 만들지 않는다 | **확정** (사용자, 2026-11-04, "포인트 연동 가이드만" 선택). 관리자 포인트 수동 조정 API(질문 19)는 이번 범위 아님 | 명세 포인트 정책: USE·EARN·RESTORE·REVOKE는 결제·환불 시점에 payments가 내부 처리(`docs/design/payments.md` 1.2). 공개 EP는 `GET /v1/users/me/points`(조회)뿐 |
| D-포인트연동 | payments는 `AuthApplicationService`를 **생성자 필수 인자**로 주입받고(D-타모듈주입, R8·R12) 포인트 메서드를 모두 `commit=False`로 호출, payments가 마지막에 한 번 `commit()`한다(D-포인트트랜잭션, R13). 상세 §6.1 **확정** (사용자, 2026-11-04). 기존 확정(D-타모듈주입, D-포인트트랜잭션)을 payments에 적용 | payments 파일 변경은 C-17 |

---

## 2. 변경 요약 (파일별) — 완료

아래 표는 리팩터링에서 바뀐 파일 목록이며, 모두 `a7e5c39`에 반영됐다(`git show --stat a7e5c39`: 16개 파일). 표에 없는 변경: `0554aed`가 `.claude/skills/auth-security-check/scripts/jwt_matrix.py`를 `BcryptPasswordHasher` 이름에 맞게 고쳤다(`PasswordHasher` import 깨짐 회귀 수정, 오케스트레이터 범위).

### 2.1 신규 (완료)
| 파일 | 내용 | 담당 |
| --- | --- | --- |
| `src/auth/domain/repository/__init__.py` | 빈 파일 | `layer-implementer` |
| `src/auth/domain/repository/user_repository.py` | `UserRepository(ABC)` | `layer-implementer` |
| `src/auth/domain/repository/point_log_repository.py` | `PointLogRepository(ABC)` | `layer-implementer` |
| `src/auth/domain/repository/token_blacklist_repository.py` | `TokenBlacklistRepository(ABC)` | `layer-implementer` |
| `src/auth/domain/service.py` | `PasswordHasher(ABC)`, `TokenProvider(ABC)` | `layer-implementer` |
| `src/container.py` | `create_*` 팩토리, 싱글턴, `wire_dependencies(app)` (최초 생성은 이번 발주의 `layer-implementer`, D-작업소유권) | `layer-implementer` |
| `tests/test_container.py` | 배선 점검 (§9) (D-작업소유권) | `layer-implementer` |

### 2.2 변경 (완료)
| 파일 | 변경 |
| --- | --- |
| `src/auth/infrastructure/repositories.py` | 클래스 이름을 `SqlAlchemyUserRepository`, `SqlAlchemyPointLogRepository`, `SqlAlchemyTokenBlacklistRepository`로 바꾸고 각 추상을 상속. 인자·속성 `db` -> `session`. 메서드 본문 불변 |
| `src/auth/infrastructure/security.py` | `PasswordHasher` -> `BcryptPasswordHasher(domain.service.PasswordHasher)`로 이름 변경, 더미 해시 지연 생성. `JwtTokenProvider`는 `TokenProvider` 상속 |
| `src/auth/application/service.py` | infrastructure import 전부 제거, 기본 구현체·`_default_hasher`·`_hasher` 삭제, 생성자 필수 인자화, `db` -> `session`, docstring 갱신 |
| `src/auth/presentation/dependencies.py` | `get_auth_service` 삭제, `provide_auth_service()` 플레이스홀더 추가, `get_current_principal`이 `Depends(provide_auth_service)` 사용, `database` import 제거 |
| `src/auth/presentation/router.py` | `Service = Annotated[AuthApplicationService, Depends(provide_auth_service)]` |
| `src/main.py` | `from container import wire_dependencies` 추가, `wire_dependencies(app)` 호출 (라우터 등록 전) |
| `tests/auth/test_security.py` | `PasswordHasher` import를 `BcryptPasswordHasher`로 |
| `tests/auth/test_service.py` | fake가 추상을 상속, 필수 인자 확인 테스트 추가 |
| `tests/auth/test_api_db.py` | 서비스 직접 생성 5곳을 헬퍼로, fixture 정리를 `pop(get_db)`로 (B-9) |

### 2.3 삭제
- `src/auth/presentation/dependencies.py`의 `get_auth_service`
- `src/auth/application/service.py`의 `_hasher`, `_default_hasher`, 기본 인자(`users or UserRepository(db)` 등)
- infrastructure의 `PasswordHasher` 이름(이름은 domain 추상이 가져감)

### 2.4 변경하지 않음
`domain/user.py`, `point_log.py`, `token_blacklist.py`, `token_claims.py`, `exceptions.py`, `infrastructure/models.py`, `settings.py`, `presentation/schemas.py`, `src/error_handlers.py`, `src/database.py`, DB 스키마. **스키마 변경 제안: 없음.**

### 2.5 구현자 범위 밖 (오케스트레이터 소유, D-R2검사강화) — 완료
`.claude/skills/layer-check/check_layers.py`의 `FORBIDDEN_LAYERS["application"]`에 `"infrastructure"`를 추가하는 일은 `.claude/**` 소유자(오케스트레이터)의 몫이었고 `0554aed`로 반영됐다: `check_layers.py:41` `"application": {"infrastructure", "presentation"},  # R2: ...`. (C-5)

### 2.6 구현 메모 (계획과 다르거나 계획에 없던 점)
| 항목 | 내용 | 근거 |
| --- | --- | --- |
| `_finish(commit)` 헬퍼 | 포인트 4개 메서드의 `if commit: commit()`을 `_finish`로 모았다. 동작은 §5.2와 같다 | `src/auth/application/service.py:130-132` |
| 서비스 import 서식 | `service.py:19`와 `:20` 사이, `:20`과 `:22` 사이에 빈 줄이 없다(`MAX_PAGE_SIZE = 100`이 import 바로 뒤). 동작에는 영향 없는 서식 문제 | `service.py:19-22` |
| `tests/conftest.py` | 계획에 없던 파일. `JWT_SECRET_KEY`, `DATABASE_URL` 기본값을 테스트에 설정(기존 파일, 이번 리팩터링으로 바뀌지 않음) | `tests/conftest.py:1-6` |
| `test_container.py (c)` | 계획은 fake를 넘기도록 했으나 구현은 `object()` 마커를 4개 인자에 그대로 넘겨 `session`/`hasher`/`tokens` 타입만 확인한다 | `tests/test_container.py:39-45` |
| `_pwd_context` | bcrypt `CryptContext`는 모듈 전역이다(구현체 인스턴스는 싱글턴, 컨텍스트는 import 시 생성). 더미 해시만 지연 생성이며 §4.2 설명과 같다 | `src/auth/infrastructure/security.py:12`, `:29-32` |

---

## 3. 도메인 (domain/)

**구현됨, 코드와 일치.** 엔티티·VO·규칙(생성자 검증, `User.register`, `Role.for_signup`, 포인트 메서드, `PointLog` 불변, `BlacklistedToken.is_expired`, `TokenClaims.to_blacklist_entry`)은 그대로다. 추가된 것은 추상 두 묶음뿐이다: `src/auth/domain/repository/{user,point_log,token_blacklist}_repository.py`, `src/auth/domain/service.py`. 아래 시그니처는 해당 파일과 한 줄씩 대조해 같음을 확인했다(`user_repository.py:7-19`, `point_log_repository.py:7-25`, `token_blacklist_repository.py:7-16`, `service.py:8-29`). 모두 순수 파이썬(`abc`, `uuid`, `datetime`)이며 R1을 지킨다(`check_layers.py` 위반 없음).

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
- 예외: 변경 없음(`AuthenticationError` 계열 401, `EmailDuplicatedError` 409; `domain/exceptions.py` 28줄). R6 잔존분은 후속 작업(D-R6후속, C-6).
- 코드값 확인(임시 항목, 상태만 유지): `Role.OWNER = "OWNER"`(`domain/user.py:8`, 주석에 "팀 확인 필요 (임시)"), `Role.for_signup`은 `ADMIN` 거부(`user.py:13`)와 `CUSTOMER`/`OWNER`만 허용(`:15`), `business_number`는 `User`에 있으나 `SignupRequest`에는 없음(`schemas.py:7-12`). 표와 같다.
- 상태 값(`Role`)은 전이가 없다. 포인트 `PointType` 4종(EARN, USE, RESTORE, REVOKE)은 `point_log`의 CHECK와 일치한다(`db-schema` §4).

---

## 4. 인프라 (infrastructure/)

**구현됨, 코드와 일치.** 테이블·컬럼·제약·FK는 `models.py` 그대로이며 `schema.sql`과 일치한다(대조 결과는 §14.1).

### 4.1 `repositories.py`
```python
class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession): self.session = session
    ...
class SqlAlchemyPointLogRepository(PointLogRepository): ...
class SqlAlchemyTokenBlacklistRepository(TokenBlacklistRepository): ...
```
- 생성자 인자 이름을 `db`에서 `session`으로 바꾼다(`self.db` -> `self.session`, 본문 치환만, D-세션이름). 컨테이너에서 위치 인자로 넘기므로 외부 영향 없음.
- `find_*`는 도메인 객체만 반환, `*Model`을 노출하지 않음(R4). `commit()`은 호출하지 않음(R5).
- 동시성: `find_by_id(for_update=True)` -> `SELECT ... FOR UPDATE`(포인트 변경 4개 메서드가 `_locked_user`로 사용). 유지. `token_blacklist.add`는 `ON CONFLICT DO NOTHING`으로 멱등. 가입 경쟁은 `users.email` UNIQUE + `IntegrityError -> EmailDuplicatedError`. 모두 현행 유지.

### 4.2 `security.py`
```python
class BcryptPasswordHasher(PasswordHasher):
    def __init__(self):
        self._dummy_hash: str | None = None   # 첫 dummy_verify 때 생성 (import 시점 비용 제거, D-해셔싱글턴)

    def hash(self, raw_password: str) -> str: ...
    def verify(self, raw_password: str, hashed_password: str) -> bool: ...   # ValueError/TypeError -> False
    def dummy_verify(self, raw_password: str) -> None: ...


class JwtTokenProvider(TokenProvider):
    def __init__(self, settings: AuthSettings | None = None): ...   # 설정 지연 로딩 유지
    def issue(...) -> tuple[str, TokenClaims]: ...
    def decode(self, token: str) -> TokenClaims: ...
```
- 본문 로직(알고리즘은 설정값 `settings.algorithm`, `require: exp, sub, jti, role`, 예외 매핑)은 불변. 인자 이름은 추상과 맞췄다(`raw_password`, `hashed_password`; `security.py:20-29`). 위치 인자 호출만 있어 영향 없음. **구현됨** (`security.py:15-84`). 알고리즘은 `settings.algorithm`으로 읽지만 `JWT_ALGORITHM`이 `HS256`이 아니면 시작 시 `RuntimeError`라 사실상 HS256 고정이다(`settings.py:29-31`).

---

## 5. 응용 (application/)

**구현됨, 코드와 일치** (`src/auth/application/service.py`). infrastructure·database import 없음(B-10).

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
- 모든 인자 필수. 기본값·`or` 기본 생성·모듈 전역 해셔 없음. 구현: `service.py:40-54`, docstring `:38`(C-7 해소). `AuthApplicationService(`를 만드는 곳은 `src/container.py:44`뿐이며 나머지는 테스트(`tests/auth/test_service.py:114`, `:226`, `tests/auth/test_api_db.py:37`)다.

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
| `purge_expired_tokens(now=None) -> int` | `blacklist.delete_expired` | 1회 (2026-11-04: 관리자 API가 호출, §7.5.3) |
| `ensure_admin(email, password, name=None) -> tuple[User, bool]` (신규 제안) | §7.5.1 | 생성 시 1회 |

- 공용 DTO `AuthenticatedPrincipal`, `PointLogPage`, `MAX_PAGE_SIZE`는 `service.py`에 그대로 둔다(`:20-34`).
- 메서드 줄: signup `:56`, login `:80`, authenticate `:90`, logout `:99`, get_user `:103`, list_point_logs `:109`, use/earn/restore/revoke `:134-169`, purge `:171`. 시나리오는 위 표와 같다.
- 트랜잭션 경계: 단독 유스케이스(signup, logout, purge)는 서비스가 commit. 포인트 4종은 D-포인트트랜잭션대로 `commit=False`로 호출자 트랜잭션에 참여한다. 요청 세션이 닫힐 때 미커밋분은 롤백된다(R13).

---

## 6. 다른 모듈이 auth를 쓰는 방법 (이전 메모와 달라진 점)

현재 auth를 쓰는 다른 모듈 코드는 아직 없다(B-8). 아래는 사용 규약이며, 이 규약과 어긋나는 `layer-implementation/SKILL.md` 예시는 C-1·C-2로 남아 있다.

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
- **로그인 선택 EP(제안, D-선택인증):** router는 `from auth.presentation.dependencies import OptionalUser`를 파라미터 타입으로 쓴다. 토큰 없음 -> `None`, 정상 토큰 -> `User`, 잘못된 토큰·비 Bearer 헤더 -> 401(D-선택인증-무효토큰·스킴). 서비스에는 `viewer.id if viewer else None`처럼 `user_id`만 넘긴다(catalog D23). 상세는 §7.3.

**관리자 기능과의 관계 (2026-11-05):** 확정 요구조건(`docs/requirements/auth.md`)의 REQ-20(폐기 토큰 정리는 관리자가 요청할 때만)과 REQ-52(관리자 포인트 지급, 차감 없음)는 auth 도메인 규칙으로 유지된다. 관리자 회원 조회(`GET /v1/admin/users/{user_id}`)와 토큰 정리(`POST /v1/admin/token-blacklist/purge`) API 2개는 admin.md D42와 일치하도록 auth 라우터에 둔다(2026-11-05 복원, C-20). 포인트 관련 관리자 API는 admin 모듈이 만들고, auth의 `AdminUser`·`get_user`·`purge_expired_tokens`·포인트 메서드를 같은 세션·`commit=False` 규약(R13)으로 호출한다. 요구조건 문서는 수정하지 않았다.

### 6.1 포인트 연동 가이드 — payments (2026-11-04, D-포인트비공개, D-포인트연동)

**엔드포인트는 만들지 않는다.** 포인트 4개 메서드(`service.py` `use_points`·`earn_points`·`restore_points`·`revoke_points`)는 호출자가 누구인지·같은 요청이 두 번 왔는지 검사하지 않는다. 공개하면 `earn_points`로 자기 포인트를 늘릴 수 있다. 사용자에게 열리는 것은 조회 `GET /v1/users/me/points`뿐이다. 호출은 결제·환불 서비스(payments)가 서버 로직 안에서만 한다.

**연결 방법 (R8·R11·R12·R13)**

```python
# src/payments/application/service.py (구현은 payments 담당, C-17)
from auth.application.service import AuthApplicationService   # 상대 application 서비스 타입 (R11 허용)

class PaymentApplicationService:
    def __init__(self, session, reservations, payments, refunds, gateway, policy,
                 auth: AuthApplicationService):                 # 필수 인자, 기본값 None 금지
        ...
```
```python
# src/container.py (payments 구역) — auth 구역의 create_auth_service를 그대로 Depends로 받는다
def create_payment_service(
    session: AsyncSession = Depends(get_db),
    ...,
    auth: AuthApplicationService = Depends(create_auth_service),
) -> PaymentApplicationService: ...
```
- 한 요청 안에서 `get_db`와 `create_auth_service`는 같은 세션을 쓴다(B-9). payments가 `AuthApplicationService(db)`를 만들지 않는다.
- 호출은 **항상 `commit=False`**. 기본값(`True`)으로 부르면 포인트만 먼저 커밋되어 결제 실패 시 되돌릴 수 없다. 테스트는 fake auth가 `commit` 인자를 기록해 모든 호출이 `False`이고 payments가 `commit()`을 한 번만 하는지 확인한다.
- payments가 `AuthApplicationService`를 만들려면 payments 설계의 생성자(`auth: ... | None = None  # 같은 세션`, `docs/design/payments.md:347`)를 위처럼 바꿔야 한다(C-17).

**흐름별 호출 (`docs/design/payments.md` 1.2 포인트 정책 표, 4.3.1·4.3.3 기준)**

| 흐름 | 시점(payments 단계) | auth 호출 | 금액(`amount` 인자는 항상 양수, 로그 부호는 auth가 정함) | auth 에러 -> HTTP |
| --- | --- | --- | --- | --- |
| 결제 요청 `pay` | 결제 INSERT 전, 게이트웨이 호출 전(4.3.1 단계 6) | `use_points(user_id, use_point, commit=False)` | 사용자가 정한 `use_point`(100P 단위, 잔액 이하). `0`이면 호출하지 않음 | 단위·잔액 위반 `ValueError` -> 400 `VALIDATION_ERROR` |
| 결제 승인 직후 | 결제 저장 후, 예약 `mark_paid` 전(단계 9) | `earn_points(user_id, earn, commit=False)` | `earn = 결제 금액 x 1%` 버림. 0이면 호출하지 않음 | 없는 회원 `UserNotFoundError` -> 404 |
| 환불 | `refunds.save`·`payments.save` 직후(4.3.3 `_apply_refund`) | `restore_points(user_id, used, commit=False)` | `used = total_price - payment.amount` > 0일 때 | 〃 |
| 환불 | 위 다음 | `revoke_points(user_id, earned, commit=False) -> int` | `earned = payment.earn_point_amount()` > 0일 때. **반환값이 실제 회수액**이며 잔액이 모자라면 `earned`보다 작다(0이면 로그 없음). payments는 반환값을 환불 응답에 쓰지 않는다 | 〃 |

**payments가 지킬 점**
1. **commit은 payments가 마지막에 한 번.** auth 호출 중 예외가 나면 커밋 전이므로 세션 종료 시 롤백된다. 게이트웨이 실패 처리로 `rollback()`한 뒤에는 사용 포인트도 함께 되돌아간다(`payments.md` 4.3.1 단계 7).
2. **멱등성은 payments 책임.** auth 메서드는 호출할 때마다 잔액과 `point_log`를 바꾼다. 같은 결제 환불 2번, 같은 결제 적립 2번을 막는 것은 payments의 중복 검사(`payments.md` C-2: `payments` 행 `with_for_update()` + `refunds.payment_id` UNIQUE)다.
3. **락 순서.** auth는 회원 행을 `FOR UPDATE`로 잠근다(`_locked_user`). payments의 고정 순서 "예약 -> 결제 -> (환불 INSERT) -> 회원(포인트)"(`payments.md` C-4)의 마지막이므로 auth를 부르는 시점이 그 순서를 어기지 않게 한다. 환불은 예약·결제 행을 잠근 뒤에 부르고, 결제 요청은 `payments.md`의 트랜잭션 표대로 "예약 -> (포인트 회원 행) -> 결제 INSERT" 순서다.
4. **계산은 payments.** 적립률 1%, `used`, `earned` 계산은 payments 도메인(`Payment`)이 한다. auth는 100P 단위 사용·음수 금지·잔액 한도만 검사한다(단위 규칙을 두 곳에 두지 않음, `payments.md` 4.1.2).
5. **사용자 객체 갱신.** `use_points`·`earn_points`는 갱신된 `User`를 돌려주지만 `CurrentUser`로 받은 객체는 갱신되지 않는다. 응답에 잔액이 필요하면 반환값을 쓴다(명세의 결제·환불 응답에는 포인트 잔액이 없음).
6. **호출자 신원.** `user_id`는 `CurrentUser`(JWT)에서 얻는다. 환불에서는 예약 스냅샷의 `user_id`(결제자)로 복구한다(관리자·상점주가 대신 환불해도 포인트는 결제자에게).
7. **현재 payments 상태(참고, 수정은 C-17):** `src/payments/presentation/dependencies.py:14-19`가 `X-User-Id`·`X-User-Role` 헤더로 인증을 흉내 내고(payments.md V-9), `src/payments/application/service.py:44`가 `TODO(D-10)`로 포인트를 구현하지 않으며(V-17), 서비스가 `db`·기본 구현체를 직접 쓴다(`:19-20` 기준선 위반 2건). 포인트 연동은 이 세 가지를 고친 뒤에 붙인다.

---

## 7. 표현 (presentation/)

엔드포인트·스키마·에러 코드는 **변경 없음**(R15). `router.py`·`schemas.py`를 `docs/reference/auth.md`와 대조한 결과는 §14.2. 현재 표(`router.py:25-77`):

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
- **구현됨**(`dependencies.py:13-24`, `router.py:22`). `from database`·`AsyncSession` import 없음(`dependencies.py:1-8`).
- `provide_*`는 이 모듈에서 **`provide_auth_service` 하나**다. 다른 모듈이 auth 레포 추상을 직접 주입받을 계획이 없으므로 `provide_user_repository` 등은 만들지 않는다(필요해지면 추가하고 `wire_dependencies`에도 같이 매핑).

### 7.2 `presentation/router.py`
`Service = Annotated[AuthApplicationService, Depends(provide_auth_service)]`로 교체, `get_auth_service` import 삭제. 나머지 동일.

### 7.3 로그인 선택 의존성 `OptionalUser` (신규 제안, D-선택인증 계열)

**시그니처와 위치:** `src/auth/presentation/dependencies.py`에 추가. 기존 `bearer_scheme`·`get_current_principal`·`get_current_user`·`require_roles`·별칭은 변경하지 않는다.

```python
from fastapi import Depends, Request

async def get_optional_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    service: Annotated[AuthApplicationService, Depends(provide_auth_service)],
) -> User | None:
    if credentials is not None and credentials.credentials:
        return (await service.authenticate(credentials.credentials)).user   # 무효 토큰은 401 (D-선택인증-무효토큰)
    raw = request.headers.get("authorization")
    if raw is None or not raw.strip():
        return None                                                          # 인증 정보 없음 = 비로그인
    raise AuthenticationError("로그인이 필요합니다.")                          # Bearer가 아닌 헤더 (D-선택인증-스킴)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
```

- `bearer_scheme`을 계속 `Depends`로 거는 이유: OpenAPI에 보안 스킴(Authorize 버튼)이 표시되고 토큰 추출 규칙(`HTTPBearer`)이 필수 인증과 같다. `Request`는 `HTTPBearer`가 구분 못 하는 "헤더 없음 vs Bearer 아님"(B-17)을 가르는 데만 쓴다.
- `AuthenticationError`는 이미 `get_current_principal`이 쓰는 `auth.domain.exceptions`의 예외다. `HTTPException`을 만들지 않는다(R6). 401 본문·`WWW-Authenticate: Bearer`는 전역 핸들러가 만든다(R7, D-에러형식). `TokenRevokedError`는 `authenticate()`가 낸다.
- `provide_auth_service` 재사용이므로 새 `provide_*`·`wire_dependencies` 변경·`container.py` 변경이 없다(R9). `tests/test_container.py`(a)의 `provide_` 수집 결과도 같다.
- `get_current_principal`과 중복되는 "토큰 추출 + `authenticate`" 두 줄은 합치지 않는다(필수 인증은 `AuthenticatedPrincipal`을, 선택 인증은 `User | None`을 돌려주며 처리 분기가 다르다). 로그아웃처럼 `claims`가 필요한 EP는 선택 인증이 아니므로 `OptionalPrincipal`은 만들지 않는다(필요해지면 그때 추가).
- R2: presentation이 `fastapi`·`auth.application`·`auth.domain`만 import한다. infrastructure·database import 없음.

**동작 표** (`Authorization` 헤더 -> `OptionalUser` 결과)

| 입력 | 결과 | 응답(해당 시) |
| --- | --- | --- |
| 헤더 없음 | `None` | - |
| 헤더가 있으나 값이 비었거나 공백 | `None` | - |
| `Bearer <유효 토큰>` (스킴 대소문자 무관) | `User` | - |
| `Bearer <위조·서명 불일치·형식 오류>` | 401 | `UNAUTHORIZED` "유효하지 않은 토큰입니다." |
| `Bearer <만료 토큰>` | 401 | `UNAUTHORIZED` "토큰이 만료되었습니다." |
| `Bearer <로그아웃된 토큰>` | 401 | `TOKEN_REVOKED` |
| `Bearer <유효 서명이지만 없는 회원>` | 401 | `UNAUTHORIZED` "유효하지 않은 토큰입니다." |
| `Basic ...`, `Token ...` 등 Bearer 아님 | 401 | `UNAUTHORIZED` "로그인이 필요합니다." |
| `Bearer`(토큰 없음), `Bearer `(공백만) | 401 | `UNAUTHORIZED` "로그인이 필요합니다." |

(401은 모두 `{"success": false, "error_code", "message"}`와 `WWW-Authenticate: Bearer`.)

**검토한 대안(채택하지 않음):** 무효 토큰을 모두 `None`으로 처리 -> 위 근거 (2)(3) 때문에 임시 기본값에서 제외. 바꾸려면 `get_optional_user`의 `authenticate` 호출을 `try/except AuthenticationError: return None`으로 감싸고 마지막 `raise`를 `return None`으로 바꾸는 한 곳 수정이며, 이 경우 `tests/catalog/test_api_db.py:168-170`(`Bearer bad.token` -> 401)과 아래 테스트 계획을 함께 바꿔야 한다.

### 7.4 테스트 계획 (D-선택인증)

DB 없이 도는 테스트를 먼저 둔다(현재 환경에서 DB 테스트가 skip되므로 R16 증거가 약해지지 않게). 새 파일 `tests/auth/test_optional_user.py`:

| # | 종류 | 케이스 | 기대 |
| --- | --- | --- | --- |
| T-1 | 단위/API(DB 없음) | 헤더 없음 | `None`, `service.authenticate` 호출 0회 |
| T-2 | 〃 | 빈/공백 헤더 값 | `None` |
| T-3 | 〃 | 유효 Bearer 토큰 | 해당 `User` 반환 |
| T-4 | 〃 | 위조(다른 비밀키 서명, 문자열 `forged`) | 401 `UNAUTHORIZED`, `WWW-Authenticate: Bearer` |
| T-5 | 〃 | 만료 토큰 | 401 `UNAUTHORIZED` "토큰이 만료되었습니다." |
| T-6 | 〃 | 로그아웃 후 같은 토큰 | 401 `TOKEN_REVOKED` |
| T-7 | 〃 | 서명은 유효하나 없는 회원 | 401 `UNAUTHORIZED` |
| T-8 | 〃 | `Basic <토큰>` | 401 `UNAUTHORIZED` "로그인이 필요합니다." |
| T-9 | 〃 | `Bearer`만(토큰 없음) | 401 `UNAUTHORIZED` |
| T-10 | 〃 | `bearer <유효 토큰>`(소문자 스킴) | `User` |

구성: 테스트 안에서 작은 `FastAPI()` 앱을 만들어 `register_exception_handlers(app)`를 호출하고 `GET /probe`(`viewer: OptionalUser` -> `{"user_id": str(viewer.id) if viewer else None}`)를 둔다. `app.dependency_overrides[provide_auth_service]`를 `tests/auth/test_service.py`의 `build()`와 같은 fake 레포·실제 `JwtTokenProvider(AuthSettings(...))`로 만든 `AuthApplicationService`로 바꾼다(`httpx.ASGITransport`, `main.app`을 건드리지 않으므로 다른 테스트에 영향 없음). `build()`가 다른 테스트 파일에 있으므로 import하지 말고 필요한 fake를 `tests/auth/` 안의 공용 헬퍼로 옮길지, 복사할지는 구현자가 정하되 `test_service.py`의 기존 테스트 이름·동작은 바꾸지 않는다. 이 앱은 D-fake API테스트(auth API 전체의 fake 기반 테스트 미채택)와 별개로 의존성 한 개만 검증한다.
- 실제 앱 통합(DB): 선택 인증을 쓰는 실제 EP는 catalog #2·#4다. 기존 `tests/catalog/test_api_db.py`가 이미 비로그인 200, 무효 토큰 401(`:168-170`), `is_active=false` 401·소유자 200을 확인한다. catalog 교체(C-13) 후에도 **이 파일은 수정 없이 통과해야 한다**(완료 조건).
- 추가 제안(catalog 교체를 같이 할 때만, catalog 담당자 소유): `Authorization: Basic ...`으로 `GET /v1/products/{id}` -> 401, 로그아웃한 토큰 -> 401 `TOKEN_REVOKED` 각 1건.
- 기존 `tests/auth/**`, `tests/test_container.py`는 변경하지 않는다.

**구현자 완료 게이트(코드 변경이 있으므로 `backend-invariants` §7):** `check_layers.py` 위반이 기준선 2건(B-13)을 넘지 않고 auth 쪽 신규 위반 0, `import main` 성공, `uv run pytest -rs` failed 0·**db 마커 skip 0**(오케스트레이터가 DB를 켜고 확인). 정독 규칙(R3, R5, R7~R15)은 `layer-checker`가 판정한다.

### 7.5 관리자 기능 (2026-11-04, D-관리자생성·D-관리자조회·D-블랙리스트정리, 모두 **임시**)

#### 7.5.1 ADMIN 계정 생성

**비교**

| 항목 | (A) 서버 시작 lifespan에서 `.env` 값으로 생성 | (B) 관리 명령 스크립트 (`uv run python ...`) |
| --- | --- | --- |
| 계층 위치 | 호출은 `main.py`(조립 지점, `check_layers` 제외). 로직은 도메인 `User.register_admin` + 서비스 `ensure_admin` | 스크립트가 서비스·DB를 모두 알아야 한다. `src/` 루트 파일은 import 제한 대상(B-22)이라 `ROOT_EXEMPT_FILES` 수정(`.claude/**`, C-19) 없이는 위반. 모듈 안(`presentation`)에 두면 `container`/infrastructure를 조립할 수 없음 |
| 시크릿 | `ADMIN_PASSWORD`가 서버가 도는 동안 환경에 남는다(`JWT_SECRET_KEY`도 같은 수준). 예시값 거부로 완화 | 비밀번호를 프롬프트로 받으면 저장되지 않음. 그러나 CI·자동화에서는 결국 환경변수 |
| 커밋 금지(R16) | `.env`는 gitignore. `.env.example`에는 **주석 처리한 예시값만**(C-18). 예시값(`change-me` 접두사, `get_auth_settings`와 같은 방식)이면 시작 실패 | 같음 |
| 멱등 | `ensure_admin`이 이미 있으면 아무것도 안 함 | 같은 서비스 메서드 재사용 |
| 운영 편의 | 개발·테스트 환경에서 `.env`만 채우면 끝. 비밀번호 변경은 반영되지 않음 | 실행을 잊으면 관리자가 없음. 비밀번호 재설정 명령을 같이 만들 수 있음 |
| 테스트 | 서비스 단위 테스트(DB 없음)가 핵심. lifespan 자체는 `ASGITransport` 테스트에서 실행되지 않으므로 `seed_admin()`을 함수로 빼서 호출 | 서비스 테스트 같음. 스크립트 진입점은 얇아 따로 테스트할 것이 적음 |
| 위험 | 설정 오류가 시작 실패로 드러남(좋은 점). 매 시작마다 조회 1회 | 별도 진입점이 하나 늘어남 |

**임시 기본값: (A).** 이유: 계층 검사를 건드리지 않고(B-22), 새 의존성·진입점이 없으며, 기존 `get_auth_settings()` 시작 시 검증(`main.py` lifespan)과 같은 방식이다. (B)를 택하면 C-19의 `.claude/**` 수정이 선행돼야 한다. 사용자가 "비밀번호를 서버 환경에 남기지 않기"를 더 중시하면 (B)로 바꾼다(서비스 `ensure_admin`은 그대로 재사용).

**도메인 (`domain/user.py`, R3)**
| 항목 | 내용 |
| --- | --- |
| `User.register_admin(email, password_hash, name=None) -> User` | 신규 `classmethod`. `role=Role.ADMIN`, `users_point=0`, `created_at=now(UTC)`, 이메일·이름 검증은 `__init__`이 한다(재사용). `Role.for_signup`은 **바꾸지 않는다**(`register(role="ADMIN")`은 계속 `ValueError`) |
| 비밀번호 | 서비스가 `User.validate_raw_password`(8자 이상, 72바이트 이하)로 검증한 뒤 해싱(회원가입과 같은 규칙) |
| 판정 | 기존 사용자가 관리자인지는 `has_role(Role.ADMIN)` |

**설정 (`infrastructure/settings.py`)**
```python
@dataclass(frozen=True)
class AdminSeedSettings:
    email: str
    password: str

def get_admin_seed_settings(env: Mapping[str, str] | None = None) -> AdminSeedSettings | None: ...
```
- `env=None`이면 `load_dotenv()` 후 `os.environ`을 읽는다. 테스트는 `env` 딕셔너리를 넘겨 개발자의 `.env`에 영향받지 않는다.
- `ADMIN_EMAIL`·`ADMIN_PASSWORD` 둘 다 없거나 빈 문자열 -> `None`(건너뜀). 하나만 있음 -> `RuntimeError`. `ADMIN_PASSWORD`가 `PLACEHOLDER_PREFIX`(`change-me`)로 시작 -> `RuntimeError`. 오류 메시지에 비밀번호 값을 넣지 않는다(R16). 비밀번호 강도는 서비스(도메인 규칙)가 검증한다.
- 캐시(`lru_cache`)는 쓰지 않는다(시작 때 한 번만 호출).

**서비스 (`application/service.py`)** — 신규 메서드 1개
| 메서드 | 시나리오 | commit |
| --- | --- | --- |
| `ensure_admin(email, password, name=None) -> tuple[User, bool]` | `User.validate_raw_password(password)` -> `users.find_by_email(User.normalize_email(email))` -> **있으면**: 관리자면 `(user, False)` 반환(해싱·쓰기 없음), 관리자가 아니면 `EmailDuplicatedError`(계정을 승격하지 않음) -> **없으면**: `hasher.hash` -> `User.register_admin` -> `users.save`. 경쟁으로 `EmailDuplicatedError`가 나면 `rollback` 후 다시 조회해 관리자면 `(user, False)`, 아니면 재raise -> 성공 시 `(user, True)` | 생성 시 1회, 이미 있으면 없음 |

**조립 (`src/container.py`, auth 구역)**
```python
def build_auth_service(session: AsyncSession) -> AuthApplicationService:
    """Depends 없이 서비스를 만든다(lifespan 등 요청 밖). create_auth_service와 같은 구현체를 쓴다."""
    return create_auth_service(
        session,
        SqlAlchemyUserRepository(session),
        SqlAlchemyPointLogRepository(session),
        SqlAlchemyTokenBlacklistRepository(session),
    )
```
- `wire_dependencies` 매핑 변경 없음(`provide_*` 추가 없음, R9).

**`src/main.py`** (조립 지점, 오케스트레이터 승인 필요, C-19)
```python
async def seed_admin(session_factory=AsyncSessionLocal) -> bool:
    """ADMIN_EMAIL/ADMIN_PASSWORD가 설정돼 있으면 관리자를 보장한다. 새로 만들었으면 True."""
    settings = get_admin_seed_settings()
    if settings is None:
        return False
    async with session_factory() as session:
        _, created = await build_auth_service(session).ensure_admin(settings.email, settings.password)
    return created
# lifespan: create_all 다음 줄에서 await seed_admin()
```
- `lifespan`은 `get_auth_settings()` 다음, `create_all` 뒤에서 호출한다(테이블이 있어야 함). 로그에는 이메일만 남기고 비밀번호는 남기지 않는다.
- 실패(`RuntimeError`, `ValueError`, `EmailDuplicatedError`)는 그대로 올라가 **서버 시작이 중단**된다(설정 오류를 숨기지 않음, 질문 15).

**남은 선택 (질문 16):** 이미 있는 관리자의 비밀번호는 `.env`를 바꿔도 갱신하지 않는다(멱등, 임시 기본값). 비밀번호 재설정이 필요하면 별도 설계.

#### 7.5.2 관리자 회원 조회 `GET /v1/admin/users/{user_id}` (D-관리자조회) — **복원됨(2026-11-05)**

> 복원: admin.md D42와 일치하도록 auth 라우터에 다시 둔다(C-20). 구현 대상이다. 응답은 `UserResponse`이며 PR #25로 `status`가 포함된다.

| 항목 | 내용 |
| --- | --- |
| 권한 | `AdminUser`(`dependencies.py`에 이미 있음). 비로그인 401, ADMIN 아님 403(`RoleForbiddenError`, 메시지 `접근 권한이 없습니다.`, 질문 8 변경 없음) |
| 요청 | 경로 `user_id: uuid.UUID`. 잘못된 UUID는 400 `VALIDATION_ERROR`. 단 **토큰이 없으면 401이 먼저**(B-23) |
| 응답 | 200 `UserResponse` 재사용. 필드는 `id, email, name, phone, role, users_point, status, created_at`(`status`는 PR #25). **`password_hash`·`business_number`는 응답 스키마에 없다**(R15). `business_number`가 관리자에게 필요하면 별도 `AdminUserResponse`를 후속 결정 |
| 404 | 서비스 `get_user`가 `UserNotFoundError` -> 전역 핸들러 404 `NOT_FOUND`(메시지 "회원을 찾을 수 없습니다.") |
| 서비스 | 기존 `get_user(user_id)` 재사용. 읽기 전용이라 `commit()` 없음. 새 메서드 없음 |
| 감사 | 조회 로그·감사 기록은 만들지 않는다(명세에 없음) |

`UserResponse`를 재사용하는 이유: 새 스키마 없이 민감 정보 제외가 이미 보장돼 있고(`schemas.py:20-29`), `GET /v1/users/me`와 필드가 같아 클라이언트가 같은 모델을 쓴다. 관리자용 추가 필드가 생기면 그때 분리한다.

#### 7.5.3 블랙리스트 만료 토큰 정리 — **복원됨(2026-11-05)**

> 복원: 관리자 API가 auth 라우터에 다시 있다(admin.md D42, C-20). 아래 라우터·스키마(`PurgeTokensResponse`)가 구현 대상이다. 서버 시작 시 자동 정리 없음은 유지.

**비교**

| 항목 | (A) 관리자 API `POST /v1/admin/token-blacklist/purge` | (B) 서버 시작 시 자동 실행 | (C) 둘 다 |
| --- | --- | --- | --- |
| 정리 시점 | 관리자가 호출할 때(자동화하려면 외부 cron이 관리자 토큰으로 호출해야 해 번거로움) | 재시작 때만. 장기 가동 서버는 정리되지 않음 | 둘의 합 |
| 운영 위험 | 호출을 잊으면 행이 쌓임(행당 `jti`+만료시각, 로그아웃 1건당 1행으로 작음). 정확성 영향 없음 | 시작 경로에 DB 삭제가 하나 늘어 시작 실패 지점이 늘고, 다중 워커가 동시에 지울 수 있음(삭제는 멱등이라 안전) | 코드·테스트 두 배 |
| 가시성 | 삭제 개수를 응답으로 확인 | 로그를 봐야 함 | |
| 테스트 | DB 없는 API 테스트(fake)로 200·401·403 확인 가능, DB 테스트로 만료/비만료 행 확인 | lifespan은 `ASGITransport` 테스트에서 실행되지 않아 함수로 빼야만 검증 가능 | |
| 변경 범위 | 라우터·스키마만. `main.py`·`container.py` 변경 없음 | `main.py` 변경 | 둘 다 |

**임시 기본값: (A).** 이유: 만료된 jti는 `decode` 단계에서 이미 거부되므로(토큰 만료 30분, `ACCESS_TOKEN_EXPIRE_MINUTES`) 정리는 저장 공간 문제일 뿐이다. (A)는 시작 경로를 건드리지 않고 라우터·스키마만 추가하며 테스트가 가장 쉽다. 자동화가 필요해지면 (C)로 확장한다(서비스 메서드는 그대로 재사용, 질문 18).

| 항목 | 내용 |
| --- | --- |
| 엔드포인트 | `POST /v1/admin/token-blacklist/purge`, 요청 본문 없음, `AdminUser`, 200 `PurgeTokensResponse{deleted_count: int}`, 에러 401·403 |
| 서비스 | 기존 `purge_expired_tokens(now=None)` 재사용(1회 `commit`). 라우터는 `now`를 넘기지 않는다(현재 시각 사용, 테스트는 서비스에 `now`를 직접 전달) |
| 응답 필드 이름 | `deleted_count`(질문 17에서 함께 확인, 명세에 없음) |

**스키마 (`presentation/schemas.py`)**
```python
class PurgeTokensResponse(BaseModel):
    deleted_count: int = Field(..., description="삭제된 만료 토큰 수")
```

**라우터 (`presentation/router.py`, 같은 `router` 사용 -> `main.py` 변경 없음)**
```python
@router.get("/admin/users/{user_id}", response_model=UserResponse, tags=["관리자"], summary="회원 조회(관리자)")
async def admin_read_user(user_id: uuid.UUID, admin: AdminUser, service: Service):
    return await service.get_user(user_id)

@router.post("/admin/token-blacklist/purge", response_model=PurgeTokensResponse, tags=["관리자"],
             summary="만료된 블랙리스트 토큰 정리")
async def admin_purge_tokens(admin: AdminUser, service: Service):
    return PurgeTokensResponse(deleted_count=await service.purge_expired_tokens())
```
- `AdminUser`를 `from auth.presentation.dependencies import ...`에 추가. `uuid` import 추가.

#### 7.5.4 엔드포인트 표 (추가분) — **복원됨(2026-11-05)**

> 아래 2개 엔드포인트는 auth 라우터에 다시 둔다(admin.md D42, C-20).

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| GET | `/v1/admin/users/{user_id}` | Bearer(ADMIN), 경로 UUID | `UserResponse` | 200 | 400(UUID 형식), 401, 403, 404 |
| POST | `/v1/admin/token-blacklist/purge` | Bearer(ADMIN), 본문 없음 | `PurgeTokensResponse` | 200 | 401, 403 |

auth에는 위 관리자 EP 2개가 있다(2026-11-05 복원). 관리자 생성은 EP 없이 서버 시작 시 처리한다. 포인트 4종은 EP가 없다(D-포인트비공개, §6.1).

#### 7.5.5 변경 파일 목록 (구현자용, **확정본** 2026-11-04, 사용자 결정 반영. C-19 허용)

| 파일 | 변경 | 소유 |
| --- | --- | --- |
| `src/auth/domain/user.py` | `User.register_admin` 추가(`Role.for_signup`·`register` 불변) | auth 구현자 |
| `src/auth/infrastructure/settings.py` | `AdminSeedSettings`, `get_admin_seed_settings(env=None)` 추가(`get_auth_settings` 불변) | auth 구현자 |
| `src/auth/application/service.py` | `ensure_admin` 추가. 나머지 메서드 불변 | auth 구현자 |
| `src/auth/presentation/schemas.py` | `PurgeTokensResponse` 추가 | auth 구현자 |
| `src/auth/presentation/router.py` | 엔드포인트 2개 추가 | auth 구현자 |
| `src/container.py` | auth 구역에 `build_auth_service` 추가. 매핑 변경 없음 | auth 구현자(자기 구역) |
| `src/main.py` | `seed_admin()` 함수와 lifespan 호출, import(`AsyncSessionLocal`, `build_auth_service`, `get_admin_seed_settings`). 자기 모듈 두 줄 범위를 넘지만 **사용자가 허용**함(C-19, 발주서에 명시) | auth 구현자 |
| `tests/auth/test_domain.py`, `test_service.py`, `test_api_db.py`, 신규 `test_admin_seed_settings.py`, `test_admin_api.py`, `tests/test_container.py`(auth 부분) | §7.5.6 | auth 구현자 |
| `.env.example`, `README.md`, `docs/reference/auth.md`, `docs/reference/README.md` | C-16, C-18 | 오케스트레이터(구현자 범위 밖) |
| `src/payments/**`, `docs/design/payments.md` | C-17 | payments 담당(이번 범위 밖) |

신규 의존성 없음(B-21), 스키마 변경 없음(`users`·`token_blacklist`는 그대로, R14).

#### 7.5.6 테스트 계획

DB 없이 도는 테스트를 먼저 둔다(DB 테스트는 skip될 수 있어 R16 증거가 약해지지 않게).

| # | 파일 | 종류 | 케이스 | 기대 |
| --- | --- | --- | --- | --- |
| T-D1 | `test_domain.py` | 단위 | `register_admin` 정상 | role `ADMIN`, 포인트 0, `created_at`에 tz, 이메일 정규화 |
| T-D2 | 〃 | 〃 | `User.register(..., role="ADMIN")` / `Role.for_signup("ADMIN")` | 여전히 `ValueError`(회귀) |
| T-S1 | `test_service.py` | 서비스(fake) | `ensure_admin` 신규 | `(user, True)`, role ADMIN, `hash` 1회, `commits == 1` |
| T-S2 | 〃 | 〃 | 같은 이메일 관리자가 이미 있음 | `(user, False)`, `hash_calls == 0`, `commits == 0` |
| T-S3 | 〃 | 〃 | 같은 이메일이 CUSTOMER | `EmailDuplicatedError`, 역할 CUSTOMER 유지(승격 없음) |
| T-S4 | 〃 | 〃 | 약한 비밀번호(8자 미만, 공백) | `ValueError`, DB 조회 전에 거부 |
| T-S5 | 〃 | 〃 | 경쟁(저장 시 `EmailDuplicatedError`) 후 상대가 관리자 | `(user, False)`, `rollback` 1회. fake `FakeUsers`에 "저장 후 다른 행이 보이는" 동작을 추가(기존 테스트 이름·동작 불변) |
| T-S6 | 〃 | 〃 | `purge_expired_tokens` | 기존 `test_purge` 그대로(변경 없음) |
| T-C1 | `test_admin_seed_settings.py` | 단위 | `env`에 둘 다 없음/빈 값 | `None` |
| T-C2 | 〃 | 〃 | 둘 다 정상 | `AdminSeedSettings` |
| T-C3 | 〃 | 〃 | 하나만 있음 | `RuntimeError`, 메시지에 비밀번호 값 없음 |
| T-C4 | 〃 | 〃 | `ADMIN_PASSWORD=change-me-...` | `RuntimeError` |
| T-A1 | `test_admin_api.py` | API(DB 없음) | 작은 `FastAPI()` 앱에 auth `router`를 포함, `provide_auth_service`를 fake 기반 서비스로 override(§7.4 구성과 같음). 관리자 토큰으로 `GET /v1/admin/users/{id}` | 200, 응답 키가 `id,email,name,phone,role,users_point,created_at`뿐(`password_hash`·`business_number` 없음) |
| T-A2 | 〃 | 〃 | CUSTOMER·OWNER 토큰 | 403 `FORBIDDEN` |
| T-A3 | 〃 | 〃 | 토큰 없음 / 로그아웃 토큰 | 401 `UNAUTHORIZED` / `TOKEN_REVOKED`, `WWW-Authenticate: Bearer` |
| T-A4 | 〃 | 〃 | 없는 회원 UUID | 404 `NOT_FOUND` |
| T-A5 | 〃 | 〃 | 관리자 + 잘못된 UUID | 400 `VALIDATION_ERROR` |
| T-A6 | 〃 | 〃 | **토큰 없음 + 잘못된 UUID** | 401(B-23, 인증이 먼저) |
| T-A7 | 〃 | 〃 | `POST /v1/admin/token-blacklist/purge` 관리자 / CUSTOMER / 토큰 없음 | 200 `{"deleted_count": n}`, fake blacklist의 `delete_expired` 1회 / 403 / 401 |
| T-K1 | `tests/test_container.py` | 단위 | `build_auth_service(marker)` | `AuthApplicationService`, `hasher`·`tokens`가 추상 인스턴스. 기존 3건 불변, `provide_` 매핑 수 변화 없음 |
| T-B1 | `test_api_db.py` | DB | `seed_admin(client.session_factory)`(환경에 `ADMIN_*` 설정) -> 로그인 -> `GET /v1/admin/users/{고객 id}` | 로그인 200, 조회 200, `users_point`가 DB 값과 같음 |
| T-B2 | 〃 | DB | `seed_admin` 2회 | 두 번째는 `False`, `users` 행 1개 |
| T-B3 | 〃 | DB | 같은 이메일이 가입된 CUSTOMER인 채 `seed_admin` | `EmailDuplicatedError`, 역할 그대로 |
| T-B4 | 〃 | DB | 만료 행·비만료 행을 `SqlAlchemyTokenBlacklistRepository.add`로 넣고 purge API(관리자) | `deleted_count == 1`, 비만료 `jti`는 `exists` True, 만료는 False. 기존 `test_purge_expired_tokens`(서비스 직접 호출)는 그대로 |
| T-B5 | 〃 | DB | 회원가입 `role="ADMIN"` | 여전히 400(기존 `test_signup_errors`가 확인하는 범위, 회귀) |

- 테스트는 `main.seed_admin`을 `session_factory` 인자로 호출한다. 실제 `AsyncSessionLocal`(`DATABASE_URL`)을 쓰는 lifespan 자체는 테스트하지 않는다(테스트 DB와 다른 DB를 건드릴 수 있음). `test_api_db.py`의 `ADMIN_*`는 `monkeypatch.setenv`로 넣고 `get_admin_seed_settings`가 `.env`를 읽지 않도록 한다(`env` 인자 사용).
- fake 재사용: `test_optional_user.py`의 fake 클래스를 복사할지 `tests/auth/` 공용 헬퍼로 옮길지는 구현자가 정하되 기존 테스트 이름·동작은 바꾸지 않는다.
- 완료 게이트: `backend-invariants` §7. `check_layers.py` 위반이 기준선 2건(B-20)을 넘지 않고 auth 신규 위반 0, `import main` 성공, `uv run pytest -rs`에서 failed 0·db 마커 skip 0(오케스트레이터가 DB를 켜고 확인).

#### 7.5.7 R1~R16 영향 (설계 판정, 공식 판정은 `layer-checker`)

R1: `register_admin`은 표준 라이브러리만. R2: router는 service·schemas·dependencies만, `main.py`·`container.py`는 조립 지점. R3: 역할 판단은 `has_role`(도메인), 서비스는 흐름만(단 "이미 있으면" 분기는 서비스, 기존 `signup`과 같은 수준). R5: `commit()`은 `ensure_admin`·`purge_expired_tokens` 서비스만. R6: `UserNotFoundError`·`EmailDuplicatedError` 사용, `HTTPException` 없음. R7: 새 EP 에러는 전역 핸들러. R8·R9: `build_auth_service`는 container에만, 서비스 기본 구현체 없음. R15: 새 EP는 명세 밖이라 C-16으로 명세 반영 필요, 응답에 민감 정보 없음. R16: `.env`·시크릿 하드코딩 없음, 예시값 거부, 새 의존성 없음.

---

## 8. 조립 (`src/container.py`) 와 `main.py`

**구현됨, §8.2 코드와 `src/container.py:1-59`가 일치**한다(대조 확인). `main.py`는 `:10` import, `:27` `register_exception_handlers(app)`, `:28` `wire_dependencies(app)`, `:29` `include_router(auth_router)`로 D-wire위치 순서를 지킨다. `auth_models` import(`main.py:7`)와 lifespan의 `get_auth_settings()`(`:18`)도 유지된다.

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

**구현 완료.** 기준선 `84 passed` -> 현재 `89 passed`, `-rs` skip 0(B-4). 아래 표의 "변경" 칸은 계획이며, 실제 반영 확인 결과를 "구현 상태" 줄로 덧붙인다.

- 구현 상태: `test_security.py:8`이 `BcryptPasswordHasher` import, `:18-21` 더미 해시 테스트. `test_service.py:41`·`:57`·`:80`·`:96`의 Fake가 각각 `PasswordHasher`, `UserRepository`, `PointLogRepository`, `TokenBlacklistRepository`를 상속, `:224-226` 필수 인자 `TypeError` 테스트. `test_api_db.py:36-44` `auth_service(db)` 헬퍼, `:94` `pop(get_db, None)`. `test_container.py` 3건(`:25`, `:34`, `:39`). 계획과의 차이는 §2.6의 `test_container (c)` 한 건뿐이다.
- 기준선(계획 시점) 표:

| 파일 | 영향 | 변경 |
| --- | --- | --- |
| `tests/auth/test_domain.py` | 없음 | 없음 |
| `tests/test_error_handlers.py` | 없음 | 없음 |
| `tests/auth/test_security.py` | `PasswordHasher` import가 깨짐 | `BcryptPasswordHasher`로 교체. 더미 지연 생성 확인 테스트 1건 추가(`dummy_verify`가 예외 없이 동작·`None` 반환만 확인, `_dummy_hash` 같은 구현 세부는 단언하지 않음) |
| `tests/auth/test_service.py` | 생성자 인자 이름이 같아 그대로 통과. 그러나 R10을 강제하려고 fake가 **추상을 상속**하도록 바꾼다 | `FakeUsers(UserRepository)`, `FakeLogs(PointLogRepository)`, `FakeBlacklist(TokenBlacklistRepository)`, `FakeHasher(PasswordHasher)`. 추상 메서드를 하나라도 빠뜨리면 인스턴스 생성에서 `TypeError`가 나서 서비스가 추상 밖 메서드를 부르는 변경을 잡는다. `tokens`는 `JwtTokenProvider(AuthSettings(...))` 그대로 사용 가능. 추가: `AuthApplicationService(FakeSession())`(필수 인자 누락)이 `TypeError`인지 확인(R8 기본 구현체 금지 회귀 방지) |
| `tests/auth/test_api_db.py` | (1) fixture 정리 `app.dependency_overrides.clear()`(77행)가 배선을 지움(B-9) (2) `AuthApplicationService(db)` **5곳**(239, 323, 328, 337, 347행)이 인자 부족으로 실패 | (1) `app.dependency_overrides.pop(get_db, None)`으로 교체 (2) 파일 안에 헬퍼 `auth_service(db)`를 둔다: `AuthApplicationService(db, SqlAlchemyUserRepository(db), SqlAlchemyPointLogRepository(db), SqlAlchemyTokenBlacklistRepository(db), BcryptPasswordHasher(), JwtTokenProvider())`. 테스트가 `container`의 비공개 싱글턴(`_password_hasher`)을 import하지 않게 한다. HTTP 경로 테스트는 `main.app`의 실제 배선을 그대로 통과하므로 수정 불필요 |
| `tests/test_container.py` (신규, `layer-implementer` 담당, D-작업소유권) | R9 실행 검증 | (a) `dependencies` 모듈에서 이름이 `provide_`로 시작하는 함수를 모아(지금은 `auth.presentation.dependencies`; 새 모듈이 생기면 목록에 추가) `wire_dependencies(FastAPI())`의 `dependency_overrides` 키에 모두 있는지 확인 (b) `provide_auth_service()`를 직접 호출하면 `NotImplementedError` (c) `create_auth_service(session, users, point_logs, blacklist)`에 fake를 넘기면 `AuthApplicationService`가 만들어지고 `hasher`가 `PasswordHasher`, `tokens`가 `TokenProvider` 인스턴스 |

방침 요약: 서비스 테스트는 fake 주입, API 테스트는 `dependency_overrides[get_db]`만 건드리고 **`clear()`하지 않는다**. `provide_auth_service` fake 주입 API 테스트(`test_api_fake.py`)는 미채택(D-fake API테스트)이다.

---

## 10. 구현 순서 (`layer-implementer`용) — 완료

1~7단계 모두 `a7e5c39`(+ 검사 강화 `0554aed`)에서 수행됐다. 아래는 기록용으로 남긴다. 7단계 게이트의 현재 재실행 결과: `check_layers.py` 위반 0건, `import main` 성공, `pytest -rs` 89 passed, `grep infrastructure|database src/auth/application src/auth/presentation` 0건, `AuthApplicationService(`는 `container.py`에서만 생성(§5.1).

1. domain: `domain/repository/` 패키지 3개 파일 + `domain/service.py`. 이 시점에 `python3 .claude/skills/layer-check/check_layers.py` 통과 확인.
2. infrastructure: `repositories.py` 클래스 이름 변경 + 추상 상속 + `db` -> `session`, `security.py`(`BcryptPasswordHasher` 지연 더미, `JwtTokenProvider(TokenProvider)`).
3. application: `service.py` 생성자 필수화, infrastructure import 제거, `db` -> `session`.
4. presentation: `dependencies.py`(`provide_auth_service`), `router.py`.
5. `src/container.py` 작성(최초 생성), `src/main.py`에 `wire_dependencies(app)` 추가.
6. 테스트 수정·추가(§9, `tests/test_container.py` 포함). 3~5단계가 끝나기 전에는 테스트가 import에서 깨지므로 1~5를 한 번에 진행한다.
7. 완료 게이트(`backend-invariants` §7):
   ```bash
   python3 .claude/skills/layer-check/check_layers.py
   (cd src && uv run python -c "import main")
   uv run pytest -rs
   ```
   - **추가 완료 조건 (D-R2검사강화):** `check_layers.py`는 `.claude/**`라 구현자가 고치지 않는다. 오케스트레이터가 `FORBIDDEN_LAYERS["application"]`에 `"infrastructure"`를 추가한 판(또는 동일 효과의 검사)으로 돌렸을 때 auth가 `[의존방향]` 위반 0건이어야 한다. 구현자는 같은 효과를 `grep -rn "infrastructure" src/auth/application src/auth/presentation`이 0건인지로 자가 확인한다.
   - 자가 점검(판정은 `layer-checker`): `grep -rn "AuthApplicationService(" src`가 `container.py` 외에는 0건이어야 한다.

---

## 11. R1~R16 해소 / 잔여 현황

### 11.1 현재 판정 (2026-11-03, HEAD `671d457`)

판정 방법: 자동 규칙은 `python3 .claude/skills/layer-check/check_layers.py` 결과(위반 없음, 경고 3건 `[넓은예외]`), 실행 규칙은 `import main`·`pytest -rs`(89 passed, skip 0), 정독 규칙은 설계자가 코드를 읽은 **참고 판정**이다. 정독 규칙의 공식 판정은 `layer-checker`가 한다(AGENTS.md "만든 사람과 확인하는 사람을 나눈다").

| 규칙 | 현재 판정 | 근거 |
| --- | --- | --- |
| R1 | 충족 | 자동: `[외부의존]`·`[의존방향]` 위반 0 |
| R2 | 충족 | 자동: application->infrastructure 금지 판(`check_layers.py:41`)에서 위반 0. `grep infrastructure\|database src/auth/application src/auth/presentation` 0건 |
| R3 | **잔존(경미)** | `service.py:112-115` page/size 범위 검증, `:166` `if actual > 0`, `:82-86` 로그인 분기가 서비스에 있음. 검증 규칙 자체(비밀번호, role, 포인트 단위·잔액)는 도메인(`user.py`)에 있음 |
| R4 | 충족 | 자동 `[레포반환]`·`[반환타입]` 위반 0. 레포는 `_to_domain`으로 도메인 객체만 반환(`repositories.py:70-82`, `:133-141`) |
| R5 | 충족(정독) | `commit()`은 `service.py:77`, `:101`, `:132`, `:173`뿐. 레포는 `flush()`까지(`repositories.py:54`, `:67`, `:98`, `:155`) |
| R6 | **잔존** | `service.py:106`·`:127` `LookupError`, `repositories.py:62` `LookupError`, `user.py:111` `PermissionError`를 그대로 raise. 자동 `[HTTP예외]` 위반은 0(`HTTPException` 없음). D-R6후속, C-6 |
| R7 | 충족 | 핸들러 `error_handlers.py:25-60`이 `{success,error_code,message}` 형식, 401은 `WWW-Authenticate: Bearer`(`:27`). `tests/test_error_handlers.py`·`test_api_db.py` 통과 |
| R8 | 충족 | 서비스 생성자는 추상만 필수 인자(`service.py:40-54`), 기본 구현체 없음. 테스트 `test_service.py:224-226` |
| R9 | 충족 | `container.py:54-59` 매핑, `provide_auth_service`(`dependencies.py:13`) 1개가 모두 매핑됨. `tests/test_container.py:25-31`이 검증 |
| R10 | 충족 | 서비스가 쓰는 레포·해셔·토큰 메서드는 모두 추상에 선언(§3). Fake가 추상 상속(`test_service.py:41`, `:57`, `:80`, `:96`) |
| R11 | 충족 | auth는 다른 모듈을 import하지 않음. 다른 모듈에서 auth를 쓰는 코드는 아직 없음(B-8) |
| R12 | 충족 | `import main` 성공. 서비스 생성자 안에서 다른 서비스를 만들지 않음(`container.py:38-51`만 생성) |
| R13 | 충족 | 포인트 4개 메서드 `commit: bool = True`(`service.py:134`, `:142`, `:150`, `:160`), 같은 요청 세션은 B-9에서 확인 |
| R14 | 충족 | §14.1 대조: 3개 테이블 컬럼·타입·NULL·CHECK·FK·인덱스 일치, UUID는 `uuid.UUID`, 시간은 `DateTime(timezone=True)` |
| R15 | 충족 | §14.2 대조. 응답 스키마에 `password_hash` 없음(`schemas.py:20-29`) |
| R16 | 충족 | `.env` 커밋 없음(`git status`에 `.env` 없음, `JWT_SECRET_KEY`는 `.env.example`에 예시값만), pytest skip 0. 신규 의존성 없음 |

R1~R16 중 **잔존 위반은 R3(경미)와 R6** 두 가지다. 둘 다 이전부터 알려진 항목이며 이번 범위 밖이다(D-R6후속).

### 11.2 계획 시점 기록 (이력)

범례: 해소 = 이 설계로 충족, 유지 = 이미 충족하며 변경 없음, **잔존** = 위반이 남음(범위 밖이라 건드리지 않음). 아래 "이 설계 후" 열은 계획이며, 실제 결과는 11.1이 정본이다.

| 규칙 | 현재 | 이 설계 후 | 비고 |
| --- | --- | --- | --- |
| R1 domain 순수 | 유지 | 유지 | 새 추상은 `abc`/`uuid`/`datetime`만 |
| R2 의존 방향 | **위반**: `application/service.py`가 `auth.infrastructure`를 import(`check_layers.py`가 application->infrastructure를 금지 목록에 두지 않아 자동 검사는 통과) | **해소** | `presentation/dependencies.py`의 `database` import도 제거. 검사 강화는 D-R2검사강화(오케스트레이터) |
| R3 도메인 규칙 위치 | 대체로 유지 | **잔존(경미)** | 서비스의 `list_point_logs` 범위 검증(page/size), `revoke_points`의 `if actual > 0`, 로그인 분기는 서비스에 있음. 가입 검증은 도메인 정적 메서드를 호출해 규칙 자체는 도메인에 있음. `User.create(..., hasher)`로 옮기는 안은 `layer-architecture` §3.2에 있으나 이번 범위가 아니므로 미적용(후속 후보) |
| R4 레포 반환 | 유지 | 유지 | |
| R5 commit 위치 | 유지 | 유지 | 레포는 flush까지 |
| R6 예외 | **잔존**: `service.py`의 `LookupError("회원을 찾을 수 없습니다.")`, `repositories.py`의 `LookupError`, `User.require_role`의 `PermissionError`를 그대로 raise | **잔존 (후속 작업으로 확정, D-R6후속)** | `UserNotFoundError(LookupError)`, `RoleForbiddenError(PermissionError)` 도입은 응답 코드가 같아 안전하지만 이번 범위 밖 |
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

참고: `[넓은예외]` 경고 3건(`error_handlers.py`)은 범위 밖이다. R6 잔존분 후속 작업 뒤 핸들러를 줄일 수 있다.

---

## 12. 정합 이슈 (C-번호)

설계안 작성자는 아래 파일을 고치지 않는다. 오케스트레이터가 사용자 승인 후 처리한다.

### 12.1 현재 상태 요약 (2026-11-03, HEAD `671d457`, 실제 파일로 확인)

| ID | 상태 | 근거 |
| --- | --- | --- |
| C-1 | **미해결** | `.claude/skills/layer-implementation/SKILL.md:231` `self.offers = offers or DiscountOfferRepository(db)`, `:269` `self.auth = AuthApplicationService(db)  # 같은 세션`, `:226-232` `__init__(self, db, *, offers=None)`. `:10`의 "이전 방식" 안내문만 있고 예시는 그대로. `provide_*`·`container`는 `:10`에만 언급 |
| C-2 | **미해결** | `SKILL.md:333-337` `get_catalog_service(db=Depends(get_db))`가 router 모듈에서 서비스 직접 생성. `AGENTS.md:35` "정답 예시 코드 ... (DI·조립은 제외)" 그대로 |
| C-3 | **부분 해결** | 테스트 코드는 해결: `tests/auth/test_api_db.py:94` `pop(get_db, None)`(`a7e5c39`). 문서는 미해결: `.claude/skills/layer-implementation/testing.md:186` `app.dependency_overrides.clear()`, `:190` "`dependency_overrides`도 fixture에서 비웁니다". `docs/design/stores.md` B-10은 "auth C-3 해소"로 적었으나 `testing.md`는 아직 `clear()`다(stores 쪽 표현 정정 필요, §12.3 C-10) |
| C-4 | **해결** | `docs/operations/orchestration.md:21`(`layer-implementer`는 `src/container.py`의 자기 모듈 구역), `:71`(container 소유권 행)에 반영. 이번 발주에서 `src/container.py`·`tests/test_container.py`는 구현자가 작성(`a7e5c39`) |
| C-5 | **해결** | `0554aed`: `.claude/skills/layer-check/check_layers.py:41` `"application": {"infrastructure", "presentation"}`. 같은 커밋이 `layer-check/SKILL.md` 1줄도 수정. 실행 결과 위반 0 |
| C-6 | **미해결(후속 확정)** | R6 잔존 위치: `service.py:106`, `:127`, `repositories.py:62`, `user.py:111`. D-R6후속 |
| C-7 | **해결** | `service.py:38` docstring이 §5.1 문구로 교체됨 |
| C-8 | **해결(결정 반영)** | (a) `test_api_fake.py` 없음(미채택), (b) `session` 이름 `service.py:42`, `repositories.py:20`, (c) 지연 더미 `security.py:18`, `:30-31`, (d) `domain/repository/` 패키지 3파일 |
| C-9 | 신규 | §12.3 |
| C-10 | 신규 | §12.3 |
| C-11 | 신규 | §12.3 |
| C-12 | 신규 | §12.3 |

### 12.2 계획 시점 원문 (이력)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-1 | `.claude/skills/layer-implementation/SKILL.md` §4 "여러 모듈이 얽힌 흐름", §4 서비스 예시, 상단 안내 | `self.auth = AuthApplicationService(db)`, `offers or DiscountOfferRepository(db)`가 R8·R12와 충돌. 상단 안내문이 "이전 방식"이라고만 하고 코드는 그대로 남아 있음 | 예시를 §6과 같은 생성자 주입 + `provide_*`/container 방식으로 교체. 오케스트레이터 처리 |
| C-2 | `.claude/skills/layer-implementation/SKILL.md` §6 `get_catalog_service(db=Depends(get_db))`, `AGENTS.md` 문서 맵 "정답 예시 코드 ... (DI·조립은 제외)" | 서비스를 router 모듈에서 직접 생성하는 예시. auth 리팩터링 후에는 DI·조립도 auth가 정답 예시가 됨 | 예시를 `Depends(provide_catalog_service)`로 교체하고, AuthApplicationService 사용 안내를 §6 표로 갱신. AGENTS.md의 "(DI·조립은 제외)" 삭제(리팩터링 완료 후). 오케스트레이터 처리 |
| C-3 | `.claude/skills/layer-implementation/testing.md` 130~190행 (`client` fixture의 `app.dependency_overrides.clear()`, "dependency_overrides도 fixture에서 비웁니다") | `wire_dependencies(app)`이 `main` import 시점에 넣은 매핑을 `clear()`가 지워 이후 테스트가 `NotImplementedError`로 실패(B-9에서 재현) | `clear()` 대신 `pop(get_db, None)` 또는 "건드린 키만 원복"으로 수정. 오케스트레이터 처리 |
| C-4 | `docs/operations/orchestration.md` §4 소유권 표 | `src/container.py` 최초 생성과 루트 `tests/test_container.py`의 소유자 불명확 | **결정됨 (D-작업소유권):** 이번 발주에서는 `layer-implementer`가 `src/container.py` 생성과 `tests/test_container.py`를 맡는다. 소유권 표에 한 줄 추가할지는 오케스트레이터 판단 |
| C-5 | `.claude/skills/layer-check/check_layers.py` `FORBIDDEN_LAYERS["application"]` | `application -> infrastructure`를 금지하지 않아 R2를 자동 검사하지 못함 | **결정됨 (D-R2검사강화):** 이번 작업에 포함. `"application": {"presentation", "infrastructure"}`로 강화. `.claude/**`는 오케스트레이터 소유이므로 구현자 범위 밖. 설계안은 §10 7단계의 완료 조건(auth가 강화된 검사를 통과)만 규정 |
| C-6 | `src/auth/domain/user.py`(`PermissionError`), `src/auth/application/service.py`·`infrastructure/repositories.py`(`LookupError`) | R6 잔존 | **결정됨 (D-R6후속):** 이번 범위 제외, 후속 작업. 예: `domain/exceptions.py`에 `UserNotFoundError(LookupError)`, `RoleForbiddenError(PermissionError)` 추가(응답 코드 동일, 기존 `pytest.raises(LookupError)`도 통과) |
| C-7 | `src/auth/application/service.py` 클래스 docstring | "payments 등 다른 모듈은 같은 세션으로 이 서비스를 만들어..." 문구가 새 구조와 반대 | §5.1의 docstring으로 교체(구현 시 반영) |
| C-8 | 이 설계가 요청 범위를 넘어 추가한 부분 | (a) `tests/auth/test_api_fake.py` (b) `db` -> `session` (c) 더미 해시 지연 생성 (d) `domain/repository/` 패키지 | **결정됨 (사용자, 2026-11-03):** (a) 미채택, (b)(c)(d) 확정. 결정 표 D-fake API테스트, D-세션이름, D-해셔싱글턴, D-레포구조 참고 |

### 12.3 새로 발견한 정합 이슈 (2026-11-03)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-9 | `src/auth/application/service.py:19-22` | import 블록과 `MAX_PAGE_SIZE = 100`, `@dataclass` 사이에 빈 줄이 없다(서식, 동작 무관). R 위반 아님 | 구현자가 후속 정리 때 빈 줄 추가. 코드 변경이라 이번 작업에서는 고치지 않음 |
| C-10 | `docs/design/stores.md` B-10 (미커밋 초안, 이번 작업에서 수정 금지) | "auth C-3 해소"라고 적혀 있으나 코드(`test_api_db.py:94`)만 해소됐고 `.claude/skills/layer-implementation/testing.md:186`·`:190`은 아직 `clear()` 지시(C-3 부분 해결) | stores 설계 갱신 시 "코드 해소, testing.md 미해결"로 정정. 오케스트레이터가 testing.md 수정 시 함께 해소 |
| C-11 | `src/auth/domain/user.py:111` | `require_role`의 `PermissionError("접근 권한이 없습니다.")`가 모든 역할 실패(`OwnerUser` 등)에 같은 메시지를 낸다. `docs/design/stores.md` C-S1은 stores 명세 403 메시지 "상점주 권한이 필요합니다."와 다르다고 지적(R15). stores는 `OwnerUser`를 그대로 쓰기로 함(D-인증의존성과 일치) | 후속 C-6 정리(`RoleForbiddenError`)에서 역할별 메시지를 낼지 사용자 결정 필요. 현재 auth 동작은 바꾸지 않음. 질문 8로 추가 |
| C-12 | stores가 auth에 기대하는 점 | `docs/design/stores.md` S-2(a)는 상점주 승인 상태를 `users.approved_at`(auth 소유)로 두는 안을 제시한다. 이 경우 auth 스키마·`models.py`·`schema.sql`·`db-schema` 변경(R14)과 D-상점주승인 해소가 필요. stores Q-5(가입 시 `name`(상호) 필수화)도 auth 가입 규칙 변경이 된다. 두 안 모두 현재 auth 설계와 충돌하지 않으며(stores는 auth를 import하지 않고 원시값만 받음, `stores.md` §3) auth는 바뀌지 않았다 | 사용자가 stores Q-6, Q-5에서 결정할 때 auth 변경 여부를 함께 정한다. 질문 9·10으로 추가 |

### 12.4 `OptionalUser` 관련 (2026-11-04)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-13 | catalog 교체 계획 (catalog 담당자 소유, 설계자·이번 auth 구현자는 수정하지 않음) | catalog가 auth 내부(`bearer_scheme`, `provide_auth_service`)로 자체 `get_optional_user`/`OptionalUser`를 만들어 쓴다(B-16). auth가 공식 `OptionalUser`를 제공하면 중복이다 | **결정됨(사용자, 2026-11-04): 이번 범위 아님, catalog 담당자에게 변경 제안.** 아래 변경 목록 참고 |
| C-14 | `docs/design/catalog.md` §7.1(`:504-516`), 파일 구조 `:60`, 의존 그림 `:629`, D56·CI-3 | catalog 설계가 "auth 파일은 수정하지 않는다, `OptionalUser`는 catalog 파일에 둔다"로 쓰여 있어 교체 시 문장이 낡음. catalog.md는 이번에 수정 금지 | 교체 확정 시 catalog 설계 갱신 때 §7.1을 "auth `OptionalUser` 사용"으로 고치고 D-번호를 추가. 이 문서 D-선택인증이 정본 |
| C-15 | `docs/reference/catalog.md` #2·#4 (권한 "공개") | 공개 EP에 잘못된 토큰이 오면 401인지 200(비로그인)인지 명세에 없음. #10(할인 상세)은 토큰을 읽지 않아(catalog D56) 같은 "공개" EP인데 잘못된 토큰도 200이다 | 질문 11에 포함. 현재 구현은 #2·#4만 401, #10은 200으로 EP마다 다름. 통일 여부는 사용자 결정(이번 범위 밖, 변경 없음) |

**C-13 catalog 교체 변경 목록 (제안)**

| # | 파일 | 변경 |
| --- | --- | --- |
| 1 | `src/catalog/presentation/dependencies.py` | `get_optional_user`·`OptionalUser`(`:37-46`) 삭제. 이 때문에 안 쓰게 되는 import(`Annotated`, `Depends`, `HTTPAuthorizationCredentials`, `AuthApplicationService`, `User`, `bearer_scheme`, `provide_auth_service`)도 삭제. `provide_*` 4개와 포트 import는 유지 |
| 2 | `src/catalog/presentation/router.py:10` | `from catalog.presentation.dependencies import OptionalUser, provide_catalog_service` -> `OptionalUser`는 `from auth.presentation.dependencies import OptionalUser`로, `provide_catalog_service`만 catalog에서 import. 사용처 `:54`, `:100`은 그대로 |
| 3 | `docs/design/catalog.md` | C-14 |
| 4 | `tests/catalog/**` | 기존 테스트 수정 불필요: `OptionalUser`를 직접 import하는 테스트 없음(B-16), `test_wiring.py`는 `provide_`로 시작하는 함수만 수집하므로 영향 없음(`get_optional_user`는 해당 안 됨). 요구 사항: `tests/catalog/test_api_db.py:168-170`(무효 토큰 401)과 `is_active=false` 시나리오(`:146-157`)가 그대로 통과 |
| 5 | 동작 변화 | 단 하나: `Authorization: Basic ...`·`Bearer`(토큰 없음) 헤더가 catalog #2·#4에서 `None`(200) -> 401로 바뀜(D-선택인증-스킴). 질문 12에서 `None` 유지로 정하면 `get_optional_user`의 마지막 `raise`를 `return None`으로 바꿔 catalog 동작을 완전히 보존할 수 있음 |

교체 후 확인: `python3 .claude/skills/layer-check/check_layers.py`(기준선 2건 초과 없음), `import main`, `uv run pytest -rs`(DB 켜고 skip 0), `Grep "bearer_scheme\|provide_auth_service" src/catalog` 0건.

### 12.5 관리자 기능 관련 (2026-11-04)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-16 | `docs/reference/auth.md`, `docs/reference/README.md` (오케스트레이터 소유, 설계자 수정 금지) | 명세에 관리자 EP 2개(`GET /v1/admin/users/{user_id}`, `POST /v1/admin/token-blacklist/purge`)가 없다. README 역할 표의 `ADMIN` 행은 "회원가입으로는 만들 수 없음"만 있고 생성 방법이 없다(R15) | 사용자 확정 후 EP 2개(요청·응답·에러 표)와 "ADMIN은 서버 시작 시 `ADMIN_EMAIL`/`ADMIN_PASSWORD`로 생성"을 명세에 추가. 확정 전까지 구현은 §7.5를 따르되 R15 차이로 보고 |
| C-17 | payments (`src/payments/**`, `docs/design/payments.md`, payments 담당) | (1) 헤더 인증 `presentation/dependencies.py:14-19`(V-9)를 auth `CurrentUser`로 교체 (2) `service.py:44` `TODO(D-10)` 포인트 미구현(V-17) (3) `payments.md:347`의 `auth: AuthApplicationService \| None = None  # 같은 세션`은 D-타모듈주입·R8·R12와 어긋남 -> 필수 인자로 주입, container `create_payment_service`가 `create_auth_service`를 `Depends`로 연결 (4) `service.py:19-20` application -> infrastructure 위반 2건(기준선, B-20) | 이번 범위 아님. §6.1을 payments 설계 갱신 때 참조. 이 설계는 payments 파일을 수정하지 않았다 |
| C-18 | `.env.example`, `README.md`(오케스트레이터 소유) | `ADMIN_EMAIL`·`ADMIN_PASSWORD` 키 추가. **주석 처리한 예시값만**(`# ADMIN_EMAIL=admin@example.com`, `# ADMIN_PASSWORD=change-me-to-a-strong-password`), 실제 비밀번호 금지(R16). README 로컬 실행에 "관리자가 필요하면 `.env`에 두 값을 채우고 서버를 시작" 한 줄 | 사용자 확정 후 |
| C-19 | `src/main.py`·`src/container.py`(오케스트레이터가 범위 확정), `.claude/skills/layer-check/check_layers.py` | (A) 채택 시 `main.py`에 `seed_admin()`·lifespan 호출·import 추가, `container.py`에 `build_auth_service` 추가가 필요하다. `layer-implementer`의 기본 범위(`main.py` 자기 모듈 두 줄)를 넘으므로 **발주서에 명시**해야 한다. (B) 채택 시에는 `ROOT_EXEMPT_FILES`(`check_layers.py:35`)에 스크립트 파일 추가가 필요(B-22) | **결정됨: 허용** (사용자, 2026-11-04, 질문 14 = (A)). 구현자는 `src/main.py`(`seed_admin`, lifespan 호출, import)와 `src/container.py` **auth 구역**(`build_auth_service` 추가)만 수정할 수 있다. 다른 모듈 구역·`check_layers.py`는 금지 |

### 12.6 관리자 API 복원 (2026-11-05)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-20 | admin 모듈 담당자(박태환 님), `docs/design/admin.md` | **전달:** auth가 제공하는 것은 관리자 계정 생성(서버 시작 시 `ADMIN_EMAIL`·`ADMIN_PASSWORD`, `ensure_admin`), `AdminUser` 의존성, `get_user`, `purge_expired_tokens`, 포인트 메서드다. API 2개 `GET /v1/admin/users/{user_id}`(회원 조회, `UserResponse` 재사용, `status` 포함)와 `POST /v1/admin/token-blacklist/purge`(응답 `{"deleted_count": n}`)는 **auth에 복원**한다(admin.md D42와 일치). admin은 그대로 사용한다(`src/admin/presentation/router.py:24`, `tests/admin/test_api_db.py:119-128`이 auth에 있다고 전제). 같은 날 먼저 철회했으나 admin에 대체 API가 없어 복원했다. C-16의 명세 반영 대상에 이 EP 2개가 다시 포함된다 | **결정됨(사용자, 2026-11-05):** auth에 복원, admin은 그대로 사용(철회는 번복) |

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
| 6 | 블랙리스트 만료 행 정리 방식 | `db-schema` §2 "만료가 지난 행은 지워도 됨" | 수동 호출(`purge_expired_tokens`)만 -> **2026-11-04 갱신 제안: 질문 18** | 현 구현 | 스케줄러·lifespan 도입 시 결정 |
| 7 | 추상 메서드 이름 정리(`add/exists/count_by_user/delete_expired` vs `find_*/save/delete`) | `layer-architecture` §5.1 | 현재 이름 유지 | D-추상메서드명, 변경 범위 최소화 | `domain/repository/*.py`와 구현체·fake 동시 변경 필요 |
| 8 | (신규, C-11) 역할 불일치 403 메시지를 역할별로 낼지 | `docs/design/stores.md` C-S1, `docs/reference/stores.md` | 현재 `접근 권한이 없습니다.` 유지(미변경) | 현재 코드값 `user.py:111` | `User.require_role`, C-6 정리와 함께 |
| 9 | (신규, C-12) 상점주 승인 상태를 `users`에 둘지 stores 소유 테이블에 둘지 (질문 3과 같은 주제) | `docs/design/stores.md` S-2, Q-6 | 미구현 유지(auth 변경 없음) | D-상점주승인 | 스키마 변경 시 R14: `models.py`, `schema.sql`, `db-schema/SKILL.md` 동시 |
| 10 | (신규, C-12) 가입 시 상점주 `name`(상호) 필수화 여부 | `docs/design/stores.md` Q-5 | 미변경(`name` 선택, `schemas.py:10`) | 명세 `name` 선택 | `SignupRequest`, `User.register` |
| 11 | (신규, D-선택인증-무효토큰) 로그인 선택 EP에 위조·만료·로그아웃·없는 회원 토큰이 오면 401로 거절할지 `None`(비로그인)으로 볼지. 명세에 공개 EP의 무효 토큰 규칙이 없음(C-15) | `docs/reference/README.md` 401 정의, `docs/reference/catalog.md` #2·#4 "공개" **결정됨(사용자, 2026-11-04): 401 거절**(현재 catalog 동작 유지, `CurrentUser`와 같은 error_code) | 현재 구현·`tests/catalog/test_api_db.py:168-170`, 보안(조용한 비로그인 처리 금지), 명세 401 정의 | `get_optional_user` 한 함수(§7.3 "검토한 대안") |
| 12 | (신규, D-선택인증-스킴) `Basic ...` 등 Bearer가 아닌 헤더와 토큰 없는 `Bearer`를 401로 볼지 `None`으로 볼지 | B-17 | **결정됨(사용자, 2026-11-04): 401 `UNAUTHORIZED` "로그인이 필요합니다."**(catalog 현재 `None`과 다름) | 필수 인증과 같은 입력이 같은 결과여야 함(`test_basic_scheme_is_unauthorized`) | `get_optional_user`의 마지막 `raise` 한 줄 |
| 13 | (신규, D-선택인증-범위, C-13) 이번에 auth의 `OptionalUser`만 구현할지, catalog 교체까지 함께 할지 | 사용자 요청 | **결정됨(사용자, 2026-11-04): auth만 구현**, catalog 교체는 변경 제안(C-13)으로 두고 catalog 담당자 승인 후 진행 | `catalog/**` 소유권 | C-13 변경 목록 |
| 14 | (신규 2026-11-04, D-관리자생성) ADMIN 계정 생성 방법: (A) 서버 시작 시 `.env`로 생성 / (B) 관리 스크립트. 환경변수 이름 | 사용자 요청, B-22 | **(A)** `ADMIN_EMAIL`·`ADMIN_PASSWORD`, 둘 다 없으면 건너뜀. **결정됨(사용자, 2026-11-04): (A)** | (B)는 `check_layers.py` 루트 파일 제약 때문에 `.claude/**` 수정 선행. 기존 `JWT_SECRET_KEY` 시작 시 검증·예시값 거부와 같은 방식 | `main.py` `seed_admin`, `settings.py` `get_admin_seed_settings` |
| 15 | (신규, D-관리자생성) `ADMIN_EMAIL`과 같은 이메일의 **비관리자 계정**이 이미 있을 때 | 사용자 요청 | 서버 시작 실패(`EmailDuplicatedError`), 계정 승격 안 함. **결정됨(사용자, 2026-11-04)** | 권한 상승을 시작 설정만으로 만들지 않음. 회원가입 ADMIN 금지 취지와 일치 | `ensure_admin` |
| 16 | (신규, D-관리자생성) 이미 있는 관리자의 비밀번호를 `.env` 변경으로 갱신할지, 설정 오류·예시값일 때 시작을 막을지 | 사용자 요청 | 갱신하지 않음(멱등), 예시값·한쪽만 설정이면 시작 실패. **결정됨(사용자, 2026-11-04)** | R16, `get_auth_settings`와 같은 fail-fast | `get_admin_seed_settings` |
| 17 | (신규, D-관리자조회, C-16) 관리자 회원 조회 EP 경로·응답, 정리 API 응답 필드 | 명세에 없음 | `GET /v1/admin/users/{user_id}` -> `UserResponse`(`business_number` 제외), 정리 응답 `{"deleted_count": n}`. **결정됨(사용자, 2026-11-04): 임시값대로** | 기존 `UserResponse` 재사용, 민감 정보 제외(R15) | `router.py`, `schemas.py` |
| 18 | (신규, D-블랙리스트정리, 질문 6 갱신) 만료 토큰 정리 방식: (A) 관리자 API / (B) 시작 시 자동 / (C) 둘 다. 이전 값(수동 호출만)을 대체 | `db-schema` §2 | **(A)** `POST /v1/admin/token-blacklist/purge`. **결정됨(사용자, 2026-11-04): (A)**, 서버 시작 시 자동 정리 없음 | 정리는 정확성이 아닌 저장 공간 문제, 시작 경로 불변, 테스트 쉬움 | `router.py`. (C)로 확장 시 `main.py` |
| 19 | (신규, D-포인트비공개) 포인트 수동 조정(관리자 지급·회수) API가 필요한지 | 사용자 요청 | 만들지 않음. 포인트 변경은 payments 내부 호출뿐. **이번 범위 아님**(사용자가 선택하지 않음, 2026-11-04). 만들지 않음 상태 유지 | 공개하면 포인트 임의 증가 위험, 명세는 결제·환불 시점 처리만 정의 | 필요 시 별도 설계(사유·감사 기록 포함) |

현재 코드값 확인(1~7번은 건드리지 않고 상태만 유지): 1번 `Role.OWNER = "OWNER"`(`user.py:8`), 2번 `SignupRequest`에 `business_number` 없음(`schemas.py:7-12`), 3번 `users`에 승인 컬럼 없음(`models.py:13-28`), 4번 `error_handlers.py:33-43`이 400 `VALIDATION_ERROR`, 5번 `login`에 시도 제한 없음(`service.py:80-88`), 6번 `purge_expired_tokens`가 수동 메서드(`service.py:171-174`)이고 호출하는 곳이 없음, 7번 추상 메서드 이름 그대로(`add`, `exists`, `count_by_user`, `delete_expired`). 모두 표의 임시 기본값과 같다.

2026-11-03 사용자 결정으로 C-4, C-5, C-6, C-8은 모두 결정되었고 구현도 끝났다(C-6 코드 정리만 후속). 남은 사용자 결정 항목은 질문 1~10(임시 기본값 유지 중)이며, 구현을 막지 않는다. 질문 11~13(2026-11-04, `OptionalUser`)은 모두 사용자가 위 표의 값으로 **결정함**(11 = 무효 토큰 401, 12 = 비 Bearer 헤더 401, 13 = auth만 구현). 남은 사용자 결정은 없고, catalog 교체(C-13)는 catalog 담당자에게 넘기는 변경 제안으로 남는다. 명세 공백 C-15(공개 EP의 무효 토큰 규칙 통일)만 별도 후속이다.

현재 코드값 확인(1~7번은 건드리지 않고 상태만 유지): 1번 `Role.OWNER = "OWNER"`(`user.py:8`), 2번 `SignupRequest`에 `business_number` 없음(`schemas.py:7-12`), 3번 `users`에 승인 컬럼 없음(`models.py:13-28`), 4번 `error_handlers.py:33-43`이 400 `VALIDATION_ERROR`, 5번 `login`에 시도 제한 없음(`service.py:80-88`), 6번 `purge_expired_tokens`가 수동 메서드(`service.py:171-174`)이고 호출하는 곳이 없음, 7번 추상 메서드 이름 그대로(`add`, `exists`, `count_by_user`, `delete_expired`). 모두 표의 임시 기본값과 같다.

2026-11-03 사용자 결정으로 C-4, C-5, C-6, C-8은 모두 결정되었고 구현도 끝났다(C-6 코드 정리만 후속). 남은 사용자 결정 항목은 질문 1~10(임시 기본값 유지 중)이며, 구현을 막지 않는다.

---

## 14. 스키마·명세 대조 결과 (2026-11-03)

### 14.1 `models.py` vs `schema.sql` (R14) — 일치, 스키마 변경 제안 없음

| 테이블.컬럼 | `schema.sql` | `models.py` | 판정 |
| --- | --- | --- | --- |
| `users.id` | `UUID PK DEFAULT gen_random_uuid()` | `UUID(as_uuid=True)` PK, `default=uuid.uuid4`, `server_default gen_random_uuid()` (`:17-20`) | 일치 |
| `users.email` | `VARCHAR(255) NOT NULL UNIQUE` | `String(255), unique=True` (`:21`) | 일치 |
| `users.password_hash` / `role` | `VARCHAR(255)` / `VARCHAR(20)` NOT NULL | `String(255)` / `String(20)` (`:22-23`) | 일치 |
| `users.name` / `phone` | `VARCHAR(100)` NULL | `String(100) \| None` (`:24-25`) | 일치 |
| `users.users_point` | `INTEGER NOT NULL DEFAULT 0 CHECK (>= 0)` | `server_default="0"` + `ck_users_point_nonneg` (`:15`, `:26`) | 일치 |
| `users.created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | `DateTime(timezone=True)`, `now()` (`:10`, `:27`) | 일치 |
| `users.business_number` | `TEXT` NULL | `Text \| None` (`:28`) | 일치 |
| `point_log.*` | `user_id UUID NOT NULL FK users(id)`, `amount INTEGER`, `point_type TEXT CHECK IN (EARN,USE,RESTORE,REVOKE)`, `created_at TIMESTAMPTZ`, 인덱스 `ix_point_log_user_id` | FK `users.id` + `index=True`, `amount`, `Text`, `ck_point_log_type`, TZ (`:39-48`) | 일치 |
| `token_blacklist.*` | `jti TEXT PK`, `expires_at TIMESTAMPTZ NOT NULL`, 인덱스 `ix_token_blacklist_expires_at` | `Text` PK, TZ + `index=True` (`:54-55`) | 일치 |

도메인·모델의 ID는 `uuid.UUID`, 시간은 timezone 있는 `datetime`이다. `models.py`는 다른 모듈 모델을 import하지 않는다(FK는 문자열 `"users.id"`).

### 14.2 `schemas.py`·`router.py` vs `docs/reference/auth.md` (R15) — 일치

| 명세 | 구현 | 판정 |
| --- | --- | --- |
| POST `/v1/auth/signup` 201, 요청 `email/password/name/phone/role`, 응답 `id,email,name,phone,role,users_point,created_at` | `router.py:25-39`, `schemas.py:7-12`, `:20-29` | 일치. 응답에 `password_hash` 없음 |
| POST `/v1/auth/login` 200 JSON `email/password`, 응답 `access_token`, `token_type="bearer"` | `router.py:42-45`, `schemas.py:15-17`, `:32-34` | 일치. form 본문 400은 `test_login_form_rejected` |
| POST `/v1/auth/logout` 204, Bearer | `router.py:48-56` | 일치 |
| GET `/v1/users/me` 200 | `router.py:59-61` | 일치 |
| GET `/v1/users/me/points` `type`, `page`(0부터, 기본 0), `size`(기본 20, 최대 100), 응답 `users_point, logs[id,amount,point_type,created_at], page, size, total_elements` | `router.py:64-77`, `schemas.py:37-51` | 일치. 범위 오류는 `Query(ge=0)`/`ge=1, le=100` -> 400 `VALIDATION_ERROR`(`error_handlers.py:33-43`) |
| 에러 400/401/409 코드 | `error_handlers.py:25-60`, 도메인 예외의 `error_code` | 일치(테스트로 확인: `pytest` 89 passed) |
| 로그인·가입 요청 `password` 길이 | 명세는 "비밀번호"만 명시, 스키마 설명은 "8자 이상". 8자 검사는 `User.validate_raw_password`(도메인) | 명세에 길이 규칙 없음. 차이는 아니지만 명세에 길이가 없다는 점만 기록 |

---

## 15. 확정 요구조건 정합 작업 (2026-11-05, 정본 `docs/requirements/auth.md`, #20)

- 상태: **설계(코드 변경 없음).** 요구조건의 "현재 코드와 다름" 항목 전부가 대상이다. 사용자가 부재 중이라 결정이 필요한 항목은 추천안을 **"임시 확정(추천)"**으로 표로 올렸다(확정 아님, 사용자 검토 대기).
- 기준: worktree `wt-auth3`(브랜치 `claude/auth-remaining-requirements`, HEAD `09bdf50`). 이 절은 §1~§14와 충돌하면 우선한다. 기존 확정 결정(D-타모듈주입, D-포인트트랜잭션 등)은 유지한다.
- 규칙 번호는 요구조건 `REQ-n`, 불변 규칙은 `R1~R16`으로 가리킨다. 결정 ID는 이 문서 규칙대로 `D-이름`, 정합 이슈는 `C-21`부터, 질문은 `질문 20`부터다.

### 15.0 차단 이슈 (실행 결과)

| # | 확인 명령 | 결과 | 판정 |
| --- | --- | --- | --- |
| B-26 | `(cd src && uv run python -c "import main")` | `import main ok` | 차단 아님 |
| B-27 | `python3 .claude/skills/layer-check/check_layers.py` | 위반 없음, 경고 3건(`[넓은예외]` error_handlers.py). 133개 검사 | 기준선. 구현 후 위반 0 유지 |
| B-28 | `uv run python -c "import jwt, passlib, secrets"` | `ok` | 새 의존성 없음(`secrets`는 표준 라이브러리). `pyproject.toml` 변경 없음 |
| B-29 | `.env.example` 확인 | 새 키 필요 없음(개발용 코드 전달은 로그, D-재설정전달) | 변경 없음 |
| B-30 | `uv run pytest -q -x tests/auth tests/admin` (DB 미기동 환경) | DB 의존 테스트 1건 실패 후 중단. 이후 `test_signup_duplicate_case_insensitive` 단독 실행은 `1 passed` | 실패 원인(연결 오류 여부)을 끝까지 확인하지 못했다. 전체 기준선은 측정하지 못함. **구현 단계에서 오케스트레이터가 DB를 켜고 skip 0을 확인(R16)** |
| B-31 | `Grep "^from (reservations\|payments\|stores\|catalog)" src/auth` | 0건(§15.4 근거) | auth는 다른 모듈을 import하지 않는다. R12 현상 유지 |
| B-32 | `Grep "tests/ + auth/signup"`, `\.signup(`, `User.register(` | `tests/helpers.py`(phone 없음), `.signup(` 22곳, `User.register(` 9곳 | REQ-2 때문에 기존 테스트 수정 필요(§15.9) |
| B-33 | `src/container.py` 열람 | `create_reservation_admin`(`ReservationAdminAdapter`), `create_stores_service`, `create_catalog_service`가 있음. `create_reservation_admin`이 파일 아래쪽(admin 구역)에 정의됨 | 탈퇴 조정 서비스 팩토리는 그 **뒤**에 둬야 함(`Depends` 기본값은 정의 시점에 평가) |

차단 이슈 없음.

### 15.1 요구조건 대 코드 대조

| REQ | 현재 코드 | 상태 | 설계 |
| --- | --- | --- | --- |
| REQ-2·6·7 | `SignupRequest.name/phone` 선택(`schemas.py:10-11`), `User.register`가 None 허용 | 다름 | D-가입필수 |
| REQ-22·23 | 프로필 변경 EP·메서드 없음 | 다름 | D-프로필변경 |
| REQ-24 | 비밀번호 변경 없음 | 다름 | D-비밀번호변경, D-토큰무효화 |
| REQ-25~32 | 재설정 없음 | 다름 | D-재설정* |
| REQ-33~36, 34-1, B-3 | 자진 탈퇴 없음. `withdraw_user`는 포인트를 그대로 둠(`service.py:269-276`) | 다름 | D-자진탈퇴조정, D-탈퇴포인트소멸 |
| REQ-37 | 상한은 `grant_points`만(`user.py:318`). `earn/restore_points`는 상한 없음 | 다름 | D-포인트상한 |
| REQ-53·55 | `GRANT`·`balance_after`·`reason`·`created_by`는 **이미 있음**(`point_log.py`). `EXPIRE` 없음, 유형별 사유·처리자 불변식 없음, API에 `balance_after` 미노출 | 일부 다름 | D-포인트유형소멸 |
| B-2(로그아웃) | `logout`이 `CurrentPrincipal`(`router.py:57`)이라 정지 회원 403. `get_current_principal_allow_suspended`는 이미 있음(`dependencies.py:48`) | 다름 | D-로그아웃정지허용 |
| 주석 | `dependencies.py:97` "아직 어떤 router에도 연결하지 않았다"가 거짓(`reservations/presentation/router.py:7,87`이 사용) | 낡음 | D-주석정리 |
| REQ-19·35 | `authenticate`가 탈퇴 401 처리(`user.py:330`) | 이미 일치 | 변경 없음 |

### 15.2 결정 표 (D-이름, 모두 임시 확정(추천), 사용자 검토 대기)

| ID | 결정 | 상태 | 근거 |
| --- | --- | --- | --- |
| D-가입필수 | `User.register`가 이름·전화번호를 필수로 검사(None·공백만·100자 초과면 `ValueError`). `User.__init__`(DB 복원)은 기존대로 None·빈 값 허용(기존 회원 보존). `SignupRequest.name/phone`은 `str`(필수, `min_length=1`, `max_length=100`). `register_admin`은 변경 없음. `signup()` 시그니처 불변 | 임시 확정(추천) | REQ-2·6·7, B-5. 생성자를 엄격하게 하면 기존 행 로딩이 깨져 로그인 불가 |
| D-프로필변경 | `PATCH /v1/users/me`, 본문 `name?`·`phone?`(둘 중 하나 이상). 도메인 `User.update_profile`: 넘긴 값은 공백만·100자 초과 금지, **적용 뒤 이름·전화번호가 둘 다 채워져야 함**(기존 회원이 하나만 보내면 400). ADMIN은 비어 있어도 허용. 탈퇴 회원 `UserWithdrawnError`. 이메일·역할은 요청 필드에 없음(보내도 무시: Pydantic 기본 extra 무시). 값 trim 안 함(기존 가입과 동일) | 임시 확정(추천) | REQ-22·23, REQ-2 관리자 예외 |
| D-비밀번호변경 | `POST /v1/users/me/password` `{current_password, new_password}` → 204. 도메인 `User.change_password(current, new, hasher, *, keep_jti)`: 현재 비밀번호 불일치 `CurrentPasswordMismatchError`(400 `CURRENT_PASSWORD_MISMATCH`), 새 값은 `validate_raw_password`, 새 값이 현재와 같아도 허용. 성공 시 `invalidate_tokens(keep_jti)` | 임시 확정(추천) | REQ-24, REQ-5. 현재 비밀번호 오류를 401로 하면 클라이언트가 토큰 만료로 오해하므로 400(README "도메인 규칙 위반 400") |
| D-토큰무효화 | 토큰이 무상태 JWT이고 발급 토큰 목록이 없으므로 **회원별 토큰 세대**로 무효화한다. `users.token_version INTEGER NOT NULL DEFAULT 0`, `users.token_keep_jti TEXT NULL`. JWT에 `ver` 클레임. `TokenClaims.token_version: int = 0`(기본값, 클레임 없는 기존 토큰은 0). 유효 조건: `claims.version == user.token_version` 또는 `claims.jti == user.token_keep_jti`. 재설정: version+1, keep None(모든 토큰 무효). 변경: version+1, keep = 변경에 쓴 토큰의 jti(그 토큰만 유지). 무효면 `TokenRevokedError("비밀번호가 변경되어 무효가 된 토큰입니다.")`(401 `TOKEN_REVOKED`, 새 코드 없음). `TokenProvider.issue(user_id, role, now=None, *, token_version=0)`(선택 인자 추가, 기존 호출 호환) | 임시 확정(추천) | REQ-24·32. `iat` 비교안은 초 단위 정밀도 때문에 재설정 직후 로그인 토큰이 무효가 되거나 직전 토큰이 살아남는 경계 오류가 있어 기각. 블랙리스트에 일괄 추가는 jti 목록이 없어 불가 |
| D-재설정코드 | 새 도메인 엔티티 `PasswordResetCode(user_id, code_hash, expires_at, failed_attempts, created_at)`. 상수 `CODE_LENGTH=6`, `TTL=15분`, `MAX_FAILED_ATTEMPTS=5`. 회원당 1행(`user_id` PK): 재요청은 같은 행을 덮어써 이전 코드 무효(REQ-28). 코드는 해시로 저장(`PasswordHasher` 재사용, 새 의존성 없음). `is_usable(now)`: `now < expires_at` 그리고 `failed_attempts < 5`(15분 정각은 만료). `check(raw, hasher, now) -> bool`: 사용 불가면 `InvalidResetCodeError`, 불일치면 `failed_attempts += 1` 후 False, 일치면 True. 5번째 실패 뒤에는 맞는 코드도 거부 | 임시 확정(추천) | REQ-28·29, 경계값 표 |
| D-재설정흐름 | 새 서비스 `PasswordResetService`(별도 클래스, `AuthApplicationService` 생성자 불변). `request_reset(email)`: 회원 조회 → 없음·탈퇴면 `hasher.dummy_verify`로 시간만 맞추고 **아무것도 안 하고 정상 반환**(REQ-27) → 있으면 코드 생성·해시·저장·`commit()` → 그 뒤 `notifier.send_code`(실패는 로그만 남기고 삼킴: 실패를 응답에 드러내면 가입 여부가 노출됨). `confirm_reset(email, code, new_password)`: ① 새 비밀번호 규칙 검사(위반이면 400, **코드 조회·횟수 변경 없음**, REQ-29) ② 회원 없음·탈퇴·코드 행 없음은 모두 `InvalidResetCodeError`(더미 검증 포함) ③ 코드 행 `FOR UPDATE` → `check` ④ 불일치면 횟수 저장 후 **`commit()`하고** `InvalidResetCodeError`(예외로 롤백되면 횟수가 안 올라가므로) ⑤ 일치면 회원 `FOR UPDATE` → `reset_password` → 코드 행 삭제(1회용) → `commit()`. 에러는 사유를 구분하지 않는 한 가지: 400 `INVALID_RESET_CODE` "재설정 코드가 올바르지 않거나 만료되었습니다." 코드 형식은 `^\d{6}$`(어긋나면 Pydantic 400, 횟수에 안 셈) | 임시 확정(추천) | REQ-26~32. 잠금 순서는 코드 행 → 회원 행이며 다른 흐름이 코드 행을 잡지 않아 교착 없음 |
| D-재설정전달 | 코드 전달은 추상 포트: `auth.domain.service.PasswordResetNotifier(ABC)` `async send_code(email, code, expires_at) -> None`. 개발용 구현 `auth.infrastructure.reset_notifier.LoggingPasswordResetNotifier`가 `logging.getLogger("auth.password_reset").warning(...)`로 코드를 로그에 남김(REQ-26 "운영 기록에서 확인"). 코드 생성도 추상 `ResetCodeGenerator(ABC).generate() -> str`, 구현 `SecretsResetCodeGenerator`(`secrets.randbelow(10**6)`, 6자리 0 채움). 둘 다 container 싱글턴. **로그에 원문 코드가 남으므로 개발·시연 전용이며 실제 메일 구현으로 교체(container 한 곳)한 뒤에만 배포한다** | 임시(개발용 구현은 임시, 포트 구조는 확정(추천)) | REQ-26, R8·R9 |
| D-재설정제한 | 재요청 최소 간격·이메일별 요청 횟수 제한은 두지 않는다(요구조건에 없음, REQ-13 로그인 무제한과 같은 정책). 잔여 위험: 재요청으로 5회 한도를 계속 초기화하는 추측 공격. 회원 행 잠금과 bcrypt 비용이 속도를 제한하나 막지는 못함 | 임시 확정(추천), 질문 22 | 요구조건 범위 밖 |
| D-자진탈퇴조정 | **조정 위치는 `AuthApplicationService` 밖**: 새 `auth/application/withdrawal_service.py`의 `AccountWithdrawalService`. `auth/application/ports.py`에 auth가 정의하는 포트 3개(`WithdrawalStorePort`, `WithdrawalOfferPort`, `WithdrawalReservationPort`, 모두 `Protocol`)를 두고 container가 기존 구현을 연결한다: stores=`StoresApplicationService`, offers=`CatalogApplicationService`, reservations=`ReservationAdminAdapter`(이미 있음, `cancel_all_for_user`를 부름). 흐름은 reservations.md 15.4.6의 ①~⑧과 같고(§15.4), 포인트 소멸은 ⑦ `accounts.withdraw_user`가 도메인 `User.withdraw`로 한다. 자진 탈퇴 사유 문자열은 도메인 상수 `SELF_WITHDRAWAL_REASON = "회원 본인 탈퇴"`. EP `POST /v1/users/me/withdraw`(DELETE는 본문 비표준이라 기각), 본문 `{password}`, 응답 200 `{id, status, deleted_at, cancelled_reservation_count}`. 정지 회원은 `CurrentUser`라 403(정지 회원은 로그아웃 외 불가, B-2) | 임시 확정(추천) | REQ-33~36, 34-1, reservations.md C-18, D-32. 상점주 폐점은 admin D13과 같게 맞춤(REQ-36 "강제 탈퇴 규칙과 같음") |
| D-탈퇴포인트소멸 | `User.withdraw(reason, now) -> int`: 상태 전이와 함께 잔액을 0으로 만들고 **소멸량을 반환**(기존 호출자는 반환값을 무시해도 호환). `AuthApplicationService.withdraw_user`(시그니처 불변)가 소멸량 > 0이면 `PointLog.record(user_id, EXPIRE, -소멸량, 0)`을 추가(0이면 내역 없음, REQ-34 ④·53). **admin 강제 탈퇴는 `accounts.withdraw_user`를 이미 호출하므로 admin 파일 수정 없이 같은 규칙이 적용된다.** 순서는 호출자가 보장: 환불의 포인트 복구(⑤)가 소멸(⑦)보다 먼저 | 임시 확정(추천) | REQ-34-1, B-3. 규칙은 도메인 한 곳이라 두 경로가 갈라질 수 없음(R3) |
| D-포인트상한 | `User._add_points`(공용)가 `users_point + amount > POINT_MAX_BALANCE`면 `ValueError("포인트 잔액이 한도를 넘습니다.")`. `earn_points`·`restore_points`·`grant_points`가 공유(문구는 기존 grant와 동일해 admin 테스트 불변). 한도 초과 시 **적립·복구를 거부**(400 `VALIDATION_ERROR`, 잘라서 일부만 올리는 방식은 포기 규칙이 요구조건에 없어 기각). `earn/restore`는 탈퇴 회원이면 `UserWithdrawnError`(방어. `use`·`revoke`는 잔액 0이라 자연히 무해) | 임시 확정(추천), 질문 21 | REQ-37, 35 |
| D-포인트유형소멸 | `PointType.EXPIRE = "EXPIRE"`(탈퇴 소멸. 시간 경과가 아님, REQ-39). `_NEGATIVE_TYPES`에 추가. `PointLog` 불변식 추가: EXPIRE는 음수·`balance_after == 0`, GRANT는 `reason`·`created_by` 필수, 그 외 유형은 둘 다 None(REQ-53·55, 기존 NULL 행과 호환). `PointLogResponse`에 `balance_after: int \| None` 추가(기존 행 NULL), 조회 `type` 필터에 `EXPIRE` 자동 포함. 이름 변경은 enum과 CHECK 두 곳 | 임시 확정(추천), 질문 20 | REQ-53·55. 용어 "소멸"의 코드 이름은 요구조건에 없음 |
| D-로그아웃정지허용 | `POST /v1/auth/logout`이 `get_current_principal_allow_suspended`를 쓴다. 별칭 `PrincipalAllowSuspended = Annotated[AuthenticatedPrincipal, Depends(get_current_principal_allow_suspended)]` 추가. 탈퇴·폐기·위조·세대 불일치 토큰은 그대로 401 | 임시 확정(추천) | B-2, 주체와 정책 표. admin.md:374는 정지 회원 로그아웃을 막으므로 C-24로 전달 |
| D-주석정리 | `dependencies.py:97`의 "아직 어떤 router에도 연결하지 않았다."를 "reservations 픽업 EP(`reservations/presentation/router.py`)가 사용한다."로 교체. 동작 변경 없음 | 임시 확정(추천) | B-2, 15.1 |
| D-서비스분리 | 재설정과 탈퇴 조정은 **새 서비스 2개**로 두고 `AuthApplicationService` 생성자는 바꾸지 않는다(`tests/auth/test_service.py build()`, `test_container.py`, payments·admin 연결 지점 보호). 프로필·비밀번호 변경·`check_self_withdrawable`은 기존 의존성(users, hasher)만 쓰므로 `AuthApplicationService`에 메서드로 추가 | 임시 확정(추천) | 병행 중인 payments 구현에 영향 최소화 |

### 15.3 도메인·인프라·스키마

#### 15.3.1 도메인 (`src/auth/domain/`)

| 파일 | 변경 |
| --- | --- |
| `user.py` | 필드 `token_version: int = 0`, `token_keep_jti: str \| None = None`(생성자 선택 인자, 음수면 `ValueError`). `register`: 이름·전화번호 필수 검사(`_require_profile_text`). 신규 메서드: `update_profile(name, phone)`, `ensure_current_password(raw, hasher)`, `change_password(current, new, hasher, *, keep_jti)`, `reset_password(new, hasher)`, `invalidate_tokens(keep_jti=None)`, `ensure_token_current(version, jti)`, 프로퍼티 `can_reset_password`(탈퇴가 아니면 True). `_add_points`(상한·탈퇴 검사) 도입, `earn/restore/grant`가 사용. `withdraw`가 소멸량(int)을 반환하고 잔액을 0으로. 상수 `SELF_WITHDRAWAL_REASON` |
| `point_log.py` | `PointType.EXPIRE`, 불변식(§15.2 D-포인트유형소멸), 오류 문구 갱신 |
| `password_reset_code.py` (신규) | `PasswordResetCode`(D-재설정코드) |
| `token_claims.py` | `token_version: int = 0` 필드 추가(기본값, 위치 인자 호환) |
| `exceptions.py` | `CurrentPasswordMismatchError(_CodedValueError)` `CURRENT_PASSWORD_MISMATCH`, `InvalidResetCodeError(_CodedValueError)` `INVALID_RESET_CODE`. 둘 다 `ValueError` 하위라 전역 핸들러가 400 + 해당 코드로 변환(`error_handlers.py` 수정 불필요, R6) |
| `service.py` | `ResetCodeGenerator(ABC)`, `PasswordResetNotifier(ABC)` 추가. `TokenProvider.issue`에 `*, token_version: int = 0` 추가 |
| `repository/password_reset_code_repository.py` (신규) | `PasswordResetCodeRepository(ABC)`: `find_by_user_id(user_id, for_update=False)`, `save(code)`(없으면 INSERT, 있으면 덮어쓰기: 새 코드는 `failed_attempts=0`), `delete(user_id)` |

상태 전이(재설정 코드): (없음) → 유효(요청) → 사용됨(삭제, 일치) / 만료(15분) / 무효(5회 실패) / 덮어써짐(재요청). 사용됨·만료·무효는 되살아나지 않는다.

`User` 새 메서드의 `ValueError` 조건:

| 메서드 | 오류 |
| --- | --- |
| `register` | 이름·전화번호 None·공백만·100자 초과 → `ValueError` |
| `update_profile` | 둘 다 None → `ValueError("변경할 항목이 없습니다.")`, 넘긴 값 공백만·100자 초과, 적용 뒤 이름·전화번호 중 비어 있는 것(ADMIN 제외), 탈퇴 → `UserWithdrawnError` |
| `change_password` | 탈퇴 → `UserWithdrawnError`, 현재 불일치 → `CurrentPasswordMismatchError`, 새 값 규칙 위반 → `ValueError` |
| `reset_password` | 새 값 규칙 위반 → `ValueError`, 탈퇴 → `UserWithdrawnError` |
| `ensure_token_current` | 세대 불일치이면서 jti도 keep이 아님 → `TokenRevokedError` |
| `earn/restore/grant_points` | 한도 초과 → `ValueError`, earn/restore 탈퇴 → `UserWithdrawnError` |
| `withdraw` | 기존 `ensure_withdrawable` 오류(관리자 `AdminAccountProtectedError`, 이미 탈퇴 `UserAlreadyWithdrawnError`, 사유 공백) 그대로 |

#### 15.3.2 인프라 (`src/auth/infrastructure/`)

- `models.py`: `UserModel.token_version`(`server_default="0"`), `token_keep_jti`(Text NULL). `PointLogModel` CHECK에 `'EXPIRE'`. 신규 `PasswordResetCodeModel`(`__tablename__ = "password_reset_codes"`).
- `repositories.py`: `SqlAlchemyUserRepository.save/_to_domain`에 두 컬럼 매핑. `SqlAlchemyPasswordResetCodeRepository`: `find_by_user_id`(`with_for_update().execution_options(populate_existing=True)`), `save`(`pg_insert ... on_conflict_do_update(index_elements=["user_id"])`, flush까지만, R5), `delete`.
- `security.py`: `JwtTokenProvider.issue`가 `ver` 클레임을 넣고 `decode`가 `payload.get("ver", 0)`을 `TokenClaims.token_version`으로 돌려줌(정수가 아니면 `AuthenticationError`). `SecretsResetCodeGenerator` 추가.
- `reset_notifier.py` (신규): `LoggingPasswordResetNotifier`.
- 동시성: 재설정 확인은 코드 행 → 회원 행 순 `FOR UPDATE`(D-재설정흐름). 비밀번호 변경·프로필 변경·탈퇴는 `_locked_user`(기존). 포인트 메서드는 기존 `_locked_user` 그대로.

#### 15.3.3 스키마 변경 제안 (직접 `schema.sql`을 고치지 않았다. R14: 구현 시 `schema.sql`, `db-schema/SKILL.md`, `models.py`를 함께 고친다)

```sql
-- S-A1 point_log 유형에 EXPIRE (탈퇴 소멸)
ALTER TABLE point_log DROP CONSTRAINT ck_point_log_type;
ALTER TABLE point_log ADD CONSTRAINT ck_point_log_type
    CHECK (point_type IN ('EARN', 'USE', 'RESTORE', 'REVOKE', 'GRANT', 'EXPIRE'));  -- EXPIRE: 탈퇴 소멸 (auth D-포인트유형소멸)

-- S-A2 토큰 세대 (비밀번호 변경·재설정 시 기존 토큰 무효화, auth D-토큰무효화)
ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN token_keep_jti TEXT;   -- 비밀번호 변경에 쓴 토큰 하나만 유지

-- S-A3 비밀번호 재설정 코드 (회원당 1행, auth D-재설정코드)
CREATE TABLE password_reset_codes (
    user_id          UUID         PRIMARY KEY REFERENCES users (id),
    code_hash        VARCHAR(255) NOT NULL,
    expires_at       TIMESTAMPTZ  NOT NULL,
    failed_attempts  INTEGER      NOT NULL DEFAULT 0 CHECK (failed_attempts >= 0),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```
- S-A4(변경 없음): 잔액 상한은 `INTEGER` 타입이 이미 2,147,483,647이라 별도 CHECK를 두지 않는다. 앱이 먼저 막는다.
- 개발 DB: `create_all`은 새 테이블(S-A3)만 만들고 컬럼 추가·CHECK 변경(S-A1·S-A2)은 하지 않는다. 서버 재시작 전에 위 `ALTER`를 수동 실행해야 한다(reservations RD-32와 같은 방식, 실행은 사용자). 기존 행은 `DEFAULT 0`.
- `db-schema/SKILL.md` §1 ERD, §3 모듈 배치(auth에 `password_reset_codes`), §4 CHECK 설명 갱신 필요.

### 15.4 응용 (application/)

#### 15.4.1 `AuthApplicationService` 추가·변경 (생성자 불변, 포인트 4개 시그니처 불변)

| 메서드 | 시나리오 | commit |
| --- | --- | --- |
| `update_profile(user_id, name, phone) -> User` | `_locked_user` → `user.update_profile` → `users.save` | 1회 |
| `change_password(user_id, current_password, new_password, *, keep_jti) -> None` | `_locked_user` → `user.change_password(..., self.hasher, keep_jti=...)` → `users.save` | 1회 |
| `check_self_withdrawable(user_id, password) -> User` | `get_user` → `user.ensure_current_password` → `user.ensure_withdrawable(SELF_WITHDRAWAL_REASON)`. 읽기 전용 | 없음 |
| `withdraw_user(user_id, reason, *, now, commit=True) -> User` (변경) | `_locked_user` → `expired = user.withdraw(...)` → `users.save` → `expired > 0`이면 `point_logs.add(EXPIRE, -expired, 0)` | 호출자 선택 |
| `login` (변경) | `tokens.issue(user.id, user.role, token_version=user.token_version)` | 없음 |
| `authenticate` (변경) | 기존 상태 검사 뒤 `user.ensure_token_current(claims.token_version, claims.jti)` | 없음 |
| `use/earn/restore/revoke_points` | **시그니처·commit 규약 불변**(C-22) | 호출자 선택 |

#### 15.4.2 `PasswordResetService` (`application/password_reset_service.py`)
생성자(전부 필수, R8): `session, users: UserRepository, codes: PasswordResetCodeRepository, hasher: PasswordHasher, generator: ResetCodeGenerator, notifier: PasswordResetNotifier, clock: Clock`. 시나리오는 D-재설정흐름. 트랜잭션 경계: 코드 발급 `commit` 1회 → 전달. 확인은 실패 시(횟수 증가) `commit` 1회 후 예외, 성공 시 `commit` 1회.

#### 15.4.3 `AccountWithdrawalService` (`application/withdrawal_service.py`) — R12 순환 방지

```python
class AccountWithdrawalService:
    def __init__(self, session, accounts: AuthApplicationService,
                 stores: WithdrawalStorePort, offers: WithdrawalOfferPort,
                 reservations: WithdrawalReservationPort, clock: Clock): ...

    async def withdraw_self(self, user_id, password) -> WithdrawalResult:
        now = self.clock.now()
        user = await self.accounts.check_self_withdrawable(user_id, password)       # ① 읽기
        store = await self.stores.lock_store_of_owner(user_id) if user.is_owner else None   # ②
        open_store = store is not None and not store.is_closed
        if open_store:
            await self.offers.end_all_sales_of_store(store.id, now=now, commit=False)       # ③
            reserved = await self.reservations.has_reserved_for_store(store.id, excluding_user_id=user_id)  # ④
        cancelled = await self.reservations.cancel_active_for_user(user_id, reason=SELF_WITHDRAWAL_REASON)  # ⑤
        if open_store:
            await self.stores.close_store_by_admin(store.id, SELF_WITHDRAWAL_REASON,
                has_reserved_reservations=reserved, now=now, commit=False)                  # ⑥
        done = await self.accounts.withdraw_user(user_id, SELF_WITHDRAWAL_REASON, now=now, commit=False)  # ⑦ 소멸
        await self.session.commit()                                                          # ⑧ 한 번 (R5, R13)
        return WithdrawalResult(done.id, done.status.value, done.deleted_at, cancelled)
```
- 잠금 순서는 reservations.md 15.4.6 표와 같다(offers → reservations → payments → refunds → users). 예외(상점에 타 고객 RESERVED → `STORE_HAS_RESERVED_RESERVATIONS`, 불일치 → 500 `DATA_INCONSISTENT` 등)가 나면 커밋 전이라 전체 롤백(세션 종료).
- `ReservationAdminAdapter`가 내는 `admin.domain.exceptions.ReservationDataInconsistentError`는 전역 핸들러가 이미 500으로 변환한다(`error_handlers.py:40`). auth는 그 예외를 import하지 않는다.
- **R12 근거**: auth의 `AuthApplicationService`·모든 auth 모듈 파일은 reservations·payments·stores·catalog를 import하지 않는다(B-31). `AccountWithdrawalService`는 자기 모듈의 `ports.py` Protocol만 알고, 구현 연결은 `container.py`뿐이다. 생성 그래프는 `AccountWithdrawalService → {AuthApplicationService, ReservationAdminAdapter → ReservationApplicationService → PaymentApplicationService → AuthApplicationService}`이며 `AuthApplicationService`는 이 서비스에 의존하지 않으므로 순환이 없다(`auth → reservations → payments → auth`가 서비스 내부에서 생기지 않음). 서비스 생성자 안에서 다른 서비스를 만들지 않는다.
- 포트(`application/ports.py`, auth가 정의, R11): `WithdrawalStorePort.lock_store_of_owner(owner_id)`, `close_store_by_admin(store_id, reason, *, has_reserved_reservations, now, commit)`, `WithdrawalOfferPort.end_all_sales_of_store(store_id, *, now, commit)`, `WithdrawalReservationPort.cancel_active_for_user(user_id, *, reason) -> int`, `has_reserved_for_store(store_id, *, excluding_user_id=None) -> bool`. 시그니처는 admin 포트와 같아 기존 서비스·어댑터가 구조적으로 만족한다. 반환 객체는 `id`, `is_closed`만 선언한 Protocol.
- **중복 인정**: ①~⑧ 순서가 `AdminApplicationService.withdraw_user`(`admin/application/service.py:82-110`)와 같다. 이번에는 admin 파일을 고치지 않고 병행 둔다. 합치려면 admin이 이 조정 서비스를 쓰도록 바꾸는 후속 작업(C-25).

#### 15.4.4 container (`src/container.py`) — 범위 확장(C-26)
- 자기 구역(auth): `create_password_reset_code_repository`, `create_password_reset_service`, 싱글턴 `_reset_code_generator`, `_reset_notifier`, `wire_dependencies`에 `provide_password_reset_service` 매핑.
- **모듈 간 연결(오케스트레이터 몫, 발주서에 명시)**: `create_account_withdrawal_service(session, accounts=Depends(create_auth_service), stores=Depends(create_stores_service), offers=Depends(create_catalog_service), reservations=Depends(create_reservation_admin))`와 `provide_withdrawal_service` 매핑. `create_reservation_admin`이 아래쪽에 정의돼 있으므로 admin 구역 뒤(`wire_dependencies` 앞)에 둔다(B-33).
- `tests/test_container.py`의 `provide_*` 수집 검사가 새 두 개를 매핑해야 통과한다.

### 15.5 표현 (presentation/) — 엔드포인트 (명세 변경은 §15.7)

| Method | URI | 요청 | 응답 | 성공 | 에러 |
| --- | --- | --- | --- | --- | --- |
| POST | `/v1/auth/signup` (변경) | `SignupRequest`(name·phone 필수) | `UserResponse` | 201 | 400, 409 |
| POST | `/v1/auth/logout` (변경) | Bearer | - | 204 | 401(`UNAUTHORIZED`, `TOKEN_REVOKED`). **정지 회원도 허용** |
| PATCH | `/v1/users/me` | `ProfileUpdateRequest` `{name?, phone?}` | `UserResponse` | 200 | 400, 401, 403 |
| POST | `/v1/users/me/password` | `PasswordChangeRequest` `{current_password, new_password}` | 본문 없음 | 204 | 400(`VALIDATION_ERROR`, `CURRENT_PASSWORD_MISMATCH`), 401, 403 |
| POST | `/v1/users/me/withdraw` | `WithdrawRequest` `{password}` | `WithdrawalResponse` | 200 | 400(`CURRENT_PASSWORD_MISMATCH`, `ADMIN_ACCOUNT_PROTECTED`, `STORE_HAS_RESERVED_RESERVATIONS`, `VALIDATION_ERROR`), 401, 403, 500(`DATA_INCONSISTENT`) |
| POST | `/v1/auth/password-reset/request` | `PasswordResetRequest` `{email}` | 본문 없음 | 204(가입 여부와 무관) | 400(필드 누락) |
| POST | `/v1/auth/password-reset/confirm` | `PasswordResetConfirmRequest` `{email, code, new_password}` | 본문 없음 | 204 | 400(`VALIDATION_ERROR`, `INVALID_RESET_CODE`) |
| GET | `/v1/users/me/points` (변경) | 동일 | `logs[]`에 `balance_after`, `type`에 `EXPIRE` | 200 | 400, 401 |

- 스키마: `PasswordChangeRequest.new_password`·`PasswordResetConfirmRequest.new_password`는 `min_length=1, max_length=128`(규칙 검사는 도메인, 기존 `SignupRequest.password`와 동일). `code`는 `pattern=r"^\d{6}$"`. `WithdrawalResponse(id, status, deleted_at, cancelled_reservation_count)`. 응답에 비밀번호 해시·토큰 세대·재설정 코드 해시는 없다(R15).
- 의존성(`dependencies.py`): `PrincipalAllowSuspended` 별칭, `provide_password_reset_service`, `provide_withdrawal_service` 플레이스홀더, 주석 정리(D-주석정리). 비밀번호 변경은 `CurrentPrincipal`(jti 필요, 정지 회원 403), 프로필·탈퇴는 `CurrentUser`.
- 목록 API 쿼리 매개변수는 기존 `GET /v1/users/me/points`(`type/page/size`)뿐이며 변경 없음.

### 15.6 R1~R16 영향 (설계 판정, 공식 판정은 `layer-checker`)
R1 도메인은 `secrets`·`logging`을 쓰지 않는다(`secrets`는 infrastructure). R2·R8 서비스는 추상만 받음. R3 비밀번호·프로필·세대·소멸·상한 규칙은 `User` 메서드. R4 레포는 도메인 객체만. R5 레포 flush까지, commit은 서비스. R6 전용 예외, 핸들러 수정 없음. R7 에러 형식 불변. R9 `provide_*` 2개를 `wire_dependencies`에 매핑. R10 추상에 선언한 메서드만 호출. R11 포트는 auth 정의, 상대는 구조적 만족. R12 §15.4.3. R13 탈퇴 조정은 같은 세션·`commit=False`·마지막 한 번. R14 §15.3.3(스키마 4개 파일 동시). R15 §15.7. R16 비밀번호·코드를 로그에 남기는 것은 재설정 코드(개발용, D-재설정전달)뿐이고 비밀번호는 남기지 않는다.

### 15.7 명세 변경 목록 (오케스트레이터 소유, 설계자는 수정하지 않음)
1. `docs/reference/auth.md` §1: `name`·`phone` 필수(O)로 변경, 400 사유에 "이름·전화번호 누락" 추가.
2. §3 로그아웃: 정지된 회원도 호출 가능, 에러 표 유지.
3. §5 포인트 내역: `type`에 `EXPIRE`, 응답 `logs[].balance_after`(nullable) 추가, `point_type` 설명 `EARN/USE/RESTORE/REVOKE/GRANT/EXPIRE`.
4. 새 절: 프로필 변경(PATCH), 비밀번호 변경, 비밀번호 재설정 요청, 재설정 확인, 자진 탈퇴(요청·응답·에러 표, 재설정 요청은 가입 여부와 무관하게 204).
5. 새 에러 코드 표기: `CURRENT_PASSWORD_MISMATCH`, `INVALID_RESET_CODE`. 비밀번호 변경 뒤 이전 토큰은 `TOKEN_REVOKED`.
6. 파일 머리말·"포인트 변경 (API 없음)" 절: 소멸은 탈퇴 처리에서만 발생한다는 문장 추가.
7. `docs/reference/README.md`: auth 목록 7개 → 12개 행 추가, "포인트 `point_log.point_type`" 상태 값 표와 "포인트 정책" 표에 `EXPIRE` 행, `ver` 클레임은 내부라 명세 제외, 노션에 나온 error_code 목록에 새 코드 2개.
8. `docs/reference/admin.md` 강제 탈퇴 EP: 남은 포인트가 소멸되고 `EXPIRE` 내역이 남는다는 문장(C-24).
9. `db-schema/SKILL.md`·`schema.sql`: §15.3.3.

### 15.8 구현 쓰기 범위 (`layer-implementer` 발주용)

| 파일 | 내용 |
| --- | --- |
| `src/auth/domain/{user,point_log,token_claims,exceptions,service}.py` | §15.3.1 |
| `src/auth/domain/password_reset_code.py` (신규) | 엔티티 |
| `src/auth/domain/repository/password_reset_code_repository.py` (신규) | 추상 |
| `src/auth/infrastructure/{models,repositories,security}.py` | §15.3.2 |
| `src/auth/infrastructure/reset_notifier.py` (신규) | 개발용 전달 |
| `src/auth/application/service.py` | §15.4.1 |
| `src/auth/application/{password_reset_service,withdrawal_service,ports}.py` (신규) | §15.4.2~3 |
| `src/auth/presentation/{schemas,router,dependencies}.py` | §15.5, 주석 정리 |
| `tests/auth/**` | §15.9 |
| **범위 확장 (표시, 발주서에 명시 필요)** | |
| `src/container.py` | 자기 구역 외 모듈 간 연결(§15.4.4, C-26). 다른 모듈 팩토리는 수정하지 않고 `Depends`로 참조만 |
| `tests/helpers.py`, `tests/test_container.py` | 가입 헬퍼에 `phone` 추가, `provide_*` 매핑 검사 확장(공용 테스트 파일) |
| `.claude/skills/db-schema/{SKILL.md,schema.sql}`, `docs/reference/**`, `.env.example`(변경 없음) | §15.3.3·§15.7, 오케스트레이터 |
| **하지 않음(확정)** | `src/admin/**`(C-25는 후속), `src/reservations/**`, `src/payments/**`, `src/stores/**`, `src/catalog/**`, `src/error_handlers.py`, `src/main.py`(모델 import는 이미 `auth_models`), `.claude/**` |

완료 게이트는 `backend-invariants` §7(위반 0, `import main`, `pytest -rs` skip 0).

### 15.9 테스트 계획
- **기존 테스트 수정**: `tests/helpers.py` `signup()`에 `phone`; `.signup(` 22곳과 `User.register(` 9곳(`tests/auth/**`)에 이름·전화번호 추가; 재설정 후 토큰·포인트 내역 단언에 영향 있는 기존 단언 점검(`tests/auth/test_status_api_db.py` 강제 탈퇴 테스트는 잔액 0·EXPIRE 내역 단언 추가). `PointLogResponse` 정확 일치 단언이 있으면 `balance_after` 추가.
- **도메인(DB 없음)**: register 필수·경계(100자·공백), `update_profile` 표(일부만·둘 다·none·기존 빈 회원·ADMIN), `change_password`(불일치·약함·성공 시 세대·keep), `ensure_token_current` 표(현재 세대, 이전 세대, keep jti, 두 번째 변경 뒤 이전 keep 무효), `reset_password`, 상한(최대값 OK, +1 거부, 실패 시 잔액 불변, grant 문구 동일), 탈퇴 회원 earn/restore 거부, `withdraw` 소멸량(0·양수·관리자 거부 시 잔액 불변), `PointLog` EXPIRE·GRANT·기타 불변식, `PasswordResetCode`(6자리 검증, 15분 정각 만료, 4회 실패 뒤 일치 OK, 5회 실패 뒤 일치도 거부, 성공 시 횟수 불변).
- **서비스(fake, DB 없음)**: `PasswordResetService` 요청(가입자: 저장·해시 저장·전달 1회·commit 1, 미가입·탈퇴: 저장 0·전달 0·`dummy_verify` 호출·예외 없음, 전달 예외를 삼켜도 commit 유지, 재요청이 횟수 초기화·이전 코드 무효), 확인(성공: 비밀번호·세대 변경·코드 삭제·commit 1·이전 토큰이 `authenticate`에서 `TOKEN_REVOKED`, 오답: 횟수 1 저장+commit 1+예외, 5번째 실패 뒤 잠김, 약한 새 비밀번호: 횟수 불변·commit 0·코드 계속 유효, 만료, 미가입·탈퇴가 같은 오류, 재사용 거부). `AuthApplicationService`: 프로필, 비밀번호 변경 후 `authenticate`(현재 토큰 유효·다른 토큰 무효·변경 후 새 로그인 토큰 유효), `login`이 세대를 넣음, `withdraw_user` 소멸 내역(`EXPIRE`, 음수, `balance_after 0`, 잔액 0이면 내역 없음), earn 상한. `AccountWithdrawalService`(포트 fake 기록기): 호출 순서(고객: check → cancel → withdraw → commit, 상점주 열린 상점: lock → end_sales → has_reserved(excluding) → cancel → close → withdraw → commit), commit 정확히 1회, 비밀번호 오류·관리자는 포트 호출 0, 타 고객 RESERVED로 `close` 예외 시 commit 0, 취소 사유가 상수.
- **API/DB(`db` 마커)**: 가입 필수 400, PATCH, 비밀번호 변경(현재 토큰 `/me` 200·다른 토큰 401), 재설정(알림을 fake로 바꿔 코드 수집, 5회 실패, 재설정 뒤 모든 토큰 401, 미가입 이메일도 204), 정지 회원 로그아웃 204(정지 회원 `/me`는 403), 자진 탈퇴(포인트 있는 고객: `WITHDRAWN`·로그인 401·`EXPIRE` 내역·예약 취소, 상점주+타 고객 RESERVED: 400 전체 롤백, 관리자 400), 포인트 내역의 `EXPIRE`·`balance_after`.
- **구조**: `tests/test_container.py`에 `provide_*` 매핑 확장, `AuthApplicationService` 생성자 인자 불변 확인, `src/auth/**`가 reservations·payments·stores·catalog를 import하지 않는 정적 검사(R12 방어).
- 병행 payments 보호: `use/earn/restore/revoke_points` 시그니처·`commit` 인자 불변을 `inspect.signature` 단언으로 고정.

### 15.10 정합 이슈 (C-21~C-26)

| ID | 위치 | 내용 | 제안 / 상태 |
| --- | --- | --- | --- |
| C-21 | `docs/design/auth.md` D-포인트비공개(2026-11-05 갱신 제안 문구), D-블랙리스트정리 | D-포인트비공개의 "관리자 수동 조정 없음"은 이미 지급만 허용으로 바뀜(B-4). 이 절의 소멸은 탈퇴 처리 내부에서만 발생(공개 EP 없음)이라 D-포인트비공개의 "공개 포인트 EP 없음"은 유지 | 구현 후 해당 행의 "제안" 표기를 확정 문구로 정리(설계 담당) |
| C-22 | payments `docs/design/payments.md` §10 | 이 설계는 `use/earn/restore/revoke_points` **시그니처·commit 규약을 바꾸지 않는다.** 동작 변화 두 가지: (a) `earn`·`restore`가 잔액 상한 초과 시 `ValueError`(400)로 거부 — 결제 적립·환불 복구가 이 경우 롤백되며 현실적으로는 잔액 ~21억에서만 발생 (b) 탈퇴 회원에 `earn/restore`는 `UserWithdrawnError`(400 `USER_WITHDRAWN`), 정상 흐름(복구 ⑤가 소멸 ⑦보다 먼저)에서는 발생하지 않음 | payments 담당에게 전달. payments 변경 불필요. 질문 21 |
| C-23 | `tests/**` 기존 가입 호출 | REQ-2로 이름·전화번호 없는 가입이 400이 된다. 다른 모듈 테스트(stores 등)는 `tests/helpers.py`를 쓰므로 헬퍼 한 곳 수정으로 해소(B-32) | 구현 범위에 포함(§15.8) |
| C-24 | admin 담당자, `docs/design/admin.md` D12·D24·`:374`, `docs/reference/admin.md` EP 4 | 요구조건 B-2·B-3: (1) 정지 회원 로그아웃 허용 — `:374`는 막음 (2) 강제 탈퇴도 잔액을 소멸하고 `EXPIRE` 내역을 남김(D24와 다름) (3) 결제 대기 예약도 취소(D12와 다름, reservations.md D-31에서 이미 반영). (2)는 auth `withdraw_user` 변경만으로 자동 적용되고 admin 코드 수정은 없음 | admin 설계·명세 문구 갱신 전달 |
| C-25 | `src/admin/application/service.py:82-110`와 §15.4.3 | 탈퇴 조정 순서가 두 곳에 중복. 이번 범위에서는 admin 파일을 수정하지 않음 | 후속: admin이 `AccountWithdrawalService`를 쓰도록 통합(admin 담당 승인 필요, 범위 확장) |
| C-26 | `src/container.py` | 탈퇴 조정 서비스는 auth·stores·catalog·reservations 팩토리를 모두 참조해 `layer-implementer`의 기본 범위(자기 모듈 구역)를 넘는다(orchestration §4) | 발주서에 container 범위 확장을 명시 |

### 15.11 질문 목록과 임시 기본값 (모두 제안, 확정 아님)

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 | 바꾸기 쉬운 곳 |
| --- | --- | --- | --- | --- | --- |
| 20 | "소멸" 포인트 유형의 코드 이름 | REQ-53 | `EXPIRE` | 포인트 소멸의 통상 용어 | `PointType` enum + `ck_point_log_type` |
| 21 | 적립·복구가 잔액 상한을 넘을 때 거부할지, 상한까지만 올리고 나머지를 포기할지 | REQ-37 | 거부(400) | grant와 동일 규칙, 포기 규칙이 요구조건에 없음 | `User._add_points` |
| 22 | 재설정 요청 최소 간격·횟수 제한 | REQ-27~29(제한 언급 없음) | 없음 | REQ-13과 같은 정책 | `PasswordResetService.request_reset` |
| 23 | 재설정 코드 전달 수단 | REQ-26 | 개발용 로그 출력(`LoggingPasswordResetNotifier`) | REQ-26 임시 방식 | container `_reset_notifier` 한 곳 |
| 24 | 현재 비밀번호 불일치의 상태 코드 | REQ-24·36 | 400 `CURRENT_PASSWORD_MISMATCH` | README "규칙 위반 400" | 새 예외 클래스 한 곳 |
| 25 | 자진 탈퇴 EP 모양·응답 | REQ-33 | `POST /v1/users/me/withdraw` + 비밀번호 본문, 200 + 취소 건수 | DELETE 본문 비표준, admin EP 4와 같은 응답 | router·schemas |
| 26 | 정지된 회원의 자진 탈퇴 | B-2(정지 회원은 로그아웃 외 불가) | 403(불가) | 요구조건 문구 | 탈퇴 EP 의존성 `CurrentUser` |
| 27 | 상점주 자진 탈퇴 시 열린 상점 폐점 여부 | REQ-36 | 폐점(admin D13과 같음) | "강제 탈퇴 규칙과 같음" | `AccountWithdrawalService` ⑥ |
| 28 | 새 비밀번호가 현재와 같아도 허용 | REQ-24(언급 없음) | 허용 | 제한 근거 없음 | `User.change_password` |
| 29 | 프로필 변경에서 ADMIN의 이름·전화번호 | REQ-2·23 | 비어 있어도 허용 | REQ-2 관리자 예외 | `User.update_profile` |
| 30 | `GET /v1/users/me/points`에 `balance_after` 노출 | REQ-55 | 노출(null 허용, 추가 필드) | 저장만 하면 회원이 볼 수 없음 | `PointLogResponse` |
