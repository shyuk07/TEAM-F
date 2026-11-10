import dataclasses

import pytest

from auth.domain.exceptions import InvalidPageError, InvalidUserFilterError
from auth.domain.user import Role, UserStatus
from auth.domain.user_list_query import UserListQuery


def test_defaults():
    q = UserListQuery.create()
    assert (q.page, q.size, q.role, q.status, q.email) == (1, 20, None, None, None)
    assert q.offset == 0


def test_offset():
    assert UserListQuery.create(page=3, size=10).offset == 20


@pytest.mark.parametrize("page,size", [(0, 20), (-1, 20), (1, 0), (1, 101), (1, -5)])
def test_invalid_page(page, size):
    with pytest.raises(InvalidPageError):
        UserListQuery.create(page=page, size=size)


@pytest.mark.parametrize("size", [1, 100])
def test_size_bounds_ok(size):
    assert UserListQuery.create(size=size).size == size


def test_bool_and_non_int_rejected():
    with pytest.raises(InvalidPageError):
        UserListQuery.create(page=True)
    with pytest.raises(InvalidPageError):
        UserListQuery.create(size=True)
    with pytest.raises(InvalidPageError):
        UserListQuery.create(page="1")  # type: ignore[arg-type]


def test_role_status_uppercase_ok():
    q = UserListQuery.create(role="OWNER", status="PENDING")
    assert q.role is Role.OWNER and q.status is UserStatus.PENDING


@pytest.mark.parametrize("field,value", [("role", "owner"), ("role", "X"), ("status", "approved"), ("status", "X")])
def test_invalid_enum_filter(field, value):
    with pytest.raises(InvalidUserFilterError):
        UserListQuery.create(**{field: value})


def test_error_messages_list_all_members():
    with pytest.raises(InvalidUserFilterError) as e:
        UserListQuery.create(role="x")
    assert all(r.value in str(e.value) for r in Role)
    with pytest.raises(InvalidUserFilterError) as e:
        UserListQuery.create(status="x")
    assert all(s.value in str(e.value) for s in UserStatus)


def test_error_code_is_validation_error():
    assert InvalidUserFilterError.error_code == "VALIDATION_ERROR"
    assert InvalidPageError.error_code == "INVALID_PAGE"


def test_blank_values_mean_no_filter():
    q = UserListQuery.create(role="  ", status="", email="   ")
    assert q.role is None and q.status is None and q.email is None


def test_strip():
    q = UserListQuery.create(role=" OWNER ", status=" APPROVED ", email="  a@b  ")
    assert q.role is Role.OWNER and q.status is UserStatus.APPROVED and q.email == "a@b"


def test_email_length():
    assert UserListQuery.create(email="a" * 255).email == "a" * 255
    with pytest.raises(InvalidUserFilterError):
        UserListQuery.create(email="a" * 256)


def test_validation_order_page_first():
    with pytest.raises(InvalidPageError):
        UserListQuery.create(page=0, role="bad", status="bad", email="a" * 300)


def test_validation_order_role_before_status_and_email():
    with pytest.raises(InvalidUserFilterError, match="role"):
        UserListQuery.create(role="bad", status="bad", email="a" * 300)
    with pytest.raises(InvalidUserFilterError, match="status"):
        UserListQuery.create(status="bad", email="a" * 300)


def test_wildcards_preserved_and_case_kept():
    assert UserListQuery.create(email="A%b_c").email == "A%b_c"


def test_frozen():
    q = UserListQuery.create()
    with pytest.raises(dataclasses.FrozenInstanceError):
        q.page = 2  # type: ignore[misc]
