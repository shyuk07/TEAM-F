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
CUSTOMER_EMAIL = "customer@example.com"
CUSTOMER_PASSWORD = "seed-customer-1234"
CUSTOMER_NAME = "샘플 고객"
CUSTOMER_PHONE = "010-0000-0002"


def _p(name: str, category: str, description: str, original_price: int, sale_price: int, stock: int) -> dict:
    return {
        "name": name,
        "category": category,
        "description": description,
        "original_price": original_price,
        "sale_price": sale_price,
        "stock": stock,
    }


# 상점주 1명 = 상점 1개. 상점명은 상점주 이름(상호)으로 정해진다.
# 카카오 키가 없으면 서버의 MockGeocoder가 주소와 관계없이 강남역 부근 좌표를 준다.
# 키가 있어도 강남역 근처로 잡히도록 강남역 주변 주소를 쓴다. 이름+주소가 같은 상점은 만들 수 없어 주소를 다르게 둔다.
STORES = [
    {
        "email": "owner@example.com",
        "password": "seed-owner-1234",
        "name": "마감직전 샘플 베이커리",
        "phone": "010-0000-0001",
        "address": "서울특별시 강남구 강남대로 396",
        "products": [
            _p("통밀 식빵", "베이커리", "오늘 아침 구운 통밀 식빵입니다.", 6000, 3000, 5),
            _p("크루아상 3개 세트", "베이커리", "버터 크루아상 3개 묶음입니다.", 9000, 4500, 4),
            _p("닭가슴살 샐러드", "샐러드", "신선한 채소와 닭가슴살 샐러드입니다.", 8500, 5000, 3),
            _p("아이스 아메리카노", "음료", "원두를 바로 내린 아메리카노입니다.", 4500, 2000, 10),
        ],
    },
    {
        "email": "owner2@example.com",
        "password": "seed-owner-1234",
        "name": "샘플 김밥천국",
        "phone": "010-0000-0011",
        "address": "서울특별시 강남구 테헤란로 101",
        "products": [
            _p("참치김밥", "분식", "참치마요 듬뿍 김밥입니다.", 4500, 2500, 8),
            _p("떡볶이 1인분", "분식", "매콤달콤 국물 떡볶이입니다.", 5000, 3000, 6),
            _p("유부초밥 6개", "분식", "새콤한 유부초밥 6개입니다.", 5500, 3000, 5),
        ],
    },
    {
        "email": "owner3@example.com",
        "password": "seed-owner-1234",
        "name": "샘플 초밥집",
        "phone": "010-0000-0012",
        "address": "서울특별시 강남구 강남대로 410",
        "products": [
            _p("모둠초밥 10피스", "일식", "연어·광어·새우 모둠초밥입니다.", 15000, 8900, 4),
            _p("연어덮밥", "일식", "생연어를 올린 덮밥입니다.", 12000, 7000, 3),
            _p("유자 우동", "일식", "향긋한 유자 우동입니다.", 9000, 5000, 5),
        ],
    },
    {
        "email": "owner4@example.com",
        "password": "seed-owner-1234",
        "name": "샘플 동네반찬",
        "phone": "010-0000-0013",
        "address": "서울특별시 서초구 서초대로 77길 17",
        "products": [
            _p("반찬 3종 세트", "반찬", "멸치볶음·진미채·시금치나물입니다.", 12000, 6000, 6),
            _p("제육볶음 도시락", "도시락", "밥과 제육볶음 도시락입니다.", 8000, 4500, 5),
            _p("계란말이", "반찬", "두툼한 계란말이입니다.", 5000, 2500, 7),
        ],
    },
    {
        "email": "owner5@example.com",
        "password": "seed-owner-1234",
        "name": "샘플 과일가게",
        "phone": "010-0000-0014",
        "address": "서울특별시 강남구 역삼로 120",
        "products": [
            _p("제철 과일컵", "과일", "딸기·포도·키위 과일컵입니다.", 6000, 3000, 10),
            _p("사과 5개", "과일", "흠집이 조금 있는 사과 5개입니다.", 10000, 5000, 4),
            _p("수박 1/4통", "과일", "잘라 둔 수박 1/4통입니다.", 9000, 4000, 3),
        ],
    },
    {
        "email": "owner6@example.com",
        "password": "seed-owner-1234",
        "name": "샘플 카페",
        "phone": "010-0000-0015",
        "address": "서울특별시 강남구 논현로 508",
        "products": [
            _p("치즈케이크 조각", "디저트", "꾸덕한 뉴욕 치즈케이크입니다.", 6500, 3500, 5),
            _p("샌드위치", "브런치", "햄치즈 에그 샌드위치입니다.", 7000, 3900, 6),
            _p("마카롱 4개", "디저트", "색색 마카롱 4개입니다.", 10000, 5500, 4),
            _p("카페라떼", "음료", "고소한 카페라떼입니다.", 5000, 2500, 8),
        ],
    },
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


def ensure_owner_approved(client: httpx.Client, admin_token: str, owner_email: str) -> str:
    owner = find_user(client, admin_token, owner_email, "OWNER")
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


def ensure_store(client: httpx.Client, owner_token: str, address: str) -> tuple[dict, str]:
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
    res = client.post("/v1/stores", json={"pickup_address": address}, headers=auth_header(owner_token))
    if res.status_code != 201:
        raise fail("상점 개설", res)
    return res.json(), "새로 개설"


def ensure_products(client: httpx.Client, owner_token: str, store_id: str, specs: list[dict]) -> dict[str, dict]:
    """샘플 상품을 이름으로 찾아 재사용하고, 없으면 등록한다. 이름 -> 상품."""
    res = client.get(f"/v1/stores/{store_id}/products", params={"page": 1, "size": 100}, headers=auth_header(owner_token))
    if res.status_code != 200:
        raise fail("상품 목록 조회", res)
    existing = {p["name"]: p for p in res.json()["items"]}
    result: dict[str, dict] = {}
    for spec in specs:
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


def ensure_offers(
    client: httpx.Client, owner_token: str, store_id: str, products: dict[str, dict], specs: list[dict]
) -> int:
    """상품마다 판매 중인 할인을 하나씩 보장한다. 판매 중 할인 수를 돌려준다."""
    # 상점주가 조회하면 기본으로 SCHEDULED, ON_SALE, SOLD_OUT, SUSPENDED가 나온다 (진행 중인 할인)
    res = client.get(f"/v1/stores/{store_id}/offers", params={"page": 1, "size": 100}, headers=auth_header(owner_token))
    if res.status_code != 200:
        raise fail("상점 할인 목록 조회", res)
    open_offers = {o["product_id"]: o for o in res.json()["items"]}
    on_sale = 0
    for spec in specs:
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

        summaries: list[tuple[str, int, int]] = []  # (상점명, 판매 중 할인 수, 홈 노출 수)
        for index, spec in enumerate(STORES, start=1):
            print(f"2-{index}. 상점 {index}/{len(STORES)}: {spec['name']}")
            created = signup(
                client, f"상점주 가입 ({spec['email']})",
                email=spec["email"], password=spec["password"], name=spec["name"], phone=spec["phone"], role="OWNER",
            )
            print(f"  - 상점주 {'새로 가입' if created else '이미 있는 계정'}: {spec['email']}")
            print(f"  - 관리자 승인: {ensure_owner_approved(client, admin_token, spec['email'])}")
            owner_token = login(
                client, f"상점주 로그인 ({spec['email']})", spec["email"], spec["password"],
                f"{spec['email']} 계정이 다른 비밀번호로 이미 있으면 이 스크립트의 STORES 비밀번호와 맞추거나 계정을 정리하세요.",
            )["access_token"]
            store, how = ensure_store(client, owner_token, spec["address"])
            print(f"  - 상점 {how}: {store['name']} ({store['pickup_address']}, 위도 {store['latitude']}, 경도 {store['longitude']})")
            products = ensure_products(client, owner_token, store["id"], spec["products"])
            on_sale = ensure_offers(client, owner_token, store["id"], products, spec["products"])
            visible = count_home_offers(client, store["id"])
            print(f"  - 고객 홈에 이 상점 할인 {visible}개가 보입니다.")
            summaries.append((store["name"], on_sale, visible))

        print("3. 고객 가입")
        created = signup(client, "고객 가입", email=CUSTOMER_EMAIL, password=CUSTOMER_PASSWORD, name=CUSTOMER_NAME, phone=CUSTOMER_PHONE, role="CUSTOMER")
        print(f"  - {'새로 가입' if created else '이미 있는 계정'}: {CUSTOMER_EMAIL}")
        login(
            client, "고객 로그인 확인", CUSTOMER_EMAIL, CUSTOMER_PASSWORD,
            f"{CUSTOMER_EMAIL} 계정이 다른 비밀번호로 이미 있으면 이 스크립트의 CUSTOMER_PASSWORD와 맞추세요.",
        )

    print()
    print("=== 샘플 데이터 준비 완료 ===")
    for name, on_sale, visible in summaries:
        print(f"상점: {name} / 판매 중 할인 {on_sale}개 (홈 목록에서 확인 {visible}개)")
    print(f"고객 계정:   {CUSTOMER_EMAIL} / {CUSTOMER_PASSWORD}")
    print("상점주 계정: " + ", ".join(s["email"] for s in STORES) + f" (비밀번호 {STORES[0]['password']})")
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
