"""JWT 위조 토큰 매트릭스와 비밀번호 해싱 점검 (DB 불필요).

    cd src && uv run python ../.claude/skills/auth-security-check/scripts/jwt_matrix.py

정상 토큰은 통과하고, 위조·변조·필수 클레임 누락 토큰은 모두 AuthenticationError(401)로 거부되어야 한다.
"""
import base64
import json
import time
import timeit
import uuid

from _common import Report, use_src

use_src()

import jwt  # noqa: E402

from auth.domain.exceptions import AuthenticationError  # noqa: E402
from auth.infrastructure.security import BcryptPasswordHasher, JwtTokenProvider  # noqa: E402
from auth.infrastructure.settings import get_auth_settings  # noqa: E402


def b64(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()


def main() -> None:
    r = Report("JWT 위조 토큰 매트릭스")
    s = get_auth_settings()
    provider = JwtTokenProvider()
    uid = uuid.uuid4()

    token, _ = provider.issue(uid, "CUSTOMER")
    header = jwt.get_unverified_header(token)
    payload = jwt.decode(token, options={"verify_signature": False})
    r.check(header.get("alg") == "HS256", "발급 알고리즘 HS256", f"header={header}")
    missing = {"sub", "role", "jti", "exp"} - set(payload)
    r.check(not missing, "발급 토큰에 sub·role·jti·exp 포함", f"누락={sorted(missing)}" if missing else "")
    ttl = payload.get("exp", 0) - payload.get("iat", 0)
    r.check(ttl == s.access_token_expire_minutes * 60, "만료 시간이 설정값과 같음", f"{ttl}초")
    try:
        claims = provider.decode(token)
        r.check(claims.user_id == uid, "정상 토큰 검증 통과")
    except AuthenticationError as err:
        r.check(False, "정상 토큰 검증 통과", str(err))

    now = int(time.time())
    base = {"sub": str(uid), "role": "ADMIN", "jti": str(uuid.uuid4()), "exp": now + 600}
    key = s.secret_key
    head, _, sig = token.split(".")
    forged = {
        "alg=none (PyJWT)": jwt.encode(base, None, algorithm="none"),
        "alg=none 수동 작성": b64({"alg": "none", "typ": "JWT"}) + "." + b64(base) + ".",
        "alg=None 대소문자": b64({"alg": "None", "typ": "JWT"}) + "." + b64(base) + ".",
        "다른 시크릿으로 서명": jwt.encode(base, "x" * 40, algorithm="HS256"),
        "같은 시크릿 HS512": jwt.encode(base, key, algorithm="HS512"),
        "만료된 토큰": jwt.encode({**base, "exp": now - 10}, key, algorithm="HS256"),
        "exp 누락": jwt.encode({k: v for k, v in base.items() if k != "exp"}, key, algorithm="HS256"),
        "jti 누락": jwt.encode({k: v for k, v in base.items() if k != "jti"}, key, algorithm="HS256"),
        "sub 누락": jwt.encode({k: v for k, v in base.items() if k != "sub"}, key, algorithm="HS256"),
        "role 누락": jwt.encode({k: v for k, v in base.items() if k != "role"}, key, algorithm="HS256"),
        "sub가 UUID 아님": jwt.encode({**base, "sub": "admin"}, key, algorithm="HS256"),
        "sub가 정수": jwt.encode({**base, "sub": 123}, key, algorithm="HS256"),
        "exp가 문자열": jwt.encode({**base, "exp": "abc"}, key, algorithm="HS256"),
        "페이로드 변조(서명 재사용)": f"{head}.{b64(base)}.{sig}",
        "형식 아님": "abc.def.ghi",
        "빈 문자열": "",
    }
    for name, forged_token in forged.items():
        try:
            result = provider.decode(forged_token)
            r.check(False, f"거부: {name}", f"통과됨 {result}")
        except AuthenticationError as err:
            r.check(True, f"거부: {name}", str(err))
        except Exception as err:  # AuthenticationError가 아니면 500이 된다
            r.check(False, f"거부: {name}", f"401이 아닌 예외 {type(err).__name__}: {err}")


    r.section("비밀번호 해싱")
    hasher = BcryptPasswordHasher()
    hashed = hasher.hash("password123")
    r.check(hashed.startswith("$2"), "bcrypt 해시", hashed[:7])
    r.check(hasher.verify("password123", hashed), "올바른 비밀번호 검증")
    r.check(not hasher.verify("wrong-pass", hashed), "틀린 비밀번호 거부")
    r.check(not hasher.verify("a", "not-a-hash"), "손상된 해시는 예외 없이 False")
    t_real = timeit.timeit(lambda: hasher.verify("wrong-pass", hashed), number=3) / 3
    t_dummy = timeit.timeit(lambda: hasher.dummy_verify("wrong-pass"), number=3) / 3
    ratio = t_dummy / t_real if t_real else 0
    r.check(0.5 < ratio < 2.0, "없는 사용자도 같은 비용으로 검증(타이밍)", f"verify {t_real:.3f}s, dummy {t_dummy:.3f}s")
    if hasher.verify("a" * 73, hasher.hash("a" * 72)):
        r.add("주의", "bcrypt 72바이트 절단", "72바이트 이후 문자는 무시됨. 비밀번호 최대 길이를 72바이트로 제한하거나 안내 필요")
    else:
        r.add("통과", "bcrypt 72바이트 절단 없음")

    r.finish()


if __name__ == "__main__":
    main()
