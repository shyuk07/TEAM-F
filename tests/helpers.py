"""API 테스트 공용 헬퍼 (fixture 아님)."""


async def signup(c, email="user@test.com", role="CUSTOMER", password="password123", **extra):
    return await c.post(
        "/v1/auth/signup",
        json={"email": email, "password": password, "role": role, "name": "홍길동", **extra},
    )


async def login(c, email="user@test.com", password="password123"):
    return await c.post("/v1/auth/login", json={"email": email, "password": password})


async def token_for(c, email="user@test.com", role="CUSTOMER"):
    await signup(c, email, role)
    return (await login(c, email)).json()["access_token"]


def bearer(t):
    return {"Authorization": f"Bearer {t}"}
