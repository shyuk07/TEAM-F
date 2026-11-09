# 서버 시작 시 DB 스키마 검사 설계 (공용 기반)

- 대상: 특정 모듈이 아닌 공용 시작 코드(`src/schema_check.py`, `src/main.py`, `src/database.py` 주변), `docs/migrations/`
- 상태: 사용자가 방향을 확정했다(2026-11-09): 시작 시 모델과 DB를 비교해 빠진 테이블·컬럼·이름 있는 CHECK가 있으면 무엇이 빠졌는지와 SQL 파일 위치를 알리고 시작을 멈춘다. DB는 자동으로 바꾸지 않는다. 아래 세부는 "확정(위임, 2026-11-09)"로 표시한 추천안이다.
- 범위 밖: Alembic 도입(팀 합의 필요), 타입·NULL·인덱스·FK 비교, 자동 ALTER.

## 0. 차단 이슈

| 확인 | 명령 / 근거 | 결과 |
| --- | --- | --- |
| 현재 시작 순서 | `Read src/main.py` lifespan | `get_auth_settings()` → `Base.metadata.create_all` → `seed_admin()` → `yield` → `engine.dispose()`. 검사는 `create_all`과 `seed_admin` 사이에 들어간다 |
| 테스트가 lifespan을 타는지 | `Read tests/conftest.py`, `Grep lifespan tests` | `httpx.ASGITransport(app=app)`는 lifespan을 실행하지 않고 lifespan 호출 테스트도 없다. 테스트 DB는 `drop_all`→`create_all`이라 항상 맞는다. 충돌 없음 |
| 새 의존성 | 설계가 쓰는 것은 `sqlalchemy.inspect`뿐 | 추가 패키지 없음 |
| 루트 공용 파일 규칙 | `Read .claude/skills/layer-check/check_layers.py:35-49, 236-246` | `main.py`·`container.py` 외의 `src/*.py`도 import 제한을 받는다(공용은 기능 모듈 domain만 참조 가능). `schema_check.py`는 `sqlalchemy`·`database`만 import하므로 통과 |
| 모델에 있는 이름 있는 CHECK | `Grep CheckConstraint src/**/models.py` | 아래 5절 목록(15개 안팎). 이름 없는 CHECK는 현재 없음 |

차단 이슈: 없음. 이 설계는 구현·실행 전 상태이며 코드를 바꾸지 않았다.

## 1. 결정 표 (D)

| # | 결정 | 상태 |
| --- | --- | --- |
| D-1 | 검사 시점: `lifespan`에서 `create_all` 직후, `seed_admin` 이전. 새 테이블은 `create_all`이 만들므로 그 뒤에 남은 차이만 검사한다. `seed_admin`이 빠진 컬럼 때문에 원인 모를 500·예외를 내기 전에 먼저 멈추기 위해 seed보다 앞에 둔다 | 확정(위임, 2026-11-09) |
| D-2 | 위치: 새 파일 `src/schema_check.py`(루트 공용 단일 파일, `database.py`·`error_handlers.py`와 같은 부류). `database.py`에 넣지 않는다(연결 설정과 검사 로직을 분리, `database.py` 변경을 피함). 기능 모듈 안에 두지 않는다(`layer-implementation` 공통 규칙) | 확정(위임) |
| D-3 | 비교 대상: `Base.metadata`의 모든 테이블에 대해 (1) 모델에 있고 DB에 없는 컬럼 (2) 모델의 `name`이 있는 `CheckConstraint`가 DB에 이름으로 없음. 테이블 자체가 없으면 `create_all` 뒤에는 없을 수 없으므로(만들기 실패는 그쪽에서 예외) 방어적으로 "테이블 없음"도 보고한다 | 확정(위임) |
| D-4 | CHECK는 이름만 비교하고 식은 비교하지 않는다. 이유: PostgreSQL이 저장하는 식(`pg_get_constraintdef`)은 `IN (...)`을 `= ANY (ARRAY[...])`로, 캐스트를 덧붙여 다시 쓰므로 모델 문자열과 안정적으로 비교할 수 없다. 오탐으로 멀쩡한 팀원 PC의 시작을 막는 편이 더 해롭다. 대신 값 목록이 바뀐 CHECK(`ck_point_log_type`, `ck_offer_status`)는 5절에 적은 대로 마이그레이션 파일이 재생성하고, 이름만으로는 옛 정의를 못 잡는 한계를 C-2에 남긴다 | 확정(위임) |
| D-5 | 타입·NULL·기본값 차이는 비교하지 않는다. 이유: 문제의 원인(컬럼 누락)은 이름 비교로 충분히 잡히고, `String(20)`↔`VARCHAR(20)`, `server_default` 문자열 표기, `Mapped[...]`의 NULL 추론은 inspector 결과와 모델이 표기상 달라 오탐이 많다. 필요해지면 후속 | 확정(위임) |
| D-6 | DB에만 있는 여분 컬럼·제약·테이블은 무시한다(`price` 같은 schema.sql 전용 컬럼이 실제로 있다) | 확정(위임) |
| D-7 | 실패 동작: 빠진 항목 전체 목록과 SQL 위치(`docs/migrations/`)를 담은 `RuntimeError`를 던져 시작 중단. 관리자 시드 설정 오류와 같은 방식이며 별도 도메인 예외·HTTP 변환은 없다(HTTP 요청 처리 전 단계). 메시지는 한 번에 전부(첫 건만 보고하지 않음) | 확정(위임) |
| D-8 | 끄는 방법: 환경변수 `SCHEMA_CHECK`, 기본 켜짐. `off`(대소문자 무시, `0`·`false`도 허용)일 때만 건너뛰고, 건너뛰면 `logging.warning` 한 줄. 그 외 값은 켜짐. `.env.example`에 주석으로 설명(변경 제안 3절). 시크릿 아님(R16 무관) | 확정(위임) |
| D-9 | 구현 형태: 순수 함수 둘과 얇은 비동기 진입점. `find_schema_drift(connection, metadata) -> list[Drift]`(동기 `Connection`, `inspect` 사용), `format_drift_message(drifts) -> str`, `async check_schema(engine, metadata=Base.metadata)`가 `engine.connect()` + `run_sync`로 호출하고 차이가 있으면 `RuntimeError`. 테스트는 앞의 두 함수와 `check_schema`를 임시 DB·임시 `MetaData`로 호출한다 | 확정(위임) |
| D-10 | 마이그레이션 SQL 위치와 이름: `docs/migrations/YYYY-MM-DD_<PR>_<내용>.sql`, 날짜는 PR 병합일. 파일은 모두 다시 실행해도 안전(`IF NOT EXISTS`, 제약은 `DO` 블록에서 `pg_constraint` 이름 확인). 파일명 순서대로 실행하면 최신 모델과 맞는다. 실행 방법은 README 한 단락(6절) | 확정(위임) |
| D-11 | 메시지의 SQL 안내는 항목별 개별 SQL을 생성하지 않고 폴더 위치와 실행 예시만 낸다(안내 문구를 코드에 고정하지 않으려면 상수 `MIGRATIONS_HINT` 한 곳에 둔다). 새 컬럼을 추가하는 PR은 같은 PR에 `docs/migrations/` 파일을 함께 추가해야 한다(운영 규칙 제안, C-3) | 확정(위임) |

## 2. 도메인 / 응용 / 표현

해당 없음. 검사는 인프라·시작 코드이고 엔티티·서비스·엔드포인트가 없다. R1(domain 순수)에 영향 없음.

## 3. 인프라: `src/schema_check.py`

```python
import logging
import os
from dataclasses import dataclass

from sqlalchemy import CheckConstraint, MetaData, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from database import Base

MIGRATIONS_DIR = "docs/migrations/"  # D-10, D-11: 안내 문구는 이 상수 한 곳

@dataclass(frozen=True)
class Drift:
    table: str
    kind: str   # "table" | "column" | "check"
    name: str   # 테이블이면 테이블명과 같음

def find_schema_drift(connection: Connection, metadata: MetaData) -> list[Drift]: ...
def format_drift_message(drifts: list[Drift]) -> str: ...
def schema_check_enabled(env=None) -> bool: ...   # SCHEMA_CHECK 해석(D-8)
async def check_schema(engine: AsyncEngine, metadata: MetaData = Base.metadata) -> None: ...
```

`find_schema_drift` 알고리즘 (읽기 전용, `inspect(connection)` 한 개 재사용):
1. `insp = inspect(connection)`; `existing = set(insp.get_table_names())`.
2. `metadata.sorted_tables`를 순회. 테이블이 `existing`에 없으면 `Drift(table, "table", table)` 추가 후 다음으로.
3. 컬럼: `have = {c["name"] for c in insp.get_columns(table.name)}`; `table.columns` 중 이름이 `have`에 없으면 `Drift(table, "column", name)`.
4. CHECK: `have_ck = {c["name"] for c in insp.get_check_constraints(table.name) if c.get("name")}`; `table.constraints` 중 `isinstance(CheckConstraint)`이고 `name`이 있으며 `have_ck`에 없으면 `Drift(table, "check", name)`. 이름 없는 CHECK(`name is None`)는 건너뛴다.
5. 결과는 테이블 순서, 컬럼 → CHECK 순으로 정렬해 메시지가 결정적이게 한다.
6. 같은 스키마(`public`) 기본 검색 경로만 본다(프로젝트가 스키마를 나누지 않는다).

메시지 형식 예:

```text
DB 스키마가 모델과 맞지 않습니다. 서버를 시작하지 않습니다 (DB는 자동으로 바꾸지 않습니다).
  - users: 컬럼 failed_login_count, login_locked_until
  - users: CHECK ck_users_failed_login_nonneg
  - pickup_reservations: 컬럼 cancelled_by
docs/migrations/ 의 SQL을 파일명 순서대로 실행하세요. 이미 반영된 항목은 건너뛰도록 작성돼 있어 다시 실행해도 안전합니다.
예) docker compose exec -T db psql -U lastcall -d lastcall < docs/migrations/2026-11-09_45_login_lockout.sql
검사를 끄려면 SCHEMA_CHECK=off (권장하지 않음)
```

(예시의 `db` 서비스명·사용자명은 `compose.yaml` 기준으로 구현자가 확인한다. 확인 필요 아님: 파일을 읽어 맞추면 된다.)

동시성: 읽기만 하며 잠금이 필요 없다(`with_for_update` 불필요). 레포지토리·`*Model` 반환(R4)과 무관. `commit`을 하지 않는다(R5 무관).

`check_schema`: `schema_check_enabled()`가 거짓이면 `logging.getLogger(__name__).warning("SCHEMA_CHECK=off: DB 스키마 검사를 건너뜁니다.")` 후 반환. 아니면 `async with engine.connect() as conn: drifts = await conn.run_sync(find_schema_drift, metadata)`; 비어 있지 않으면 `raise RuntimeError(format_drift_message(drifts))`. 연결 실패 등 다른 예외는 그대로 전파한다.

## 4. `src/main.py` 변경 (공용 초기 세팅 파일)

```python
from schema_check import check_schema
...
async with engine.begin() as connection:
    await connection.run_sync(Base.metadata.create_all)
await check_schema(engine)   # create_all이 못 채우는 차이(기존 테이블의 새 컬럼·CHECK)를 시작 시 드러낸다
await seed_admin()
```

- 모든 `models.py` import가 이미 위에 있으므로 `Base.metadata`에 전체 테이블이 등록돼 있다(비교 누락 없음).
- RuntimeError가 lifespan에서 나면 uvicorn이 시작 실패로 종료하고 트레이스백에 메시지가 보인다. `engine.dispose()`는 `yield` 뒤라 호출되지 않지만 프로세스가 종료되므로 문제없다(관리자 시드 실패와 동일).
- `src/database.py`는 바꾸지 않는다.

## 5. 마이그레이션 SQL 파일 (`docs/migrations/`)

공통 규칙: 컬럼은 `ADD COLUMN IF NOT EXISTS`, 제약은 아래 헬퍼 패턴. 파일 맨 위에 `-- 실행: ...`과 대상 PR·설계 문서 위치를 주석으로 적는다. 각 파일은 트랜잭션(`BEGIN; ... COMMIT;`)으로 감싼다.

```sql
-- 제약 추가 패턴 (이름이 없을 때만)
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                 WHERE conname = 'ck_xxx' AND conrelid = 'public.<table>'::regclass) THEN
    ALTER TABLE <table> ADD CONSTRAINT ck_xxx CHECK (...);
  END IF;
END $$;
```

값 목록이 바뀐 CHECK(`ck_point_log_type`, `ck_offer_status`)는 "정의에 새 값이 없으면 drop 후 재생성" 패턴을 쓴다(`pg_get_constraintdef(oid) NOT LIKE '%EXPIRE%'`).

| 파일 | PR / 근거 | 내용 |
| --- | --- | --- |
| `2026-11-05_25_admin_columns.sql` | #25, `docs/design/admin.md` 2.4절 | `users`: `status VARCHAR(20) NOT NULL DEFAULT 'APPROVED'`, `approved_at`, `rejected_reason VARCHAR(500)`, `rejected_at`, `suspended_reason VARCHAR(500)`, `suspended_at`, `suspended_until`, `deleted_at`, `deleted_reason VARCHAR(500)`, `ck_users_status`. `point_log`: `reason VARCHAR(500)`, `balance_after INTEGER`, `created_by UUID REFERENCES users(id)`(`point_log` CHECK는 아래 #30 파일이 최종값으로 처리). `stores`: `suspended_reason VARCHAR(500)`, `suspended_at`, `closed_reason VARCHAR(500)`. `discount_offers`: `suspended_reason VARCHAR(500)`, `suspended_at`, `ck_offer_status`(옛 status CHECK는 이름이 달라 `pg_constraint`에서 `conrelid='discount_offers'`, `contype='c'`, 정의에 `status` 포함, 이름이 `ck_offer_status`가 아닌 것을 모두 drop 후 재생성. admin.md 2.4절이 "이름은 DB에서 확인"이라 한 부분을 이 쿼리로 대체) |
| `2026-11-06_29_payments_point_used.sql` | #29, `docs/design/payments.md` 1043행 | `payments.point_used INTEGER NOT NULL DEFAULT 0`, `ck_payments_point_used CHECK (point_used >= 0)`(원본은 이름 없는 인라인 CHECK라 DB 자동 이름이 달랐다. 모델 이름과 맞추려고 이름 있는 제약으로 추가하고, 이미 인라인 CHECK가 있어도 중복은 무해) |
| `2026-11-06_30_auth_token_version_expire.sql` | #30, `docs/design/auth.md` 15.3.3절 | `users.token_version INTEGER NOT NULL DEFAULT 0`, `users.token_keep_jti TEXT`, `ck_point_log_type` 6개 값(`EARN, USE, RESTORE, REVOKE, GRANT, EXPIRE`)으로 재생성. `password_reset_codes`는 `create_all`이 만들므로 SQL 없음(주석으로 명시). 단 #30 이후 `password_reset_codes`가 이미 옛 모양으로 있다면 C-4 참고 |
| `2026-11-09_44_reservation_cancelled_by.sql` | #44, `docs/design/reservations.md` 1049-1056행 | `pickup_reservations.cancelled_by VARCHAR(20)`, `ck_reservation_cancelled_by`, `ck_reservation_cancelled_by_status` |
| `2026-11-09_45_login_lockout.sql` | #45, `docs/design/auth.md` 1435-1437행 | `users.failed_login_count INTEGER NOT NULL DEFAULT 0`, `users.login_locked_until TIMESTAMPTZ`, `ck_users_failed_login_nonneg` |

작성 순서와 검증: 구현자는 위 파일을 쓴 뒤 일회용 DB(`lastcall_test`와 다른 이름)에서 (1) 옛 스키마(해당 PR 이전 모델 모양)를 만들고 (2) 파일을 전부 두 번 실행해 오류가 없고 (3) `find_schema_drift`가 빈 목록인지 확인한다. 실제 팀원 DB에는 실행하지 않는다(실행은 사용자).

## 6. README 변경 제안 (한 단락, "5. FastAPI 실행" 앞 또는 뒤)

> **DB 스키마가 바뀐 PR을 받았을 때:** 서버는 시작할 때 DB 테이블이 모델과 맞는지 검사합니다. `create_all`은 이미 있는 테이블에 새 컬럼을 추가하지 못하므로, 컬럼이나 CHECK가 빠져 있으면 무엇이 빠졌는지 알려 주며 시작을 멈춥니다(DB를 자동으로 바꾸지 않습니다). 그때는 `docs/migrations/`의 SQL 파일을 파일명 순서대로 실행하세요(다시 실행해도 안전합니다). 예: `docker compose exec -T <db 서비스명> psql -U lastcall -d lastcall < docs/migrations/<파일>.sql`. 데이터가 필요 없다면 `docker compose down -v` 후 다시 `up -d`로 DB를 새로 만드는 방법도 있습니다. 검사를 잠시 끄려면 `.env`에 `SCHEMA_CHECK=off`를 둡니다(권장하지 않음). 컬럼을 추가하는 PR은 같은 PR에 `docs/migrations/` 파일을 함께 넣습니다.

## 7. R1~R16 영향

| 규칙 | 영향 |
| --- | --- |
| R1, R2, R11 | `schema_check.py`는 `sqlalchemy`·`database`만 import한다. 기능 모듈을 import하지 않고 `Base.metadata`만 쓴다. `check_layers.py` 루트 파일 검사 통과 예상 |
| R3, R4, R5, R8~R10, R13 | 해당 없음(엔티티·레포·서비스·DI 없음). 읽기 전용, `commit` 없음 |
| R6, R7 | 해당 없음. HTTP 처리 이전 단계의 시작 실패이며 `HTTPException`을 쓰지 않는다. 시작 중단은 에러 응답 형식 대상이 아니다 |
| R12 | `main`이 `schema_check`를 import, `schema_check`는 `database`만. 순환 없음. `(cd src && uv run python -c "import main")` 확인 필요 |
| R14 | 스키마 변경 없음. 마이그레이션 파일은 `models.py`·`schema.sql`의 현재 상태를 따라간다. 파일 내용이 `schema.sql`과 어긋나면 `schema.sql`이 정본 |
| R15 | API 변경 없음 |
| R16 | 시크릿 없음. 의존성 추가 없음. 테스트를 skip으로 처리하지 않는다. DB가 필요한 테스트는 기존 `db` 마커 방식을 따른다 |

## 8. 쓰기 범위

| 파일 | 소유 | 비고 |
| --- | --- | --- |
| `docs/design/schema-check.md` | 설계자(이 문서) | 이번에 작성 |
| `src/schema_check.py` (신규) | 구현자 | 공용 코드 |
| `src/main.py` | **범위 확장**: 공용 초기 세팅 파일(import 1줄 + `check_schema(engine)` 호출 1줄) | `layer-implementation` §7이 정한 "두 줄" 밖이므로 보고서에 표시 |
| `docs/migrations/*.sql` (신규 5개) | 구현자 또는 오케스트레이터(`docs/design/` 밖이므로 범위 지정 필요) | |
| `README.md` | 오케스트레이터(6절 단락) | |
| `.env.example` | 오케스트레이터 | `SCHEMA_CHECK` 주석 한 줄 |
| `tests/test_schema_check.py` (신규) | 구현자 | |
| `src/database.py` | 변경 없음 | |

## 9. 테스트 계획 (`tests/test_schema_check.py`)

DB가 필요한 테스트는 기존 `session_factory`처럼 연결 실패 시에만 skip하는 방식을 쓰되, 별도 임시 DB를 만들지 않고 `lastcall_test`에서 `Base.metadata` 대신 **테스트 전용 `MetaData`**를 쓴다(앱 테이블을 건드리지 않는다).

| # | 시나리오 | 기대 |
| --- | --- | --- |
| T-1 | 임시 `MetaData`에 테이블 `t_a(id, x, CHECK ck_t_a_x)`를 정의, DB에는 `id`만 있는 `t_a`를 `CREATE TABLE`로 만든다 | `find_schema_drift`가 `Drift("t_a","column","x")`와 `Drift("t_a","check","ck_t_a_x")` 반환, 테스트 끝에서 `DROP TABLE` |
| T-2 | 같은 상태에서 `check_schema(engine, metadata)` | `RuntimeError`, 메시지에 `t_a`, `x`, `ck_t_a_x`, `docs/migrations/` 포함 |
| T-3 | 모델과 완전히 같은 DB(`Base.metadata.create_all` 직후, 실제 앱 모델 전체) | 빈 목록, `check_schema`가 예외 없이 끝남(실제 모델과의 일치 회귀 방지) |
| T-4 | DB에 여분 컬럼·여분 테이블이 있음 | 무시(빈 목록) |
| T-5 | CHECK 식이 모델과 다르지만 이름은 같음 | 통과(D-4를 고정하는 테스트) |
| T-6 | 이름 없는 `CheckConstraint`가 모델에 있음 | 보고하지 않음 |
| T-7 | `SCHEMA_CHECK=off`/`OFF`/`0`/`false` + 차이 있음 | 예외 없음, 경고 로그 1건(`caplog`). 값이 없거나 `on`이면 검사 수행 |
| T-8 | 테이블 자체가 없음(임시 `MetaData`에만 있는 테이블) | `Drift(kind="table")` |
| T-9 | 메시지 형식 단위 테스트(`format_drift_message`, DB 불필요) | 테이블별 묶음, 정렬 결정적 |

lifespan 통합(T-10): `lifespan`을 직접 구동하는 테스트는 개발 DB를 건드리므로 만들지 않는다. 대신 `main.lifespan`이 `check_schema`를 `create_all` 뒤·`seed_admin` 앞에서 부르는지는 `monkeypatch`로 순서를 기록하는 단위 테스트로 확인하되, 엔진은 가짜로 대체한다(구현자가 비용 대비 판단, 생략 시 보고).

완료 게이트는 `backend-invariants` §7 그대로: `check_layers.py` 위반 0, `import main` 성공, `uv run pytest -rs` failed 0·db 마커 skip 0.

## 10. 질문 목록과 임시 기본값

| # | 확인 필요 항목 | 출처 | 임시 기본값 | 근거 |
| --- | --- | --- | --- | --- |
| Q-1 | 끄는 환경변수 이름과 기본값 | 사용자 위임 | `SCHEMA_CHECK`, 기본 켜짐, `off`·`0`·`false`로 끔 | 팀원이 일시적으로 막힐 때 우회 수단이 있어야 하고, 기본은 사고 방지 |
| Q-2 | 검사 시점이 `seed_admin` 앞인가 | 설계 | 앞 | 빠진 컬럼 때문에 seed가 먼저 터지면 원인 모를 오류가 되기 때문 |
| Q-3 | 마이그레이션 파일 이름 규칙·실행 방법 | 설계 | `YYYY-MM-DD_<PR>_<내용>.sql`, `psql < 파일` | 사용자 지시(날짜별 파일), 재실행 안전 |
| Q-4 | 새 컬럼을 추가하는 PR이 `docs/migrations/` 파일을 함께 넣도록 팀 규칙 추가 | 설계 | 제안만. 규칙화 여부는 사용자 결정 | 안 넣으면 시작이 막혀도 안내할 SQL이 없다 |
| Q-5 | 값 목록만 바뀐 CHECK(이름 동일)는 감지 못함 | D-4 | 감지하지 않음. 파일 안내와 PR 본문으로 공지 | 식 비교는 오탐 위험(D-4) |

## 11. 정합 이슈 (C)

| # | 내용 | 처리 |
| --- | --- | --- |
| C-1 | `layer-implementation` §7은 `main.py` 수정을 "두 줄"로 제한한다. 이번 변경은 import와 호출 각 1줄이라 이 범위를 넘는다 | 8절에 범위 확장 표시. 사용자 승인 필요 |
| C-2 | 이름만 비교하므로 CHECK 식이 바뀐 PR(예: `ck_point_log_type`에 `EXPIRE` 추가)은 이미 이름이 있는 팀원 DB에서 감지되지 않는다. 그 값을 쓰는 순간 CHECK 위반 500이 난다 | 한계로 문서화. 값 목록을 바꾸는 PR은 이름을 새로 붙여(예: `ck_point_log_type_v2`) 감지시키는 방법이 있으나 모델 이름 변경이 필요해 사용자 결정(Q-5) |
| C-3 | 이 검사는 마이그레이션 파일이 최신이라는 것을 강제하지 않는다 | Q-4 |
| C-4 | `password_reset_codes`는 #30이 `create_all`로 만들게 했으나, #45 이후 `ck_password_reset_attempts_nonneg`가 이름 있는 CHECK로 추가돼 있다. 그 전에 만든 옛 테이블이라면 이 CHECK 이름이 없어 검사가 잡는다 | 5절 #30 파일에 이 제약 추가 DO 블록을 포함(`IF NOT EXISTS`) |
| C-5 | `payments.md`가 만든 인라인 CHECK(이름 자동 `payments_point_used_check`)와 모델의 `ck_payments_point_used`가 이름이 다르다. 즉 `ALTER ... CHECK (point_used >= 0)`로 만든 DB는 이 검사에서 "CHECK 누락"으로 잡힌다 | 5절 #29 파일이 이름 있는 제약을 추가해 해소. 팀원 DB에는 CHECK가 중복으로 남지만 무해 |
| C-6 | 모델에 없는 컬럼이 `schema.sql`에 있다(`price` 등, `models.py` 주석 S-3). 검사는 모델 기준이라 영향 없음 | 변경 없음 |

C-2·C-5는 `create_all`로 처음부터 만든 DB와 수동 ALTER로 맞춘 DB의 제약 이름이 달라질 수 있다는 같은 원인이다. 구현 후 실제 로컬 DB(옛 상태)로 오탐이 없는지 사용자가 한 번 확인하는 것을 권장한다.
