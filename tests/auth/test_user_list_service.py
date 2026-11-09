import dataclasses
import uuid
from datetime import timedelta

import pytest

from auth.application.service import UserPage, UserSummary
from auth.domain.exceptions import InvalidPageError, InvalidUserFilterError
from auth.domain.user import Role, User, UserStatus
from tests.auth.fakes import T0
from tests.auth.test_service import FakeUsers, build

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class RecordingUsers(FakeUsers):
    def __init__(self, rows=None):
        super().__init__()
        self.rows = rows or []
        self.find_calls = []
        self.count_calls = []

    async def find_all(self, query, now):
        self.find_calls.append((query, now))
        return self.rows

    async def count_all(self, query, now):
        self.count_calls.append((query, now))
        return len(self.rows) + 5


def make_user(email, status=UserStatus.APPROVED, until=None, role=Role.CUSTOMER):
    extra = {}
    if status is UserStatus.SUSPENDED:
        extra = dict(suspended_reason="r", suspended_at=T0 - timedelta(days=2), suspended_until=until)
    return User(
        email=email, password_hash="h", role=role, name="n", phone="010", id=uuid.uuid4(),
        created_at=T0 - timedelta(days=1), status=status, **extra,
    )


def svc_with(rows=None):
    svc, db, parts = build()
    repo = RecordingUsers(rows)
    svc.users = repo
    return svc, db, repo


async def test_filters_pass_through_vo():
    svc, _, repo = svc_with()
    page = await svc.list_users(role="OWNER", status="PENDING", email=" a ", page=2, size=10)
    q, _ = repo.find_calls[0]
    assert (q.role, q.status, q.email, q.page, q.size) == (Role.OWNER, UserStatus.PENDING, "a", 2, 10)
    assert repo.count_calls[0][0] == q
    assert (page.page, page.size) == (2, 10)


async def test_same_now_for_both_calls():
    svc, _, repo = svc_with()
    await svc.list_users()
    assert repo.find_calls[0][1] == repo.count_calls[0][1] == T0


@pytest.mark.parametrize("kwargs,exc", [
    (dict(page=0), InvalidPageError),
    (dict(size=101), InvalidPageError),
    (dict(role="x"), InvalidUserFilterError),
    (dict(status="x"), InvalidUserFilterError),
    (dict(email="a" * 256), InvalidUserFilterError),
])
async def test_invalid_input_never_hits_repo(kwargs, exc):
    svc, _, repo = svc_with()
    with pytest.raises(exc):
        await svc.list_users(**kwargs)
    assert repo.find_calls == [] and repo.count_calls == []


async def test_effective_status_in_items():
    rows = [
        make_user("expired@t.com", UserStatus.SUSPENDED, T0 - timedelta(seconds=1)),
        make_user("boundary@t.com", UserStatus.SUSPENDED, T0),
        make_user("future@t.com", UserStatus.SUSPENDED, T0 + timedelta(days=1)),
        make_user("forever@t.com", UserStatus.SUSPENDED, None),
        make_user("pending@t.com", UserStatus.PENDING, role=Role.OWNER),
    ]
    svc, _, _ = svc_with(rows)
    page = await svc.list_users()
    assert [i.status for i in page.items] == ["APPROVED", "APPROVED", "SUSPENDED", "SUSPENDED", "PENDING"]
    assert page.items[4].role == "OWNER"


async def test_summary_fields_fixed_and_no_sensitive():
    names = {f.name for f in dataclasses.fields(UserSummary)}
    assert names == {"id", "email", "name", "role", "status", "created_at"}
    assert {f.name for f in dataclasses.fields(UserPage)} == {"items", "page", "size", "total"}


async def test_total_and_echo_and_no_commit():
    rows = [make_user("a@t.com"), make_user("b@t.com")]
    svc, db, _ = svc_with(rows)
    page = await svc.list_users(page=1, size=2)
    assert page.total == 7 and len(page.items) == 2 and (page.page, page.size) == (1, 2)
    assert db.commits == 0 and db.rollbacks == 0


async def test_empty_result():
    svc, _, _ = svc_with([])
    page = await svc.list_users()
    assert page.items == [] and page.total == 5  # fake count은 len+5
