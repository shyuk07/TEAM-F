"""로컬 개발 화면 확인용 샘플 데이터 생성 스크립트.

서버 API(HTTP)만 사용하며 DB에 직접 쓰지 않는다. 다시 실행해도 안전하다
(이미 있는 계정·상점·상품은 재사용하고, 판매 중인 할인이 있으면 새로 만들지 않는다).

사용법 (backend 폴더, 서버가 켜져 있는 상태):
    uv run python scripts/seed_dev.py

환경변수:
    SEED_BASE_URL   서버 주소 (기본 http://localhost:8001)
    ADMIN_EMAIL     관리자 이메일 (없으면 backend/.env, 상위 .env에서 읽음)
    ADMIN_PASSWORD  관리자 비밀번호 (위와 같음)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Windows 콘솔(cp949 등)에서도 한국어 출력이 깨지거나 오류 나지 않게 한다
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

BACKEND_DIR = Path(__file__).resolve().parent.parent

# ── 샘플 데이터 상수 (로컬 개발 전용 계정. 실제 서비스에서 쓰지 않는다) ──
OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "seed-owner-1234"
OWNER_NAME = "마감직전 샘플 베이커리"  # 상점명은 상점주 이름(상호)으로 정해진다
OWNER_PHONE = "010-0000-0001"

CUSTOMER_EMAIL = "customer@example.com"
CUSTOMER_PASSWORD = "seed-customer-1234"
CUSTOMER_NAME = "샘플 고객"
CUSTOMER_PHONE = "010-0000-0002"

# 카카오 키가 없으면 서버의 MockGeocoder가 주소와 관계없이 강남역 부근 좌표를 준다.
# 키가 있어도 강남역 근처로 잡히도록 강남역 주변 주소를 쓴다.
STORE_ADDRESS = "서울특별시 강남구 강남대로 396"

PRODUCTS = [
    {"name": "통밀 식빵", "category": "베이커리", "description": "오늘 아침 구운 통밀 식빵입니다.", "original_price": 6000, "sale_price": 3000, "stock": 5},
    {"name": "크루아상 3개 세트", "category": "베이커리", "description": "버터 크루아상 3개 묶음입니다.", "original_price": 9000, "sale_price": 4500, "stock": 4},
    {"name": "닭가슴살 샐러드", "category": "샐러드", "description": "신선한 채소와 닭가슴살 샐러드입니다.", "original_price": 8500, "sale_price": 5000, "stock": 3},
    {"name": "아이스 아메리카노", "category": "음료", "description": "원두를 바로 내린 아메리카노입니다.", "original_price": 4500, "sale_price": 2000, "stock": 10},
]

KST = timezone(timedelta(hours=9))  # 고정 오프셋이라 Windows에 tzdata가 없어도 동작한다
FRONTEND_URL = "http://localhost:5173/"


class SeedError(Exception):
    """단계 실패. main에서 받아 출력하고 종료 코드 1로 끝낸다."""


def fail(step: str, response: httpx.Response | None = None, detail: str = "") -> SeedError:
    lines = [f"[실패] 단계: {step}"]
    if response is not None:
        lines.append(f"  상태 코드: {response.status_code} ({response.request.method} {response.request.url.path})")
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            lines.append(f"  error_code: {body.get('error_code')}")
            lines.append(f"  message: {body.get('message')}")
        else:
            lines.append(f"  응답 본문: {response.text[:500]}")
    if detail:
        lines.append(f"  안내: {detail}")
    return SeedError("\n".join(lines))


def error_code(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body.get("error_code") if isinstance(body, dict) else None


def load_admin_credentials() -> tuple[str, str]:
    # 이미 설정된 환경변수가 우선이고, 없으면 backend/.env, 그다음 상위 .env에서 읽는다
    load_dotenv(BACKEND_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR.parent / ".env", override=False)
    email = (os.environ.get("ADMIN_EMAIL") or "").strip()
    password = os.environ.get("ADMIN_PASSWORD") or ""
    if not email or not password:
        raise SeedError(
            "[실패] 단계: 관리자 계정 정보 읽기\n"
            "  ADMIN_EMAIL과 ADMIN_PASSWORD를 찾지 못했습니다.\n"
            "  backend/.env에 아래 두 줄을 추가하고(비밀번호는 8자 이상, 'change-me'로 시작하지 않게)\n"
            "  서버를 다시 켠 뒤(서버가 시작할 때 관리자 계정을 만듭니다) 이 스크립트를 다시 실행하세요.\n"
            "    ADMIN_EMAIL=admin@example.com\n"
            "    ADMIN_PASSWORD=<임의의 비밀번호>"
        )
    return email, password


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client, step: str, email: str, password: str, hint: str = "") -> dict:
    res = client.post("/v1/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise fail(step, res, hint)
    return res.json()


def signup(client: httpx.Client, step: str, *, email: str, password: str, name: str, phone: str, role: str) -> bool:
    """가입한다. 새로 만들었으면 True, 이미 있으면 False."""
    res = client.post(
        "/v1/auth/signup",
        json={"email": email, "password": password, "name": name, "phone": phone, "role": role},
    )
    if res.status_code == 201:
        return True
    if res.status_code == 409 and error_code(res) == "EMAIL_DUPLICATED":
        return False
    raise fail(step, res)


def find_user(client: httpx.Client, admin_token: str, email: str, role: str) -> dict:
    step = "관리자: 상점주 계정 찾기"
    res = client.get(
        "/v1/admin/users",
        params={"role": role, "email": email, "page": 1, "size": 100},
        headers=auth_header(admin_token),
    )
    if res.status_code != 200:
        raise fail(step, res)
    for item in res.json()["items"]:
        if item["email"].lower() == email.lower():
            return item
    raise fail(step, detail=f"{email} 계정이 회원 목록에 없습니다.")


def ensure_owner_approved(client: httpx.Client, admin_token: str) -> str:
    owner = find_user(client, admin_token, OWNER_EMAIL, "OWNER")
    status = owner["status"]
    if status == "APPROVED":
        return "이미 승인됨"
    if status != "PENDING":
        raise fail(
            "관리자: 상점주 승인",
            detail=f"상점주 계정 상태가 {status}라 승인할 수 없습니다. 관리자 화면에서 상태를 확인하세요.",
        )
    res = client.patch(f"/v1/admin/owners/{owner['id']}/approve", headers=auth_header(admin_token))
    if res.status_code != 200:
        raise fail("관리자: 상점주 승인", res)
    return "승인 완료"


def ensure_store(client: httpx.Client, owner_token: str) -> tuple[dict, str]:
    res = client.get("/v1/stores/me", headers=auth_header(owner_token))
    if res.status_code == 200:
        store = res.json()
        if store["status"] != "ACTIVE":
            raise fail(
                "상점 확인",
                detail=f"기존 상점({store['name']})의 상태가 {store['status']}입니다. 영업 중인 상점이 아니면 할인이 홈에 보이지 않습니다.",
            )
        return store, "기존 상점 재사용"
    if res.status_code != 404:
        raise fail("내 상점 조회", res)
    res = client.post("/v1/stores", json={"pickup_address": STORE_ADDRESS}, headers=auth_header(owner_token))
    if res.status_code != 201:
        raise fail("상점 개설", res)
    return res.json(), "새로 개설"


def ensure_products(client: httpx.Client, owner_token: str, store_id: str) -> dict[str, dict]:
    """샘플 상품을 이름으로 찾아 재사용하고, 없으면 등록한다. 이름 -> 상품."""
    res = client.get(f"/v1/stores/{store_id}/products", params={"page": 1, "size": 100}, headers=auth_header(owner_token))
    if res.status_code != 200:
        raise fail("상품 목록 조회", res)
    existing = {p["name"]: p for p in res.json()["items"]}
    result: dict[str, dict] = {}
    for spec in PRODUCTS:
        product = existing.get(spec["name"])
        if product is None:
            res = client.post(
                f"/v1/stores/{store_id}/products",
                json={
                    "name": spec["name"],
                    "category": spec["category"],
                    "description": spec["description"],
                    "original_price": spec["original_price"],
                },
                headers=auth_header(owner_token),
            )
            if res.status_code != 201:
                raise fail(f"상품 등록 ({spec['name']})", res)
            product = res.json()
            print(f"  - 상품 등록: {spec['name']}")
        elif not product["is_active"]:
            res = client.post(f"/v1/products/{product['id']}/activate", headers=auth_header(owner_token))
            if res.status_code != 200:
                raise fail(f"상품 재노출 ({spec['name']})", res)
            product = res.json()
            print(f"  - 상품 재노출: {spec['name']}")
        else:
            print(f"  - 상품 재사용: {spec['name']}")
        result[spec["name"]] = product
    return result


def offer_times() -> dict[str, str]:
    # 판매 시작은 과거, 판매 마감·픽업은 미래 (판매 마감 > 지금, 픽업 마감 >= 판매 마감, 픽업 마감 > 픽업 시작)
    now = datetime.now(KST).replace(microsecond=0)
    return {
        "sales_start": (now - timedelta(minutes=10)).isoformat(),
        "sales_end": (now + timedelta(hours=4)).isoformat(),
        "pickup_start": (now + timedelta(hours=2)).isoformat(),
        "pickup_end": (now + timedelta(hours=6)).isoformat(),
    }


def ensure_offers(client: httpx.Client, owner_token: str, store_id: str, products: dict[str, dict]) -> int:
    """상품마다 판매 중인 할인을 하나씩 보장한다. 판매 중 할인 수를 돌려준다."""
    # 상점주가 조회하면 기본으로 SCHEDULED, ON_SALE, SOLD_OUT, SUSPENDED가 나온다 (진행 중인 할인)
    res = client.get(f"/v1/stores/{store_id}/offers", params={"page": 1, "size": 100}, headers=auth_header(owner_token))
    if res.status_code != 200:
        raise fail("상점 할인 목록 조회", res)
    open_offers = {o["product_id"]: o for o in res.json()["items"]}
    on_sale = 0
    for spec in PRODUCTS:
        product = products[spec["name"]]
        current = open_offers.get(product["id"])
        if current is not None:
            status = current["status"]
            if status == "ON_SALE":
                print(f"  - 할인 재사용: {spec['name']} (남은 수량 {current['remaining_stock']}개)")
                on_sale += 1
                continue
            if status == "SOLD_OUT":
                res = client.post(
                    f"/v1/offers/{current['id']}/stock-adjustments",
                    json={"amount": spec["stock"], "reason": "샘플 데이터 재고 보충"},
                    headers=auth_header(owner_token),
                )
                if res.status_code != 200:
                    raise fail(f"재고 보충 ({spec['name']})", res)
                print(f"  - 품절 할인 재고 보충: {spec['name']} (+{spec['stock']}개)")
                on_sale += 1
                continue
            # SCHEDULED·SUSPENDED는 진행 중인 할인이라 새로 등록할 수 없다. 그대로 두고 알린다.
            print(f"  - 할인 건너뜀: {spec['name']} (기존 할인 상태 {status}, 홈에는 보이지 않을 수 있음)")
            continue
        res = client.post(
            f"/v1/products/{product['id']}/offers",
            json={"sale_price": spec["sale_price"], "initial_stock": spec["stock"], **offer_times()},
            headers=auth_header(owner_token),
        )
        if res.status_code != 201:
            raise fail(f"할인 등록 ({spec['name']})", res)
        offer = res.json()
        print(f"  - 할인 등록: {spec['name']} {spec['original_price']}원 -> {spec['sale_price']}원, {spec['stock']}개 (상태 {offer['status']})")
        if offer["status"] == "ON_SALE":
            on_sale += 1
    return on_sale


def count_home_offers(client: httpx.Client, store_id: str) -> int:
    # 고객 홈과 같은 공개 목록(위치 없이 전체 조회)에서 이 상점의 할인이 보이는지 확인한다
    res = client.get("/v1/offers", params={"page": 1, "size": 100})
    if res.status_code != 200:
        raise fail("고객 홈 할인 목록 확인", res)
    return sum(1 for item in res.json()["items"] if item["offer"]["store_id"] == store_id)


def run(base_url: str) -> None:
    admin_email, admin_password = load_admin_credentials()
    with httpx.Client(base_url=base_url, timeout=15.0) as client:
        try:
            client.get("/health/db")
        except httpx.HTTPError as e:
            raise SeedError(
                f"[실패] 단계: 서버 연결\n  {base_url}에 연결하지 못했습니다 ({type(e).__name__}).\n"
                "  안내: backend 폴더에서 'uv run uvicorn main:app --app-dir src --reload --port 8001'로 서버를 먼저 켜세요."
            ) from e

        print("1. 관리자 로그인")
        admin_token = login(
            client, "관리자 로그인", admin_email, admin_password,
            "ADMIN_EMAIL/ADMIN_PASSWORD가 서버를 켤 때 쓴 .env 값과 같은지 확인하세요. "
            "값을 새로 넣었다면 서버를 다시 켜야 관리자 계정이 만들어집니다.",
        )["access_token"]

        print("2. 상점주 가입")
        created = signup(client, "상점주 가입", email=OWNER_EMAIL, password=OWNER_PASSWORD, name=OWNER_NAME, phone=OWNER_PHONE, role="OWNER")
        print(f"  - {'새로 가입' if created else '이미 있는 계정'}: {OWNER_EMAIL}")

        print("3. 관리자: 상점주 승인")
        print(f"  - {ensure_owner_approved(client, admin_token)}")

        print("4. 상점주 로그인")
        owner_token = login(
            client, "상점주 로그인", OWNER_EMAIL, OWNER_PASSWORD,
            f"{OWNER_EMAIL} 계정이 다른 비밀번호로 이미 있으면 이 스크립트의 OWNER_PASSWORD와 맞추거나 계정을 정리하세요.",
        )["access_token"]

        print("5. 상점 개설")
        store, how = ensure_store(client, owner_token)
        print(f"  - {how}: {store['name']} ({store['pickup_address']}, 위도 {store['latitude']}, 경도 {store['longitude']})")

        print("6. 상품 등록")
        products = ensure_products(client, owner_token, store["id"])

        print("7. 할인 등록")
        on_sale = ensure_offers(client, owner_token, store["id"], products)

        print("8. 고객 가입")
        created = signup(client, "고객 가입", email=CUSTOMER_EMAIL, password=CUSTOMER_PASSWORD, name=CUSTOMER_NAME, phone=CUSTOMER_PHONE, role="CUSTOMER")
        print(f"  - {'새로 가입' if created else '이미 있는 계정'}: {CUSTOMER_EMAIL}")
        login(
            client, "고객 로그인 확인", CUSTOMER_EMAIL, CUSTOMER_PASSWORD,
            f"{CUSTOMER_EMAIL} 계정이 다른 비밀번호로 이미 있으면 이 스크립트의 CUSTOMER_PASSWORD와 맞추세요.",
        )

        print("9. 고객 홈 노출 확인 (GET /v1/offers)")
        visible = count_home_offers(client, store["id"])
        print(f"  - 이 상점의 판매 중 할인 {visible}개가 보입니다.")

    print()
    print("=== 샘플 데이터 준비 완료 ===")
    print(f"상점: {store['name']} / 판매 중 할인 {on_sale}개 (홈 목록에서 확인 {visible}개)")
    print(f"고객 계정:   {CUSTOMER_EMAIL} / {CUSTOMER_PASSWORD}")
    print(f"상점주 계정: {OWNER_EMAIL} / {OWNER_PASSWORD}")
    print(f"확인할 주소: {FRONTEND_URL}")
    print("참고: 브라우저 위치 권한을 허용하면 현재 위치 기준 반경으로 검색합니다. 상점 좌표는 강남역 부근이라")
    print("      멀리 있으면 카드가 안 보일 수 있으니, 그때는 위치 권한을 거부하고 전체 목록으로 확인하세요.")


def main() -> int:
    base_url = (os.environ.get("SEED_BASE_URL") or "http://localhost:8001").rstrip("/")
    print(f"서버: {base_url}")
    try:
        run(base_url)
    except SeedError as e:
        print(e, file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"[실패] 서버와 통신 중 오류: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
