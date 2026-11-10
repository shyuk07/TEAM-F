"""서버 시작 시 DB 스키마 검사 (../docs/design/schema-check.md).

모델(`Base.metadata`)에 있는데 DB에 없는 컬럼과 이름 있는 CHECK를 찾아 알린다.
DB는 바꾸지 않는다(읽기 전용). 타입·NULL·인덱스·FK, CHECK 식은 비교하지 않는다(D-4, D-5).
"""

import logging
import os
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import CheckConstraint, MetaData, inspect
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from database import Base

MIGRATIONS_DIR = "../docs/migrations/"  # D-11: 안내 문구는 이 상수 한 곳
MIGRATIONS_HINT = (
    f"{MIGRATIONS_DIR} 의 SQL을 파일명 순서대로 실행하세요. "
    "이미 반영된 항목은 건너뛰도록 작성돼 있어 다시 실행해도 안전합니다.\n"
    f"예) docker compose exec -T postgres psql -U lastcall -d lastcall < {MIGRATIONS_DIR}<파일>.sql\n"
    "검사를 끄려면 SCHEMA_CHECK=off (권장하지 않음)"
)

_OFF_VALUES = {"off", "0", "false"}


@dataclass(frozen=True)
class Drift:
    table: str
    kind: str  # "table" | "column" | "check"
    name: str  # 테이블이면 테이블명과 같음


def find_schema_drift(connection: Connection, metadata: MetaData) -> list[Drift]:
    """모델에는 있고 DB에는 없는 테이블·컬럼·이름 있는 CHECK를 모은다(읽기 전용)."""
    insp = inspect(connection)
    existing = set(insp.get_table_names())
    drifts: list[Drift] = []
    for table in metadata.sorted_tables:
        if table.name not in existing:
            drifts.append(Drift(table.name, "table", table.name))
            continue
        have = {c["name"] for c in insp.get_columns(table.name)}
        drifts.extend(
            Drift(table.name, "column", c.name) for c in table.columns if c.name not in have
        )
        have_ck = {
            c["name"] for c in insp.get_check_constraints(table.name) if c.get("name")
        }
        drifts.extend(
            Drift(table.name, "check", str(con.name))
            for con in table.constraints
            if isinstance(con, CheckConstraint) and con.name and str(con.name) not in have_ck
        )
    return drifts


def format_drift_message(drifts: list[Drift]) -> str:
    lines = ["DB 스키마가 모델과 맞지 않습니다. 서버를 시작하지 않습니다 (DB는 자동으로 바꾸지 않습니다)."]
    tables: list[str] = []
    for d in drifts:
        if d.table not in tables:
            tables.append(d.table)
    for table in tables:
        mine = [d for d in drifts if d.table == table]
        if any(d.kind == "table" for d in mine):
            lines.append(f"  - {table}: 테이블 없음")
            continue
        columns = [d.name for d in mine if d.kind == "column"]
        if columns:
            lines.append(f"  - {table}: 컬럼 {', '.join(columns)}")
        lines.extend(f"  - {table}: CHECK {d.name}" for d in mine if d.kind == "check")
    lines.append(MIGRATIONS_HINT)
    return "\n".join(lines)


def schema_check_enabled(env: Mapping[str, str] | None = None) -> bool:
    """SCHEMA_CHECK가 off/0/false(대소문자 무시)일 때만 끈다. 그 외는 켜짐(D-8)."""
    source = os.environ if env is None else env
    return source.get("SCHEMA_CHECK", "").strip().lower() not in _OFF_VALUES


async def check_schema(engine: AsyncEngine, metadata: MetaData = Base.metadata) -> None:
    if not schema_check_enabled():
        logging.getLogger(__name__).warning("SCHEMA_CHECK=off: DB 스키마 검사를 건너뜁니다.")
        return
    async with engine.connect() as connection:
        drifts = await connection.run_sync(find_schema_drift, metadata)
    if drifts:
        raise RuntimeError(format_drift_message(drifts))
