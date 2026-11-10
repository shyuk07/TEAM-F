"""서버 시작 시 스키마 검사 (../docs/design/schema-check.md 9절).

DB 테스트는 session_factory(lastcall_test, 앱 테이블 create_all 완료 상태)의 엔진을 쓰고,
임시 MetaData의 t_sc_* 테이블만 만들고 지운다.
"""

import logging

import pytest
from sqlalchemy import CheckConstraint, Column, Integer, MetaData, Table, text

import main
import schema_check
from database import Base
from schema_check import (
    Drift,
    check_schema,
    find_schema_drift,
    format_drift_message,
    schema_check_enabled,
)

pytestmark = pytest.mark.anyio


def _metadata(table="t_sc_a", with_unnamed=False):
    md = MetaData()
    cols = [Column("id", Integer, primary_key=True), Column("x", Integer)]
    cons = [CheckConstraint("x >= 0", name=f"ck_{table}_x")]
    if with_unnamed:
        cons.append(CheckConstraint("x < 1000000"))
    Table(table, md, *cols, *cons)
    return md


@pytest.fixture
async def engine(session_factory):
    eng = session_factory.kw["bind"]
    yield eng
    async with eng.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS t_sc_a"))


async def _create_old_table(eng):
    async with eng.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS t_sc_a"))
        await conn.execute(text("CREATE TABLE t_sc_a (id INTEGER PRIMARY KEY)"))


async def _drift(eng, md):
    async with eng.connect() as conn:
        return await conn.run_sync(find_schema_drift, md)


async def test_missing_column_and_check_are_reported(engine):
    await _create_old_table(engine)
    drifts = await _drift(engine, _metadata())
    assert drifts == [Drift("t_sc_a", "column", "x"), Drift("t_sc_a", "check", "ck_t_sc_a_x")]


async def test_check_schema_raises_with_details(engine):
    await _create_old_table(engine)
    with pytest.raises(RuntimeError) as exc:
        await check_schema(engine, _metadata())
    message = str(exc.value)
    for expected in ("t_sc_a", "x", "ck_t_sc_a_x", "../docs/migrations/"):
        assert expected in message


async def test_real_models_match_created_db(engine):
    assert await _drift(engine, Base.metadata) == []
    await check_schema(engine)


async def test_extra_columns_and_tables_are_ignored(engine):
    async with engine.begin() as conn:
        await conn.execute(
            text("CREATE TABLE t_sc_a (id INTEGER PRIMARY KEY, x INTEGER, extra INTEGER)")
        )
        await conn.execute(text("ALTER TABLE t_sc_a ADD CONSTRAINT ck_t_sc_a_x CHECK (x >= 0)"))
    assert await _drift(engine, _metadata()) == []
    # t_sc_a는 DB에만 있는 테이블일 때도 무시
    assert await _drift(engine, MetaData()) == []


async def test_check_with_different_expression_but_same_name_passes(engine):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE t_sc_a (id INTEGER PRIMARY KEY, x INTEGER)"))
        await conn.execute(text("ALTER TABLE t_sc_a ADD CONSTRAINT ck_t_sc_a_x CHECK (x <> 7)"))
    assert await _drift(engine, _metadata()) == []


async def test_unnamed_check_is_not_reported(engine):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE t_sc_a (id INTEGER PRIMARY KEY, x INTEGER)"))
        await conn.execute(text("ALTER TABLE t_sc_a ADD CONSTRAINT ck_t_sc_a_x CHECK (x >= 0)"))
    assert await _drift(engine, _metadata(with_unnamed=True)) == []


async def test_missing_table_is_reported(engine):
    drifts = await _drift(engine, _metadata())
    assert drifts == [Drift("t_sc_a", "table", "t_sc_a")]


@pytest.mark.parametrize("value", ["off", "OFF", "0", "false", "False"])
async def test_env_off_skips_with_warning(engine, monkeypatch, caplog, value):
    await _create_old_table(engine)
    monkeypatch.setenv("SCHEMA_CHECK", value)
    with caplog.at_level(logging.WARNING, logger="schema_check"):
        await check_schema(engine, _metadata())
    warnings = [r for r in caplog.records if r.name == "schema_check"]
    assert len(warnings) == 1


@pytest.mark.parametrize("value", [None, "on", "1", "weird"])
async def test_env_on_or_unset_still_checks(engine, monkeypatch, value):
    await _create_old_table(engine)
    if value is None:
        monkeypatch.delenv("SCHEMA_CHECK", raising=False)
    else:
        monkeypatch.setenv("SCHEMA_CHECK", value)
    with pytest.raises(RuntimeError):
        await check_schema(engine, _metadata())


def test_schema_check_enabled_with_explicit_env():
    assert schema_check_enabled({}) is True
    assert schema_check_enabled({"SCHEMA_CHECK": " Off "}) is False


def test_format_message_groups_by_table_in_stable_order():
    drifts = [
        Drift("users", "column", "failed_login_count"),
        Drift("users", "column", "login_locked_until"),
        Drift("users", "check", "ck_users_failed_login_nonneg"),
        Drift("pickup_reservations", "column", "cancelled_by"),
        Drift("gone", "table", "gone"),
    ]
    lines = format_drift_message(drifts).splitlines()
    assert lines[1:5] == [
        "  - users: 컬럼 failed_login_count, login_locked_until",
        "  - users: CHECK ck_users_failed_login_nonneg",
        "  - pickup_reservations: 컬럼 cancelled_by",
        "  - gone: 테이블 없음",
    ]
    assert schema_check.MIGRATIONS_DIR in lines[5]
    assert format_drift_message(drifts) == format_drift_message(drifts)


async def test_lifespan_checks_between_create_all_and_seed_admin(monkeypatch):
    """lifespan 순서만 확인한다. 엔진·검사·시드는 가짜라 DB를 건드리지 않는다."""
    calls = []

    class FakeConn:
        async def run_sync(self, fn):
            calls.append("create_all")

    class FakeBegin:
        async def __aenter__(self):
            return FakeConn()

        async def __aexit__(self, *exc):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

        async def dispose(self):
            calls.append("dispose")

    async def fake_check(engine):
        calls.append("check_schema")

    async def fake_seed():
        calls.append("seed_admin")

    monkeypatch.setattr(main, "engine", FakeEngine())
    monkeypatch.setattr(main, "check_schema", fake_check)
    monkeypatch.setattr(main, "seed_admin", fake_seed)
    async with main.lifespan(main.app):
        assert calls == ["create_all", "check_schema", "seed_admin"]
