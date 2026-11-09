"""auth API를 ASGI로 직접 호출하는 E2E 보안 점검 (서버 실행 불필요, PostgreSQL 필요).

    cd src && uv run python ../.claude/skills/auth-security-check/scripts/e2e_auth.py [--keep]

매 실행마다 고유 이메일(sec-<랜덤>@example.com)로 가입하고, 끝나면 만든 회원과 블랙리스트 행을 지운다.
--keep을 주면 지우지 않는다.
"""
import asyncio
import sys
import uuid

from _common import Report, use_src

use_src()

import httpx  # noqa: E402
import jwt  # noqa: E402
from sqlalchemy import text  # noqa: E402

from auth.infrastructure.security import JwtTokenProvider  # noqa: E402
from database import engine  # noqa: E402
from main import app  # noqa: E402

LOGIN = "/v1/auth/login"
PW = "password123"


def is_error(res: httpx.Response, code: str) -> bool:
    try:
        body = res.json()
    except ValueError:
        return False
    return body.get("success") is False and body.get("error_code") == code and bool(body.get("message"))


def bearer(res: httpx.Response) -> bool:
    return res.headers.get("www-authenticate", "").lower().startswith("bearer")


async def run(r: Report, keep: bool) -> None:
    tag = uuid.uuid4().hex[:10]
    email = f"sec-{tag}@example.com"
    owner_email = f"sec-owner-{tag}@example.com"
    created = [email, owner_email]
    jtis: list[str] = []

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            try:
                r.section("회원가입")
                res = await c.post("/v1/auth/signup", json={"email": email, "password": PW, "name": "보안점검", "phone": "010-0000-0000", "role": "CUSTOMER"})
                r.check(res.status_code == 201, "가입 201", str(res.status_code))
                r.check(not any("password" in k for k in res.json()), "가입 응답에 password 없음", str(sorted(res.json())))
                res = await c.post("/v1/auth/signup", json={"email": f"sec-adm-{tag}@example.com", "password": PW, "name": "보안점검", "phone": "010-0000-0000", "role": "ADMIN"})
                r.check(res.status_code == 400 and is_error(res, "VALIDATION_ERROR"), "ADMIN 가입 거부 400", str(res.status_code))
                res = await c.post("/v1/auth/signup", json={"email": owner_email, "password": PW, "name": "보안점검", "phone": "010-0000-0000", "role": "OWNER"})
                if res.status_code == 201:
                    r.add("주의", "누구나 OWNER로 가입 가능", "상점주 승인 절차 없음 (stores 구현 시 승인 상태 확인 필요)")
                else:
                    r.add("통과", "OWNER 가입 제한", str(res.status_code))

                r.section("로그인")
                r1 = await c.post(LOGIN, json={"email": email, "password": "wrong-pass"})
                r2 = await c.post(LOGIN, json={"email": f"nouser-{email}", "password": "wrong-pass"})
                r.check(r1.status_code == 401 and is_error(r1, "INVALID_CREDENTIALS"), "비밀번호 틀림 401 INVALID_CREDENTIALS")
                r.check(r2.status_code == 401 and is_error(r2, "INVALID_CREDENTIALS"), "없는 사용자 401 INVALID_CREDENTIALS")
                r.check(r1.json() == r2.json(), "로그인 실패 2종 본문 동일 (계정 존재 여부 비노출)")
                # REQ-13: 연속 5회 실패 -> 10분 잠금. 잠긴 사실은 비밀번호가 맞을 때만 429(REQ-13-1). 별도 계정으로 확인한다.
                lock_email = f"sec-lock-{tag}@example.com"
                await c.post("/v1/auth/signup", json={"email": lock_email, "password": PW, "name": "보안점검", "phone": "010-0000-0000", "role": "CUSTOMER"})
                statuses = [(await c.post(LOGIN, json={"email": lock_email, "password": "wrong-pass"})).status_code for _ in range(7)]
                r.check(set(statuses) == {401}, "잠금 뒤에도 틀린 비밀번호는 401 (잠김 비노출, REQ-13-1)", str(statuses))
                res = await c.post(LOGIN, json={"email": lock_email, "password": PW})
                r.check(res.status_code == 429 and is_error(res, "ACCOUNT_LOCKED") and res.headers.get("retry-after", "").isdigit()
                        and not res.headers.get("www-authenticate"),
                        "연속 5회 실패 뒤 맞는 비밀번호 429 ACCOUNT_LOCKED + Retry-After (REQ-13)", f"{res.status_code} {res.headers.get('retry-after')}")
                res = await c.post(LOGIN, json={"email": email, "password": PW})
                body = res.json()
                r.check(res.status_code == 200 and body.get("token_type") == "bearer" and body.get("access_token"),
                        "로그인 성공 access_token + token_type=bearer")
                token = body.get("access_token", "")
                if token:
                    jtis.append(jwt.decode(token, options={"verify_signature": False}).get("jti", ""))
                auth = {"Authorization": f"Bearer {token}"}

                r.section("토큰 검증")
                res = await c.get("/v1/users/me", headers=auth)
                r.check(res.status_code == 200, "정상 토큰 200", str(res.status_code))
                for name, headers in {
                    "Authorization 없음": {},
                    "Basic 스킴": {"Authorization": "Basic abc"},
                    "형식 아닌 토큰": {"Authorization": "Bearer abc"},
                }.items():
                    res = await c.get("/v1/users/me", headers=headers)
                    r.check(res.status_code == 401 and bearer(res) and is_error(res, "UNAUTHORIZED"),
                            f"{name} → 401 + WWW-Authenticate: Bearer", f"{res.status_code} {res.headers.get('www-authenticate')}")
                ghost, _ = JwtTokenProvider().issue(uuid.uuid4(), "ADMIN")
                res = await c.get("/v1/users/me", headers={"Authorization": f"Bearer {ghost}"})
                r.check(res.status_code == 401 and bearer(res), "서명은 유효하지만 없는 사용자 → 401", str(res.status_code))

                r.section("로그아웃과 블랙리스트")
                res = await c.post("/v1/auth/logout", headers=auth)
                r.check(res.status_code == 204, "로그아웃 204", str(res.status_code))
                res = await c.get("/v1/users/me", headers=auth)
                r.check(res.status_code == 401 and bearer(res) and is_error(res, "TOKEN_REVOKED"),
                        "로그아웃한 토큰 재사용 → 401 TOKEN_REVOKED + WWW-Authenticate", str(res.status_code))
                res = await c.post("/v1/auth/logout", headers=auth)
                r.check(res.status_code == 401, "로그아웃 두 번 → 401", str(res.status_code))

                async with engine.connect() as conn:
                    row = (await conn.execute(text("select password_hash from users where email=:e"), {"e": email})).one()
                    r.check(row[0].startswith("$2") and row[0] != PW, "DB에 bcrypt 해시로 저장 (평문 아님)", row[0][:7])
                    n = (await conn.execute(text("select count(*) from token_blacklist where jti=:j"), {"j": jtis[0] if jtis else ""})).scalar()
                    r.check(n == 1, "블랙리스트에 jti 저장", f"{n}행")

                r.section("OpenAPI")
                spec = (await c.get("/openapi.json")).json()
                schemes = spec.get("components", {}).get("securitySchemes", {})
                # 로그인은 JSON이라 Swagger Authorize는 OAuth2 password flow가 아니라 HTTP Bearer(토큰 붙여 넣기)여야 한다.
                kinds = [(s.get("type"), s.get("scheme")) for s in schemes.values()]
                r.check(bool(kinds) and all(k == ("http", "bearer") for k in kinds) and LOGIN in spec["paths"],
                        "securitySchemes가 HTTP Bearer뿐 (JSON 로그인과 Swagger Authorize 호환)", str(kinds))
                leaked = [k for k, v in spec["components"]["schemas"].items()
                          if k.endswith("Response") and any("password" in p for p in v.get("properties", {}))]
                r.check(not leaked, "Response 스키마에 password 필드 없음", str(leaked) if leaked else "")
            finally:
                if not keep:
                    async with engine.begin() as conn:
                        await conn.execute(text("delete from token_blacklist where jti = any(:j)"), {"j": [j for j in jtis if j]})
                        await conn.execute(text("delete from point_log where user_id in (select id from users where email = any(:e))"), {"e": created})
                        await conn.execute(text("delete from users where email = any(:e)"), {"e": created})
                    print(f"\n(정리) 테스트 회원 {created}와 블랙리스트 행을 지웠습니다.")


def main() -> None:
    r = Report("auth E2E 보안 점검")
    asyncio.run(run(r, keep="--keep" in sys.argv))
    r.finish()


if __name__ == "__main__":
    main()
