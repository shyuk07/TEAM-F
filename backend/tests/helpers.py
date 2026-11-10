"""API 테스트 공용 헬퍼 (fixture 아님)."""

from sqlalchemy import text


async def signup(c, email="user@test.com", role="CUSTOMER", password="password123", **extra):
    return await c.post(
        "/v1/auth/signup",
        json={"email": email, "password": password, "role": role, "name": "홍길동", "phone": "010-0000-0000", **extra},
    )


async def login(c, email="user@test.com", password="password123"):
    return await c.post("/v1/auth/login", json={"email": email, "password": password})


async def approve_owner(c, email):
    """가입한 상점주를 승인 상태로 만든다 (D4: OWNER 가입은 PENDING). 승인 EP는 admin 모듈 담당이라 직접 UPDATE."""
    async with c.session_factory() as session:
        await session.execute(
            text("UPDATE users SET status = 'APPROVED', approved_at = now() WHERE email = :e"),
            {"e": email.strip().lower()},
        )
        await session.commit()


async def token_for(c, email="user@test.com", role="CUSTOMER"):
    """가입 + 로그인 토큰. OWNER는 승인된 상점주로 만든다."""
    await signup(c, email, role)
    if role == "OWNER":
        await approve_owner(c, email)
    return (await login(c, email)).json()["access_token"]


def bearer(t):
    return {"Authorization": f"Bearer {t}"}
