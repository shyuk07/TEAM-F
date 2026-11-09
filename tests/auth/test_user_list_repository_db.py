"""회원 목록 레포지토리 DB 테스트 (auth 설계 §18.6)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from auth.domain.user import Role, User, UserStatus
from auth.domain.user_list_query import UserListQuery
from auth.infrastructure.repositories import SqlAlchemyUserRepository

pytestmark = [pytest.mark.db, pytest.mark.anyio]

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
BASE = NOW - timedelta(days=30)


def user(email, role=Role.CUSTOMER, status=UserStatus.APPROVED, until=None, minutes=0, uid=None):
    extra = {}
    if status is UserStatus.SUSPENDED:
        extra = dict(suspended_reason="r", suspended_at=NOW - timedelta(days=3), suspended_until=until)
    if status is UserStatus.WITHDRAWN:
        extra = dict(deleted_at=NOW - timedelta(days=1), deleted_reason="r")
    if status is UserStatus.REJECTED:
        extra = dict(rejected_reason="r", rejected_at=NOW - timedelta(days=1))
    return User(
        email=email, password_hash="h", role=role, name="n", phone="010",
        created_at=BASE + timedelta(minutes=minutes), status=status, id=uid, **extra,
    )


def make_seed() -> list[User]:
    """save가 user.id를 바꾸므로 호출마다 새 객체를 만든다."""
    return [
        user("customer@t.com", minutes=1),
        user("owner.pending@t.com", Role.OWNER, UserStatus.PENDING, minutes=2),
        user("owner.approved@t.com", Role.OWNER, minutes=3),
        user("owner.rejected@t.com", Role.OWNER, UserStatus.REJECTED, minutes=4),
        user("susp.forever@t.com", status=UserStatus.SUSPENDED, until=None, minutes=5),
        user("susp.active@t.com", status=UserStatus.SUSPENDED, until=NOW + timedelta(seconds=1), minutes=6),
        user("susp.past@t.com", status=UserStatus.SUSPENDED, until=NOW - timedelta(days=1), minutes=7),
        user("susp.exact@t.com", status=UserStatus.SUSPENDED, until=NOW, minutes=8),
        user("admin@t.com", Role.ADMIN, minutes=9),
        user("gone@t.com", status=UserStatus.WITHDRAWN, minutes=10),
        user("pct%sign@t.com", minutes=11),
        user("under_score@t.com", minutes=12),
        user("underXscore@t.com", minutes=13),
        user("a/b@t.com", minutes=14),
        user("back\\slash@t.com", minutes=15),
    ]


@pytest.fixture
async def repo(session_factory):
    async with session_factory() as s:
        await s.execute(text("DELETE FROM users"))
        r = SqlAlchemyUserRepository(s)
        for u in make_seed():
            await r.save(u)
        await s.commit()
    async with session_factory() as s:
        yield SqlAlchemyUserRepository(s)


async def emails(repo, **kw):
    q = UserListQuery.create(size=100, **kw)
    return [u.email for u in await repo.find_all(q, NOW)]


async def test_order_created_at_then_id(session_factory):
    # 같은 created_at 행 30개: ORDER BY id가 없으면 무작위 UUID가 정렬돼 나올 확률은 1/30!
    same = BASE + timedelta(days=-5)
    async with session_factory() as s:
        await s.execute(text("DELETE FROM users"))
        r = SqlAlchemyUserRepository(s)
        for i in range(30):
            u = user(f"same{i}@t.com")
            u.created_at = same
            await r.save(u)
        await s.commit()
    async with session_factory() as s:
        r = SqlAlchemyUserRepository(s)
        got = await r.find_all(UserListQuery.create(size=100), NOW)
        assert len(got) == 30
        assert [u.id for u in got] == sorted(u.id for u in got)


async def test_order_ascending(repo):
    got = await emails(repo)
    assert got == [u.email for u in make_seed()]


async def test_role_filter(repo):
    assert set(await emails(repo, role="ADMIN")) == {"admin@t.com"}
    assert len(await emails(repo, role="OWNER")) == 3


async def test_email_case_insensitive(repo):
    # 이메일은 소문자로 저장된다(User.normalize_email). 대문자 검색어가 찾아야 한다.
    assert await emails(repo, email="OWNER.PENDING") == ["owner.pending@t.com"]
    assert await emails(repo, email="Owner.Pending@T.com") == ["owner.pending@t.com"]


async def test_wildcards_literal(repo):
    assert await emails(repo, email="%") == ["pct%sign@t.com"]
    assert await emails(repo, email="under_score") == ["under_score@t.com"]
    assert await emails(repo, email="a/b") == ["a/b@t.com"]
    assert await emails(repo, email="back\\slash") == ["back\\slash@t.com"]


async def test_combined_filters(repo):
    assert await emails(repo, role="OWNER", status="APPROVED", email="owner") == ["owner.approved@t.com"]


async def test_paging_and_count(repo):
    total = len(make_seed())
    p1 = await repo.find_all(UserListQuery.create(page=1, size=10), NOW)
    p2 = await repo.find_all(UserListQuery.create(page=2, size=10), NOW)
    p3 = await repo.find_all(UserListQuery.create(page=3, size=10), NOW)
    assert (len(p1), len(p2), p3) == (10, total - 10, [])
    assert await repo.count_all(UserListQuery.create(page=3, size=1), NOW) == total


async def test_status_consistency_with_domain(repo):
    everyone = await repo.find_all(UserListQuery.create(size=100), NOW)
    for s in UserStatus:
        expected = {u.id for u in everyone if u.effective_status(NOW) is s}
        got = await repo.find_all(UserListQuery.create(status=s.value, size=100), NOW)
        assert {u.id for u in got} == expected, s
        assert await repo.count_all(UserListQuery.create(status=s.value), NOW) == len(expected)
    # 경계: until == now 는 APPROVED, 직전은 SUSPENDED
    approved = await emails(repo, status="APPROVED")
    suspended = await emails(repo, status="SUSPENDED")
    assert "susp.exact@t.com" in approved and "susp.past@t.com" in approved
    assert "susp.active@t.com" in suspended and "susp.forever@t.com" in suspended


async def test_withdrawn_included(repo):
    assert "gone@t.com" in await emails(repo)
    assert await emails(repo, status="WITHDRAWN") == ["gone@t.com"]


async def test_returns_domain_objects(repo):
    got = await repo.find_all(UserListQuery.create(), NOW)
    assert got and all(isinstance(u, User) for u in got)
