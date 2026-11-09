"""관리자 회원 목록 DB 테스트 (T-D2~T-D4). T-D3: SQL 상태 필터와 User.effective_status 대조."""

import itertools
from datetime import datetime, timedelta, timezone

import pytest

from auth.domain.user import Role, User, UserStatus
from auth.domain.user_search import UserSearchCriteria
from auth.infrastructure.repositories import SqlAlchemyUserRepository

pytestmark = [pytest.mark.db, pytest.mark.anyio]

NOW = datetime(2026, 11, 9, 12, 0, tzinfo=timezone.utc)
ALL = UserSearchCriteria()


def build(email, role=Role.CUSTOMER, status=UserStatus.APPROVED, until=None, created=None):
    extra = {}
    if status is UserStatus.SUSPENDED:
        extra = dict(suspended_reason="r", suspended_at=NOW - timedelta(days=2))
    elif status is UserStatus.REJECTED:
        extra = dict(rejected_reason="r", rejected_at=NOW - timedelta(days=2))
    elif status is UserStatus.WITHDRAWN:
        extra = dict(deleted_reason="r", deleted_at=NOW - timedelta(days=2))
    return User(email=email, password_hash="h", role=role, name="n", phone="010", status=status,
                suspended_until=until, created_at=created or NOW - timedelta(days=1), **extra)


async def seed(client, users):
    async with client.session_factory() as s:
        repo = SqlAlchemyUserRepository(s)
        saved = [await repo.save(u) for u in users]
        await s.commit()
        return saved


async def page(client, criteria, offset=0, limit=100):
    async with client.session_factory() as s:
        repo = SqlAlchemyUserRepository(s)
        rows = await repo.find_page(criteria, now=NOW, offset=offset, limit=limit)
        total = await repo.count_matching(criteria, now=NOW)
        return rows, total


async def test_filters_total_order_paging(client):
    created = [NOW - timedelta(hours=i) for i in (5, 5, 4, 3, 2)]  # 앞 둘은 같은 created_at
    users = [build(f"u{i}@x.com", role=Role.OWNER if i % 2 else Role.CUSTOMER, created=c)
             for i, c in enumerate(created)]
    users.append(build("w@x.com", status=UserStatus.WITHDRAWN))
    await seed(client, users)

    rows, total = await page(client, ALL)
    assert total == 6 and any(u.status is UserStatus.WITHDRAWN for u in rows)  # 탈퇴 포함
    keys = [(u.created_at, u.id) for u in rows]
    assert keys == sorted(keys, reverse=True)

    p1, _ = await page(client, ALL, 0, 4)
    p2, t2 = await page(client, ALL, 4, 4)
    assert len(p1) == 4 and len(p2) == 2 and t2 == 6
    assert {u.id for u in p1}.isdisjoint({u.id for u in p2})
    assert {u.id for u in p1 + p2} == {u.id for u in rows}

    empty, t3 = await page(client, ALL, 100, 10)
    assert empty == [] and t3 == 6

    owners, to = await page(client, UserSearchCriteria.of(Role.OWNER, None, None))
    assert to == 2 and all(u.role is Role.OWNER for u in owners)
    w, tw = await page(client, UserSearchCriteria.of(None, UserStatus.WITHDRAWN, None))
    assert tw == 1 and w[0].email == "w@x.com"


async def test_status_filter_matches_effective_status(client):
    """T-D3: 상태 5종 x 정지 만료 4가지(없음/과거/==now/미래)의 모든 조합."""
    untils = [None, NOW - timedelta(days=1), NOW, NOW + timedelta(days=1)]
    users = [
        build(f"{st.value.lower()}{i}@x.com", status=st, until=u,
              role=Role.OWNER if st in (UserStatus.PENDING, UserStatus.REJECTED) else Role.CUSTOMER)
        for (st, (i, u)) in itertools.product(UserStatus, enumerate(untils))
        if st is UserStatus.SUSPENDED or u is None
    ]
    assert len(users) == 8
    saved = await seed(client, users)
    for status in UserStatus:
        expected = {u.id for u in saved if u.effective_status(NOW) == status}
        rows, total = await page(client, UserSearchCriteria.of(None, status, None))
        assert {u.id for u in rows} == expected, status
        assert total == len(expected), status
    # 표본 sanity: 정지 4건 중 SUSPENDED는 None/미래 2건만
    rows, _ = await page(client, UserSearchCriteria.of(None, UserStatus.SUSPENDED, None))
    assert len(rows) == 2


async def test_email_search(client):
    await seed(client, [build("abc@x.com"), build("axb@x.com"), build("a_b@y.org"),
                        build("p%q@x.com", role=Role.OWNER), build("zzz@gmail.com")])
    async def emails(c):
        rows, total = await page(client, c)
        assert total == len(rows)
        return sorted(u.email for u in rows)

    assert await emails(UserSearchCriteria.of(None, None, "ABC")) == ["abc@x.com"]
    assert await emails(UserSearchCriteria.of(None, None, "@gmail.com")) == ["zzz@gmail.com"]
    assert await emails(UserSearchCriteria.of(None, None, "x.com")) == ["abc@x.com", "axb@x.com", "p%q@x.com"]
    assert await emails(UserSearchCriteria.of(None, None, "a_b")) == ["a_b@y.org"]
    assert await emails(UserSearchCriteria.of(None, None, "%")) == ["p%q@x.com"]
    assert await emails(UserSearchCriteria.of(Role.OWNER, None, "x.com")) == ["p%q@x.com"]


async def test_endpoint_with_real_db(client):
    from tests.helpers import bearer, login, signup

    await signup(client, "adm@test.com")
    async with client.session_factory() as s:
        from sqlalchemy import text
        await s.execute(text("UPDATE users SET role='ADMIN' WHERE email='adm@test.com'"))
        await s.commit()
    token = (await login(client, "adm@test.com")).json()["access_token"]
    r = await client.get("/v1/admin/users?email=ADM%25&size=5", headers=bearer(token))
    assert r.status_code == 200 and r.json()["total_elements"] == 0
    r = await client.get("/v1/admin/users?email=ADM", headers=bearer(token))
    assert r.json()["total_elements"] == 1 and r.json()["users"][0]["role"] == "ADMIN"
