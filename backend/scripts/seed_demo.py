"""시연용 데이터 생성 스크립트: 가게 3곳 + 음식 사진 상품 6개 + 판매 중 할인.

서버 API(HTTP)만 사용하며 DB에 직접 쓰지 않는다. 다시 실행해도 안전하다
(이미 있는 계정·상점·상품은 재사용하고, 판매 중인 할인이 있으면 새로 만들지 않는다).

사용법 (backend 폴더, 서버가 켜져 있는 상태):
    uv run python scripts/seed_demo.py

환경변수:
    SEED_BASE_URL   서버 주소 (기본 http://localhost:8001)
    ADMIN_EMAIL     관리자 이메일 (없으면 backend/.env, 상위 .env에서 읽음)
    ADMIN_PASSWORD  관리자 비밀번호 (위와 같음)

카카오 키(KAKAO_REST_API_KEY)가 있으면 실제 주소 좌표로, 없으면 서버의 MockGeocoder 좌표로 상점이 개설된다.
사진은 scripts/demo_images/에 있다. 계정은 로컬 시연 전용이며 실제 서비스에서 쓰지 않는다.
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
IMAGE_DIR = Path(__file__).resolve().parent / "demo_images"
FRONTEND_URL = "http://localhost:5173/"

# ── 시연 데이터 상수 (로컬 시연 전용 계정) ──
OWNER_PASSWORD = "demo-owner-1234"
CUSTOMER_EMAIL = "demo-customer@example.com"
CUSTOMER_PASSWORD = "demo-customer-1234"
CUSTOMER_NAME = "시연 고객"

# 상점명은 상점주 이름(상호)으로 정해진다.
STORES = [
    {
        "email": "demo-mangwon@example.com",
        "name": "망원베이커리",
        "phone": "010-1000-0001",
        "address": "서울 마포구 포은로 100",
        "products": [
            {"image": "bread.webp", "name": "식빵 모둠 5종", "category": "베이커리",
             "description": "우유·통밀·밤·옥수수·쌀식빵 모둠", "original_price": 12000, "sale_price": 6000, "stock": 8},
            {"image": "croissant.webp", "name": "버터 크루아상 4개", "category": "베이커리",
             "description": "결이 살아 있는 버터 크루아상", "original_price": 9000, "sale_price": 5400, "stock": 6},
        ],
    },
    {
        "email": "demo-hapjeong@example.com",
        "name": "합정베이커리",
        "phone": "010-1000-0002",
        "address": "서울 마포구 양화로 45",
        "products": [
            {"image": "sandwich.webp", "name": "햄치즈 샌드위치 2개", "category": "샌드위치",
             "description": "햄·치즈·양상추·토마토", "original_price": 8000, "sale_price": 4000, "stock": 5},
            {"image": "salad.webp", "name": "리코타 샐러드", "category": "샐러드",
             "description": "리코타 치즈·방울토마토·견과류", "original_price": 7500, "sale_price": 3700, "stock": 4},
        ],
    },
    {
        "email": "demo-yeonnam@example.com",
        "name": "연남제과",
        "phone": "010-1000-0003",
        "address": "서울 마포구 동교로 251",
        "products": [
            {"image": "cake.webp", "name": "딸기 조각 케이크 2조각", "category": "케이크",
             "description": "생크림 딸기 케이크", "original_price": 6500, "sale_price": 3900, "stock": 3},
            {"image": "bagel.webp", "name": "베이글 3종", "category": "베이커리",
             "description": "플레인·블루베리·어니언, 크림치즈", "original_price": 7000, "sale_price": 3500, "stock": 6},
        ],
    },
]


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
    load_dotenv(BACKEND_DIR / ".env", override=False)
    load_dotenv(BACKEND_DIR.parent / ".env", override=False)
    email = (os.environ.get("ADMIN_EMAIL") or "").strip()
    password = os.environ.get("ADMIN_PASSWORD") or ""
    if not email or not password:
        raise SeedError(
            "[실패] 단계: 관리자 계정 정보 읽기\n"
            "  ADMIN_EMAIL과 ADMIN_PASSWORD를 찾지 못했습니다.\n"
            "  backend/.env에 두 줄을 추가하고 서버를 다시 켠 뒤(서버가 시작할 때 관리자 계정을 만듭니다) 다시 실행하세요.\n"
            "    ADMIN_EMAIL=admin@example.com\n"
            "    ADMIN_PASSWORD=<임의의 비밀번호>"
        )
    return email, password


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client, step: str, email: str, password: str) -> str:
    res = client.post("/v1/auth/login", json={"email": email, "password": password})
    if res.status_code != 200:
        raise fail(step, res)
    return res.json()["access_token"]


def signup(client: httpx.Client, step: str, **body: str) -> bool:
    res = client.post("/v1/auth/signup", json=body)
    if res.status_code == 201:
        return True
    if res.status_code == 409 and error_code(res) == "EMAIL_DUPLICATED":
        return False
    raise fail(step, res)


def ensure_approved(client: httpx.Client, admin: str, email: str) -> str:
    step = f"관리자: 상점주 승인 ({email})"
    res = client.get("/v1/admin/users", params={"role": "OWNER", "email": email, "page": 1, "size": 100}, headers=auth(admin))
    if res.status_code != 200:
        raise fail(step, res)
    owner = next((u for u in res.json()["items"] if u["email"].lower() == email.lower()), None)
    if owner is None:
        raise fail(step, detail=f"{email} 계정이 회원 목록에 없습니다.")
    if owner["status"] == "APPROVED":
        return "이미 승인됨"
    res = client.patch(f"/v1/admin/owners/{owner['id']}/approve", headers=auth(admin))
    if res.status_code != 200:
        raise fail(step, res)
    return "승인"


def ensure_store(client: httpx.Client, token: str, spec: dict) -> dict:
    res = client.get("/v1/stores/me", headers=auth(token))
    if res.status_code == 200:
        store = res.json()
        if store["status"] != "ACTIVE":
            raise fail(f"상점 확인 ({spec['name']})", detail=f"상점 상태가 {store['status']}입니다. 영업 중이 아니면 홈에 보이지 않습니다.")
        print(f"  - 상점 재사용: {store['name']}")
        return store
    res = client.post("/v1/stores", json={"pickup_address": spec["address"]}, headers=auth(token))
    if res.status_code != 201:
        raise fail(f"상점 개설 ({spec['name']})", res)
    store = res.json()
    print(f"  - 상점 개설: {store['name']} ({store['pickup_address']}, 위도 {store['latitude']}, 경도 {store['longitude']})")
    return store


def ensure_product(client: httpx.Client, token: str, store_id: str, spec: dict, existing: dict[str, dict]) -> dict:
    product = existing.get(spec["name"])
    if product is not None:
        if not product.get("is_active", True):
            res = client.post(f"/v1/products/{product['id']}/activate", headers=auth(token))
            if res.status_code != 200:
                raise fail(f"상품 재노출 ({spec['name']})", res)
            print(f"  - 상품 재노출: {spec['name']}")
        else:
            print(f"  - 상품 재사용: {spec['name']}")
        return product
    with open(IMAGE_DIR / spec["image"], "rb") as f:
        res = client.post(
            f"/v1/stores/{store_id}/products",
            headers=auth(token),
            data={"name": spec["name"], "category": spec["category"], "description": spec["description"],
                  "original_price": str(spec["original_price"])},
            files={"file": (spec["image"], f, "image/webp")},
        )
    if res.status_code != 201:
        raise fail(f"상품 등록 ({spec['name']})", res)
    print(f"  - 상품 등록(사진 포함): {spec['name']}")
    return res.json()


def offer_times(index: int) -> dict[str, str]:
    # 지금부터 6시간 동안 판매(상품마다 15분씩 차이), 픽업은 7~9시간 뒤
    now = datetime.now(timezone.utc)
    return {
        "sales_end": (now + timedelta(hours=6, minutes=15 * index)).isoformat(),
        "pickup_start": (now + timedelta(hours=7)).isoformat(),
        "pickup_end": (now + timedelta(hours=9)).isoformat(),
    }


def ensure_offer(client: httpx.Client, token: str, store_id: str, product: dict, spec: dict, index: int) -> None:
    res = client.get(f"/v1/stores/{store_id}/offers", params={"page": 1, "size": 100}, headers=auth(token))
    if res.status_code != 200:
        raise fail(f"할인 목록 ({spec['name']})", res)
    live = [o for o in res.json()["items"] if o["product_id"] == product["id"] and o["status"] in ("ON_SALE", "SCHEDULED")]
    if live:
        print(f"  - 할인 재사용: {spec['name']} (남은 수량 {live[0]['remaining_stock']}개)")
        return
    res = client.post(
        f"/v1/products/{product['id']}/offers",
        headers=auth(token),
        json={"sale_price": spec["sale_price"], "initial_stock": spec["stock"], **offer_times(index)},
    )
    if res.status_code != 201:
        raise fail(f"할인 등록 ({spec['name']})", res)
    print(f"  - 할인 등록: {spec['name']} {spec['original_price']}원 -> {spec['sale_price']}원, {spec['stock']}개")


def run(base_url: str) -> None:
    admin_email, admin_password = load_admin_credentials()
    with httpx.Client(base_url=base_url, timeout=30) as client:
        print("1. 관리자 로그인")
        admin = login(client, "관리자 로그인", admin_email, admin_password)
        for spec in STORES:
            print(f"2. {spec['name']}")
            created = signup(client, f"상점주 가입 ({spec['name']})", email=spec["email"], password=OWNER_PASSWORD,
                             name=spec["name"], phone=spec["phone"], role="OWNER")
            print(f"  - {'새로 가입' if created else '이미 있는 계정'}: {spec['email']}")
            print(f"  - {ensure_approved(client, admin, spec['email'])}")
            token = login(client, f"상점주 로그인 ({spec['name']})", spec["email"], OWNER_PASSWORD)
            store = ensure_store(client, token, spec)
            res = client.get(f"/v1/stores/{store['id']}/products", params={"page": 1, "size": 100}, headers=auth(token))
            if res.status_code != 200:
                raise fail(f"상품 목록 ({spec['name']})", res)
            existing = {p["name"]: p for p in res.json()["items"]}
            for i, product_spec in enumerate(spec["products"]):
                product = ensure_product(client, token, store["id"], product_spec, existing)
                ensure_offer(client, token, store["id"], product, product_spec, i)
        print("3. 고객 계정")
        created = signup(client, "고객 가입", email=CUSTOMER_EMAIL, password=CUSTOMER_PASSWORD,
                         name=CUSTOMER_NAME, phone="010-1000-0009", role="CUSTOMER")
        print(f"  - {'새로 가입' if created else '이미 있는 계정'}: {CUSTOMER_EMAIL}")
    print()
    print("완료. 확인할 주소:", FRONTEND_URL, "(가게별 보기:", FRONTEND_URL + "?view=store)")
    print(f"  상점주: {', '.join(s['email'] for s in STORES)} / 비밀번호 {OWNER_PASSWORD}")
    print(f"  고객: {CUSTOMER_EMAIL} / 비밀번호 {CUSTOMER_PASSWORD}")


def main() -> int:
    base_url = os.environ.get("SEED_BASE_URL", "http://localhost:8001").rstrip("/")
    try:
        run(base_url)
    except SeedError as error:
        print(error, file=sys.stderr)
        return 1
    except httpx.ConnectError:
        print(f"[실패] 서버에 연결할 수 없습니다: {base_url}\n  서버를 먼저 켜세요.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
