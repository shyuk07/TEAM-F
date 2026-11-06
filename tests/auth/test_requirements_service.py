"""auth 요구조건 정합(§15) 서비스 테스트: 재설정·탈퇴 조정·프로필·비밀번호·소멸 (fake 주입, DB 없음)."""

import inspect
import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest

from auth.application.password_reset_service import PasswordResetService
from auth.application.service import AuthApplicationService
from auth.application.withdrawal_service import AccountWithdrawalService
from auth.domain.exceptions import (
    AdminAccountProtectedError,
    CurrentPasswordMismatchError,
    InvalidResetCodeError,
    TokenRevokedError,
    UserWithdrawnError,
)
from auth.domain.password_reset_code import PasswordResetCode
from auth.domain.point_log import PointType
from auth.domain.repository.password_reset_code_repository import PasswordResetCodeRepository
from auth.domain.service import PasswordResetNotifier, ResetCodeGenerator
from auth.domain.user import POINT_MAX_BALANCE, SELF_WITHDRAWAL_REASON, UserStatus
from tests.auth.fakes import T0
from tests.auth.test_service import build

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def signed_up(svc, email="a@b.com", role="CUSTOMER"):
    return await svc.signup(email, "password1", role, name="n", phone="010")


# ── 프로필·비밀번호 ──
async def test_update_profile_commits_once():
    svc, db, _ = build()
    u = await signed_up(svc)
    db.commits = 0
    got = await svc.update_profile(u.id, "새이름", None)
    assert got.name == "새이름" and db.commits == 1


async def test_change_password_then_authenticate_tokens():
    svc, db, parts = build()
    u = await signed_up(svc)
    t1 = (await svc.login("a@b.com", "password1")).token
    t2 = (await svc.login("a@b.com", "password1")).token
    claims1 = parts["tokens"].decode(t1)
    db.commits = 0
    await svc.change_password(u.id, "password1", "newpassword1", keep_jti=claims1.jti)
    assert db.commits == 1
    await svc.authenticate(t1)  # 변경에 쓴 토큰은 유지
    with pytest.raises(TokenRevokedError):
        await svc.authenticate(t2)  # 다른 토큰은 무효
    t3 = (await svc.login("a@b.com", "newpassword1")).token  # 변경 뒤 새 로그인 토큰 유효
    await svc.authenticate(t3)


async def test_change_password_wrong_current_does_not_commit():
    svc, db, _ = build()
    u = await signed_up(svc)
    db.commits = 0
    with pytest.raises(CurrentPasswordMismatchError):
        await svc.change_password(u.id, "wrong", "newpassword1", keep_jti="j")
    assert db.commits == 0


async def test_login_issues_token_with_user_version():
    svc, _, parts = build()
    u = await signed_up(svc)
    u.invalidate_tokens()
    claims = parts["tokens"].decode((await svc.login("a@b.com", "password1")).token)
    assert claims.token_version == 1


async def test_legacy_token_without_ver_claim_is_version_zero():
    import jwt

    svc, _, parts = build()
    u = await signed_up(svc)
    payload = {"sub": str(u.id), "role": "CUSTOMER", "jti": "x", "exp": int((T0 + timedelta(days=9999)).timestamp())}
    token = jwt.encode(payload, "k" * 40, algorithm="HS256")
    assert parts["tokens"].decode(token).token_version == 0
    await svc.authenticate(token)  # 세대 0 회원은 통과


async def test_check_self_withdrawable_is_read_only():
    svc, db, _ = build()
    u = await signed_up(svc)
    db.commits = 0
    assert (await svc.check_self_withdrawable(u.id, "password1")).id == u.id
    assert db.commits == 0
    with pytest.raises(CurrentPasswordMismatchError):
        await svc.check_self_withdrawable(u.id, "bad")


# ── 탈퇴 소멸 ──
async def test_withdraw_user_records_expire_log():
    svc, db, parts = build()
    u = await signed_up(svc)
    u.users_point = 700
    done = await svc.withdraw_user(u.id, "사유", now=T0)
    assert done.users_point == 0 and done.status is UserStatus.WITHDRAWN
    (log,) = parts["point_logs"].items
    assert (log.point_type, log.amount, log.balance_after) == (PointType.EXPIRE, -700, 0)


async def test_withdraw_user_zero_balance_no_log_and_commit_flag():
    svc, db, parts = build()
    u = await signed_up(svc)
    db.commits = 0
    await svc.withdraw_user(u.id, "사유", now=T0, commit=False)
    assert parts["point_logs"].items == [] and db.commits == 0


async def test_withdraw_admin_rejected_keeps_balance_and_no_log():
    svc, _, parts = build()
    admin, _ = await svc.ensure_admin("adm@b.com", "password1")
    admin.users_point = 50
    with pytest.raises(AdminAccountProtectedError):
        await svc.withdraw_user(admin.id, "사유", now=T0)
    assert admin.users_point == 50 and parts["point_logs"].items == []


async def test_earn_cap_and_withdrawn_via_service():
    svc, _, parts = build()
    u = await signed_up(svc)
    u.users_point = POINT_MAX_BALANCE
    with pytest.raises(ValueError):
        await svc.earn_points(u.id, 1)
    assert parts["point_logs"].items == []
    u.users_point = 0
    await svc.withdraw_user(u.id, "사유", now=T0)
    with pytest.raises(UserWithdrawnError):
        await svc.restore_points(u.id, 100)


def test_payments_facing_signatures_unchanged():
    """payments가 쓰는 메서드의 시그니처·commit 규약 고정 (C-22)."""
    for name in ("use_points", "earn_points", "restore_points", "revoke_points"):
        sig = inspect.signature(getattr(AuthApplicationService, name))
        params = list(sig.parameters.values())
        assert [p.name for p in params] == ["self", "user_id", "amount", "commit"]
        assert params[3].kind is inspect.Parameter.KEYWORD_ONLY and params[3].default is True
    init = list(inspect.signature(AuthApplicationService.__init__).parameters)
    assert init == ["self", "session", "users", "point_logs", "blacklist", "hasher", "tokens", "clock"]


# ── PasswordResetService ──
class FakeCodes(PasswordResetCodeRepository):
    def __init__(self):
        self.rows: dict[uuid.UUID, PasswordResetCode] = {}
        self.saves = 0

    async def find_by_user_id(self, user_id, for_update=False):
        row = self.rows.get(user_id)
        if row is None:
            return None
        return PasswordResetCode(
            row.user_id, row.code_hash, row.expires_at, row.failed_attempts, row.created_at
        )

    async def save(self, code):
        self.saves += 1
        self.rows[code.user_id] = PasswordResetCode(
            code.user_id, code.code_hash, code.expires_at, code.failed_attempts, code.created_at
        )
        return code

    async def delete(self, user_id):
        self.rows.pop(user_id, None)


class FixedGenerator(ResetCodeGenerator):
    def __init__(self, *codes):
        self.codes = list(codes)

    def generate(self):
        return self.codes.pop(0)


class RecordingNotifier(PasswordResetNotifier):
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_code(self, email, code, expires_at):
        self.sent.append((email, code, expires_at))
        if self.fail:
            raise RuntimeError("smtp down")


def make_reset(*codes, fail=False):
    svc, db, parts = build()
    codes_repo, notifier = FakeCodes(), RecordingNotifier(fail)
    reset = PasswordResetService(
        session=db,
        users=parts["users"],
        codes=codes_repo,
        hasher=parts["hasher"],
        generator=FixedGenerator(*codes),
        notifier=notifier,
        clock=parts["clock"],
    )
    return reset, svc, db, parts, codes_repo, notifier


async def test_request_registered_saves_hash_sends_once_commits_once():
    reset, svc, db, parts, codes, notifier = make_reset("123456")
    u = await signed_up(svc)
    db.commits = 0
    await reset.request_reset("A@B.com")
    assert db.commits == 1
    assert codes.rows[u.id].code_hash == "hashed:123456"  # 원문이 아닌 해시
    assert [(e, c) for e, c, _ in notifier.sent] == [("a@b.com", "123456")]
    assert notifier.sent[0][2] == T0 + timedelta(minutes=15)


async def test_request_unknown_or_withdrawn_does_nothing_but_dummy_verify():
    reset, svc, db, parts, codes, notifier = make_reset("111111")
    await reset.request_reset("nobody@b.com")
    u = await signed_up(svc)
    await svc.withdraw_user(u.id, "사유", now=T0)
    db.commits = 0
    await reset.request_reset("a@b.com")
    assert codes.rows == {} and notifier.sent == [] and db.commits == 0
    assert parts["hasher"].dummy_calls == 2


async def test_request_notifier_failure_is_swallowed_after_commit():
    reset, svc, db, _, codes, notifier = make_reset("123456", fail=True)
    u = await signed_up(svc)
    db.commits = 0
    await reset.request_reset("a@b.com")  # 예외 없음
    assert db.commits == 1 and u.id in codes.rows


async def test_rerequest_within_cooldown_keeps_existing_code_and_sends_nothing():
    reset, svc, db, parts, codes, notifier = make_reset("111111", "222222")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    parts["clock"].advance(seconds=59)
    db.commits = 0
    await reset.request_reset("a@b.com")  # 예외 없이 정상 반환(항상 204)
    assert db.commits == 0 and len(notifier.sent) == 1
    assert codes.rows[u.id].code_hash == "hashed:111111" and codes.rows[u.id].failed_attempts == 1
    await reset.confirm_reset("a@b.com", "111111", "newpassword1")  # 기존 코드 유효


async def test_rerequest_after_cooldown_invalidates_previous_code():
    reset, svc, db, parts, codes, notifier = make_reset("111111", "222222")
    await signed_up(svc)
    await reset.request_reset("a@b.com")
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    parts["clock"].advance(seconds=60)
    await reset.request_reset("a@b.com")
    (row,) = codes.rows.values()
    assert row.failed_attempts == 0 and len(notifier.sent) == 2  # 새 코드는 0에서 시작
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "111111", "newpassword1")  # 이전 코드 무효
    await reset.confirm_reset("a@b.com", "222222", "newpassword1")


async def test_confirm_success_changes_password_revokes_tokens_deletes_code():
    reset, svc, db, parts, codes, _ = make_reset("123456")
    u = await signed_up(svc)
    old = (await svc.login("a@b.com", "password1")).token
    await reset.request_reset("a@b.com")
    db.commits = 0
    await reset.confirm_reset("a@b.com", "123456", "newpassword1")
    assert db.commits == 1 and codes.rows == {}
    assert u.password_hash == "hashed:newpassword1" and u.token_version == 1
    with pytest.raises(TokenRevokedError):
        await svc.authenticate(old)
    with pytest.raises(InvalidResetCodeError):  # 재사용 거부
        await reset.confirm_reset("a@b.com", "123456", "another12345")


async def test_confirm_wrong_code_saves_attempt_and_commits_before_error():
    reset, svc, db, _, codes, _ = make_reset("123456")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    db.commits = 0
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    assert db.commits == 1 and codes.rows[u.id].failed_attempts == 1


async def test_confirm_locks_after_five_failures_even_with_right_code():
    reset, svc, db, _, codes, _ = make_reset("123456")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    for _ in range(5):
        with pytest.raises(InvalidResetCodeError):
            await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    db.commits = 0
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "123456", "newpassword1")
    assert u.token_version == 0 and codes.rows[u.id].failed_attempts == 5


async def test_five_failures_then_rerequest_issues_fresh_usable_code():
    reset, svc, db, parts, codes, notifier = make_reset("111111", "222222")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    for _ in range(5):
        with pytest.raises(InvalidResetCodeError):
            await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    parts["clock"].advance(seconds=60)
    await reset.request_reset("a@b.com")
    assert codes.rows[u.id].failed_attempts == 0 and len(notifier.sent) == 2
    await reset.confirm_reset("a@b.com", "222222", "newpassword1")  # 새 코드로 성공
    assert u.token_version == 1


async def test_five_failures_then_rerequest_within_cooldown_keeps_locked_code():
    reset, svc, db, parts, codes, notifier = make_reset("111111", "222222")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    for _ in range(5):
        with pytest.raises(InvalidResetCodeError):
            await reset.confirm_reset("a@b.com", "000000", "newpassword1")
    await reset.request_reset("a@b.com")  # 60초 안: 새 코드 없음
    assert codes.rows[u.id].failed_attempts == 5 and len(notifier.sent) == 1
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "111111", "newpassword1")
    assert u.token_version == 0


async def test_confirm_weak_password_does_not_touch_code():
    reset, svc, db, _, codes, _ = make_reset("123456")
    u = await signed_up(svc)
    await reset.request_reset("a@b.com")
    db.commits = 0
    with pytest.raises(ValueError) as err:
        await reset.confirm_reset("a@b.com", "000000", "short")
    assert not isinstance(err.value, InvalidResetCodeError)
    assert db.commits == 0 and codes.rows[u.id].failed_attempts == 0
    await reset.confirm_reset("a@b.com", "123456", "newpassword1")  # 코드는 계속 유효


async def test_confirm_expired_code():
    reset, svc, db, parts, codes, _ = make_reset("123456")
    await signed_up(svc)
    await reset.request_reset("a@b.com")
    parts["clock"].advance(minutes=15)
    with pytest.raises(InvalidResetCodeError):
        await reset.confirm_reset("a@b.com", "123456", "newpassword1")


async def test_confirm_unknown_withdrawn_and_missing_row_give_same_error():
    reset, svc, db, parts, codes, _ = make_reset("123456")
    with pytest.raises(InvalidResetCodeError) as unknown:
        await reset.confirm_reset("nobody@b.com", "123456", "newpassword1")
    u = await signed_up(svc)
    with pytest.raises(InvalidResetCodeError) as no_row:  # 코드를 요청한 적 없음
        await reset.confirm_reset("a@b.com", "123456", "newpassword1")
    await reset.request_reset("a@b.com")
    await svc.withdraw_user(u.id, "사유", now=T0)
    with pytest.raises(InvalidResetCodeError) as withdrawn:
        await reset.confirm_reset("a@b.com", "123456", "newpassword1")
    assert str(unknown.value) == str(no_row.value) == str(withdrawn.value)
    assert parts["hasher"].dummy_calls == 3


# ── AccountWithdrawalService (포트 fake 기록기) ──
class Recorder:
    """세 포트를 한 객체로 구현해 호출 순서를 기록한다."""

    def __init__(self, store=None, reserved=False, cancelled=2, fail_on=None):
        self.events = []
        self.store = store
        self.reserved = reserved
        self.cancelled = cancelled
        self.fail_on = fail_on

    def _hit(self, name):
        self.events.append(name)
        if self.fail_on == name:
            raise ValueError(name)

    async def lock_store_of_owner(self, owner_id):
        self._hit("lock_store")
        return self.store

    async def close_store_by_admin(self, store_id, reason, *, has_reserved_reservations, now, commit=True):
        self._hit("close_store")
        self.close_args = (reason, has_reserved_reservations, commit)
        return self.store

    async def end_all_sales_of_store(self, store_id, *, now, commit=True):
        self._hit("end_sales")
        assert commit is False
        return 0

    async def cancel_active_for_user(self, user_id, *, reason):
        self._hit("cancel")
        self.cancel_reason = reason
        return self.cancelled

    async def has_reserved_for_store(self, store_id, *, excluding_user_id=None):
        self._hit("has_reserved")
        self.excluded = excluding_user_id
        return self.reserved


def make_withdrawal(recorder):
    svc, db, parts = build()
    original = svc.withdraw_user

    async def traced(*a, **kw):
        recorder.events.append("withdraw")
        assert kw["commit"] is False
        return await original(*a, **kw)

    svc.withdraw_user = traced
    original_check = svc.check_self_withdrawable

    async def traced_check(*a, **kw):
        recorder.events.append("check")
        return await original_check(*a, **kw)

    svc.check_self_withdrawable = traced_check
    original_commit = db.commit

    async def traced_commit():
        recorder.events.append("commit")
        await original_commit()

    db.commit = traced_commit
    service = AccountWithdrawalService(
        session=db, accounts=svc, stores=recorder, offers=recorder,
        reservations=recorder, clock=parts["clock"],
    )
    return service, svc, db, parts


async def test_withdraw_self_customer_order_and_single_commit():
    rec = Recorder(cancelled=3)
    service, svc, db, parts = make_withdrawal(rec)
    u = await signed_up(svc)
    u.users_point = 400
    db.commits = 0
    rec.events.clear()
    result = await service.withdraw_self(u.id, "password1")
    assert rec.events == ["check", "cancel", "withdraw", "commit"]
    assert db.commits == 1
    assert rec.cancel_reason == SELF_WITHDRAWAL_REASON == "회원 본인 탈퇴"
    assert (result.id, result.status, result.cancelled_reservation_count) == (u.id, "WITHDRAWN", 3)
    assert u.users_point == 0 and u.deleted_reason == SELF_WITHDRAWAL_REASON


async def test_withdraw_self_owner_with_open_store_order():
    store = SimpleNamespace(id=uuid.uuid4(), is_closed=False)
    rec = Recorder(store=store)
    service, svc, db, _ = make_withdrawal(rec)
    u = await signed_up(svc, role="OWNER")
    rec.events.clear()
    await service.withdraw_self(u.id, "password1")
    assert rec.events == [
        "check", "lock_store", "end_sales", "has_reserved", "cancel", "close_store", "withdraw", "commit",
    ]
    assert rec.excluded == u.id
    assert rec.close_args == (SELF_WITHDRAWAL_REASON, False, False)


async def test_withdraw_self_owner_with_closed_or_no_store_skips_store_steps():
    for store in (None, SimpleNamespace(id=uuid.uuid4(), is_closed=True)):
        rec = Recorder(store=store)
        service, svc, db, _ = make_withdrawal(rec)
        u = await signed_up(svc, role="OWNER")
        rec.events.clear()
        await service.withdraw_self(u.id, "password1")
        assert rec.events == ["check", "lock_store", "cancel", "withdraw", "commit"]


async def test_withdraw_self_wrong_password_and_admin_call_no_ports():
    rec = Recorder()
    service, svc, db, _ = make_withdrawal(rec)
    u = await signed_up(svc)
    admin, _ = await svc.ensure_admin("adm@b.com", "password1")
    rec.events.clear()
    with pytest.raises(CurrentPasswordMismatchError):
        await service.withdraw_self(u.id, "bad")
    with pytest.raises(AdminAccountProtectedError):
        await service.withdraw_self(admin.id, "password1")
    assert rec.events == ["check", "check"]  # 포트 호출 0
    assert u.status is UserStatus.APPROVED


async def test_withdraw_self_store_failure_means_no_commit():
    store = SimpleNamespace(id=uuid.uuid4(), is_closed=False)
    rec = Recorder(store=store, fail_on="close_store")
    service, svc, db, _ = make_withdrawal(rec)
    u = await signed_up(svc, role="OWNER")
    db.commits = 0
    rec.events.clear()
    with pytest.raises(ValueError):
        await service.withdraw_self(u.id, "password1")
    assert db.commits == 0 and "commit" not in rec.events and "withdraw" not in rec.events
