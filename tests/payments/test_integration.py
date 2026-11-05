"""결제 <-> 예약 <-> 환불 통합 테스트. DB 없음.

실제 container 조립(wire_dependencies + 어댑터 + 서비스)을 그대로 쓰고, 레포지토리·세션만
트랜잭션을 흉내 내는 메모리 fake로 바꾼다(commit 전 변경은 rollback/요청 종료 때 버려진다).
재고 포트는 세 가지다.
- restores: 복구에 성공하는 가짜 재고(release -> True). 전체 성공 흐름을 본다.
- release_fails: release가 예외를 내는 가짜 재고. 롤백을 본다.
- interim: 실제 임시 포트 ReadOnlyOfferStockPort(release -> False). 결제된 예약의 취소·환불은 503이다.
"""

import copy
import uuid
from datetime import timedelta
from types import SimpleNamespace
from typing import Annotated

import httpx
import pytest
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials

import container
from auth.domain.exceptions import AuthenticationError
from auth.domain.user import Role, User
from auth.presentation.dependencies import bearer_scheme, get_current_user
from catalog.domain.discount_offer import DiscountOffer
from database import get_db
from main import app
from payments.domain.exceptions import PaymentAlreadyExistsError, PaymentAlreadyRefundedError
from payments.domain.payment import Payment, PaymentStatus
from payments.domain.refund import Refund
from payments.domain.repository.payment_repository import PaymentRepository
from payments.domain.repository.refund_repository import RefundRepository
from reservations.domain.offer_ref import OfferRef
from reservations.domain.pickup_reservation import PickupReservation
from reservations.domain.pickup_reservation import ReservationStatus as S
from reservations.domain.repository import ReservationRepository
from tests.reservations.fakes import NOW, FakeStock, Log, Terms
from tests.reservations.test_adapters import Offers, Products, Stores

pytestmark = pytest.mark.anyio

CUSTOMER = uuid.uuid4()
OWNER = uuid.uuid4()
PRICE, QTY = 3000, 2
TOTAL = PRICE * QTY
H = timedelta(hours=1)
STOCK_503 = {
    "success": False,
    "error_code": "STOCK_NOT_CONNECTED",
    "message": "재고 연동이 아직 준비되지 않아 결제된 예약의 취소·환불을 처리할 수 없습니다.",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


# ── 트랜잭션을 흉내 내는 메모리 저장소 ──
class Tx:
    """commit하면 pending이 확정되고, 버려지면(rollback·요청 종료) 사라진다."""

    def __init__(self, log: Log):
        self.log = log
        self.stores: list[Store] = []
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1
        self.log.events.append("commit")
        for store in self.stores:
            store.committed.update(store.pending)
            store.pending.clear()

    async def rollback(self):
        self.rollbacks += 1
        self.log.events.append("rollback")
        self.discard()

    def discard(self):
        for store in self.stores:
            store.pending.clear()


class Store:
    def __init__(self, tx: Tx):
        self.committed: dict = {}
        self.pending: dict = {}
        tx.stores.append(self)

    def get(self, key):
        item = self.pending.get(key) or self.committed.get(key)
        return copy.deepcopy(item) if item is not None else None

    def put(self, key, item):
        self.pending[key] = copy.deepcopy(item)

    def all(self):
        merged = {**self.committed, **self.pending}
        return [copy.deepcopy(v) for v in merged.values()]


class ResRepo(ReservationRepository):
    def __init__(self, tx: Tx, log: Log):
        self.store, self.log = Store(tx), log

    async def find_by_id(self, reservation_id, for_update=False):
        self.log.events.append("res_lock" if for_update else "res_read")
        return self.store.get(reservation_id)

    async def find_by_user(self, user_id, *, status, page, size):
        rows = [r for r in self.store.all() if r.user_id == user_id]
        return rows, len(rows)

    async def find_by_offer(self, offer_id, *, for_update=False):
        return [r for r in self.store.all() if r.offer_id == offer_id]

    async def exists_by_offer(self, offer_id):
        return any(r.offer_id == offer_id for r in self.store.all())

    async def save(self, reservation):
        if reservation.id is None:
            reservation.id = uuid.uuid4()
        self.store.put(reservation.id, reservation)
        self.log.events.append("res_save")
        return reservation


class PayRepo(PaymentRepository):
    def __init__(self, tx: Tx, log: Log):
        self.store, self.log = Store(tx), log

    async def find_by_id(self, payment_id, for_update=False):
        self.log.events.append("pay_lock" if for_update else "pay_read")
        return self.store.get(payment_id)

    async def find_by_reservation_id(self, reservation_id, for_update=False):
        self.log.events.append("pay_lock" if for_update else "pay_read")
        return next((p for p in self.store.all() if p.reservation_id == reservation_id), None)

    async def save(self, payment):
        if payment.id is None:
            if any(p.reservation_id == payment.reservation_id for p in self.store.all()):
                raise PaymentAlreadyExistsError()
            payment.id = uuid.uuid4()
            self.log.events.append("pay_insert")
        else:
            self.log.events.append("pay_update")
        self.store.put(payment.id, payment)
        return payment


class RefRepo(RefundRepository):
    def __init__(self, tx: Tx, log: Log):
        self.store, self.log = Store(tx), log
        self.fail = False

    async def find_by_id(self, refund_id):
        return self.store.get(refund_id)

    async def find_by_payment_id(self, payment_id):
        self.log.events.append("refund_read")
        return next((r for r in self.store.all() if r.payment_id == payment_id), None)

    async def save(self, refund):
        if self.fail:
            raise RuntimeError("환불 저장 실패")
        if any(r.payment_id == refund.payment_id for r in self.store.all()):
            raise PaymentAlreadyRefundedError()
        refund.id = uuid.uuid4()
        self.store.put(refund.id, refund)
        self.log.events.append("refund_insert")
        return refund


class FailingStock(FakeStock):
    async def release(self, offer_id, quantity, *, user_id, reason):
        raise RuntimeError("재고 복구 실패")


async def fake_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("로그인이 필요합니다.")
    user_id, role = credentials.credentials.split(":")
    return User(email="t@example.com", password_hash="x", role=Role(role), id=uuid.UUID(user_id))


def headers(user_id=CUSTOMER, role="CUSTOMER"):
    return {"Authorization": f"Bearer {user_id}:{role}"}


class Env:
    def __init__(self, mode: str):
        self.log = Log()
        self.tx = Tx(self.log)
        self.res = ResRepo(self.tx, self.log)
        self.pay = PayRepo(self.tx, self.log)
        self.refund = RefRepo(self.tx, self.log)
        self.overrides: dict = {}
        if mode == "interim":
            self.stock = None
            self.offer_id = uuid.uuid4()
            offer = DiscountOffer(
                product_id=uuid.uuid4(), sale_price=PRICE, initial_stock=5, sales_start=NOW - H,
                sales_end=NOW + H, pickup_start=NOW + H, pickup_end=NOW + 3 * H, id=self.offer_id,
            )
            product = SimpleNamespace(name="샌드위치", store_id=uuid.uuid4())
            store = SimpleNamespace(owner_id=OWNER, name="마감 베이커리", pickup_address="서울")
            self.overrides.update(
                {
                    container.create_discount_offer_repository: lambda: Offers(offer),
                    container.create_product_repository: lambda: Products(product),
                    container.create_store_port: lambda: Stores(store),
                }
            )
        else:
            self.stock = (FailingStock if mode == "release_fails" else FakeStock)(self.log, OWNER, stock=3)
            self.offer_id = self.stock.offer_id
            self.overrides[container.create_stock_port] = lambda: self.stock

        async def tx_session():
            try:
                yield self.tx
            finally:
                self.tx.discard()  # 실제 세션이 닫히며 커밋 안 된 변경을 버리는 것과 같다

        self.overrides.update(
            {
                get_db: tx_session,
                get_current_user: fake_current_user,
                container.create_reservation_repository: lambda: self.res,
                container.create_payment_repository: lambda: self.pay,
                container.create_refund_repository: lambda: self.refund,
            }
        )

    # ── 확정된(committed) 상태 조회 ──
    def reservation(self, rid):
        return self.res.store.committed[rid]

    def payment_for(self, rid):
        return next((p for p in self.pay.store.committed.values() if p.reservation_id == rid), None)

    @property
    def refunds_saved(self):
        return list(self.refund.store.committed.values())

    # ── 준비 ──
    def _reset(self):
        self.tx.commits = 0
        self.log.events.clear()

    async def seed(self, status=S.PENDING_PAYMENT) -> uuid.UUID:
        terms = Terms(offer_id=self.offer_id, owner_id=OWNER, sale_price=PRICE)
        reservation = PickupReservation.create(CUSTOMER, OfferRef.from_info(terms), QTY, "A12345", NOW)
        if status == S.RESERVED:
            reservation.mark_paid()
        await self.res.save(reservation)
        await self.tx.commit()
        self._reset()
        return reservation.id

    async def seed_payment(self, rid, *, refunded=False, refund_row_only=False):
        payment = Payment.request(rid, CUSTOMER, TOTAL, NOW)
        payment.approve("pg", NOW)
        await self.pay.save(payment)
        if refunded or refund_row_only:
            refund = Refund(payment.id, TOTAL, 0, "x", completed_at=NOW)
            if refunded:
                payment.status = PaymentStatus.REFUNDED
                await self.pay.save(payment)
            await self.refund.save(refund)
        await self.tx.commit()
        self._reset()
        return payment


@pytest.fixture
def make_env():
    previous: dict = {}

    def factory(mode: str = "restores") -> Env:
        env = Env(mode)
        for key, value in env.overrides.items():
            previous.setdefault(key, app.dependency_overrides.get(key))
            app.dependency_overrides[key] = value
        return env

    yield factory
    for key, value in previous.items():
        if value is None:
            app.dependency_overrides.pop(key, None)
        else:
            app.dependency_overrides[key] = value


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def pay(client, rid, user=CUSTOMER):
    return await client.post("/v1/payments", json={"reservation_id": str(rid)}, headers=headers(user))


async def cancel(client, rid, user=CUSTOMER):
    return await client.post(f"/v1/reservations/{rid}/cancel", headers=headers(user))


async def refund(client, payment_id, user=CUSTOMER, reason="변심"):
    return await client.post(
        f"/v1/payments/{payment_id}/refunds", json={"reason": reason}, headers=headers(user)
    )


# ══ 전체 성공 흐름 (복구 성공 재고) ══
async def test_pay_confirms_reservation_then_pickup(make_env, client):
    env = make_env()
    rid = await env.seed()

    r = await pay(client, rid)

    assert r.status_code == 201 and r.json()["status"] == "PAID" and r.json()["amount"] == TOTAL
    assert env.reservation(rid).status == S.RESERVED  # 결제 -> 예약 확정
    assert env.payment_for(rid).status == PaymentStatus.PAID
    assert env.tx.commits == 1  # commit은 결제 서비스가 한 번만

    r = await client.post(
        f"/v1/reservations/{rid}/pickup", json={"pickup_code": "A12345"}, headers=headers(OWNER, "OWNER")
    )
    assert r.status_code == 200 and r.json()["status"] == "PICKED_UP"
    assert env.reservation(rid).status == S.PICKED_UP


async def test_cancel_paid_reservation_refunds_and_restores_stock(make_env, client):
    env = make_env()
    rid = await env.seed()
    await pay(client, rid)
    env.tx.commits = 0

    r = await cancel(client, rid)

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert env.tx.commits == 1  # 취소 + 환불 + 재고 복구가 commit 1회
    assert env.reservation(rid).status == S.CANCELLED
    assert env.payment_for(rid).status == PaymentStatus.REFUNDED
    [saved] = env.refunds_saved
    assert (saved.refund_amount, saved.penalty_amount) == (TOTAL, 0)  # 위약금 0원(RD-3)
    assert env.stock.released == [(env.offer_id, QTY, CUSTOMER, "고객 요청 취소")]
    assert env.stock.stock == 3 + QTY


async def test_refund_api_cancels_reservation_and_restores_stock(make_env, client):
    env = make_env()
    rid = await env.seed()
    payment_id = (await pay(client, rid)).json()["id"]
    env.tx.commits = 0

    r = await refund(client, payment_id, reason="환불해주세요")

    assert r.status_code == 201, r.text
    assert (r.json()["refund_amount"], r.json()["penalty_amount"]) == (TOTAL, 0)
    assert env.tx.commits == 1
    assert env.reservation(rid).status == S.CANCELLED  # RD-2: 환불 API가 예약 취소까지
    assert env.payment_for(rid).status == PaymentStatus.REFUNDED
    assert env.stock.released == [(env.offer_id, QTY, CUSTOMER, "환불해주세요")]


# ══ 중복 ══
async def test_duplicate_pay_is_409(make_env, client):
    env = make_env()
    rid = await env.seed()
    await pay(client, rid)
    commits = env.tx.commits

    r = await pay(client, rid)

    assert r.status_code == 409 and r.json()["message"] == "이미 결제된 예약입니다."
    assert env.tx.commits == commits and len(env.pay.store.committed) == 1


async def test_duplicate_refund_is_409(make_env, client):
    env = make_env()
    rid = await env.seed()
    payment_id = (await pay(client, rid)).json()["id"]
    await refund(client, payment_id)
    commits = env.tx.commits

    r = await refund(client, payment_id)

    assert r.status_code == 409 and r.json()["message"] == "이미 환불 처리된 결제입니다."
    assert env.tx.commits == commits and len(env.refunds_saved) == 1


# ══ 실패 롤백 ══
async def test_cancel_api_refund_failure_keeps_reservation_unchanged(make_env, client):
    env = make_env()
    rid = await env.seed()
    await pay(client, rid)
    env.tx.commits = 0
    env.refund.fail = True

    with pytest.raises(RuntimeError, match="환불 저장 실패"):
        await cancel(client, rid)

    assert env.tx.commits == 0
    assert env.reservation(rid).status == S.RESERVED  # 취소 상태가 반영되지 않음
    assert env.payment_for(rid).status == PaymentStatus.PAID
    assert env.refunds_saved == []


async def test_refund_api_cancel_failure_saves_no_refund(make_env, client):
    env = make_env("release_fails")
    rid = await env.seed()
    payment_id = (await pay(client, rid)).json()["id"]
    env.tx.commits = 0

    with pytest.raises(RuntimeError, match="재고 복구 실패"):
        await refund(client, payment_id)

    assert env.tx.commits == 0 and env.tx.rollbacks >= 1
    assert env.refunds_saved == []  # cancel_for_refund 실패 시 환불 미저장
    assert env.payment_for(rid).status == PaymentStatus.PAID
    assert env.reservation(rid).status == S.RESERVED


# ══ 3단계 불일치 fail-closed (임시 409, 저장 0) ══
@pytest.mark.parametrize("case", ["no_payment", "payment_refunded", "refund_row_exists"])
async def test_cancel_with_inconsistent_payment_is_409_and_saves_nothing(make_env, client, case):
    env = make_env()
    rid = await env.seed(S.RESERVED)
    if case == "payment_refunded":
        await env.seed_payment(rid, refunded=True)
    elif case == "refund_row_exists":
        await env.seed_payment(rid, refund_row_only=True)
    refunds_before = len(env.refunds_saved)

    r = await cancel(client, rid)

    assert r.status_code == 409
    assert r.json() == {
        "success": False,
        "error_code": "DATA_INCONSISTENT",
        "message": "예약과 결제 상태가 일치하지 않아 처리할 수 없습니다.",
    }
    assert env.tx.commits == 0
    assert env.reservation(rid).status == S.RESERVED
    assert len(env.refunds_saved) == refunds_before  # 새 환불 없음


# ══ 임시 재고 포트(실제 container 경로) ══
async def test_interim_cancel_paid_is_503_and_saves_nothing(make_env, client):
    env = make_env("interim")
    rid = await env.seed()
    assert (await pay(client, rid)).status_code == 201
    env.tx.commits = 0

    r = await cancel(client, rid)

    assert r.status_code == 503 and r.json() == STOCK_503
    assert env.tx.commits == 0
    assert env.reservation(rid).status == S.RESERVED
    assert env.payment_for(rid).status == PaymentStatus.PAID
    assert env.refunds_saved == []


async def test_interim_refund_api_is_503_with_common_format_and_saves_nothing(make_env, client):
    env = make_env("interim")
    rid = await env.seed()
    payment_id = (await pay(client, rid)).json()["id"]
    env.tx.commits = 0

    r = await refund(client, payment_id)

    assert r.status_code == 503 and r.json() == STOCK_503
    assert env.tx.commits == 0 and env.tx.rollbacks >= 1
    assert env.reservation(rid).status == S.RESERVED
    assert env.payment_for(rid).status == PaymentStatus.PAID
    assert env.refunds_saved == []


async def test_interim_cancel_unpaid_is_200(make_env, client):
    env = make_env("interim")
    rid = await env.seed()

    r = await cancel(client, rid)

    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    assert env.tx.commits == 1
    assert env.reservation(rid).status == S.CANCELLED
    assert env.refunds_saved == []


# ══ 잠금 순서 (RD-5: 상품 -> 할인 -> 예약 -> 결제 -> 환불) ══
LOCK_ORDER = ["offer_lock", "res_lock", "pay_lock", "refund_insert"]


def assert_lock_order(events):
    positions = [events.index(name) for name in LOCK_ORDER if name in events]
    assert positions == sorted(positions), events
    # 결제 잠금은 할인·예약 잠금 뒤에만 온다 (결제를 먼저 잠그는 경로 금지)
    assert events.index("pay_lock") > events.index("res_lock"), events
    assert events.index("pay_lock") > events.index("offer_lock"), events


async def test_lock_order_pay(make_env, client):
    env = make_env()
    rid = await env.seed()
    await pay(client, rid)
    events = env.log.events
    assert "pay_lock" not in events  # 새 행 INSERT라 잠글 결제 행이 없다(UNIQUE가 최종 방어)
    assert events.index("offer_lock") < events.index("res_lock") < events.index("pay_insert")


async def test_lock_order_customer_cancel(make_env, client):
    env = make_env()
    rid = await env.seed()
    await pay(client, rid)
    env.log.events.clear()
    await cancel(client, rid)
    assert {"offer_lock", "res_lock", "pay_lock", "refund_insert"} <= set(env.log.events)
    assert_lock_order(env.log.events)


async def test_lock_order_refund_api(make_env, client):
    env = make_env()
    rid = await env.seed()
    payment_id = (await pay(client, rid)).json()["id"]
    env.log.events.clear()
    await refund(client, payment_id)
    events = env.log.events
    assert events[0] == "pay_read"  # 결제는 잠금 없이 읽기만 먼저 한다
    assert {"offer_lock", "res_lock", "pay_lock", "refund_insert"} <= set(events)
    assert_lock_order(events)
