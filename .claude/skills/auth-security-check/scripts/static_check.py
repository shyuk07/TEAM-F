"""auth 관련 정적 보안 검사 (DB·서버 불필요).

    cd src && uv run python ../.claude/skills/auth-security-check/scripts/static_check.py

- .env가 git에 커밋되지 않았고 .gitignore에 있는지
- .env.example의 JWT_SECRET_KEY를 설정 검증(get_auth_settings)이 거부하는지
- CORSMiddleware에서 allow_origins="*"와 allow_credentials=True를 같이 쓰지 않는지
- jwt.decode 호출마다 algorithms=를 명시했는지
- 시크릿·비밀번호 문자열을 코드에 하드코딩하지 않았는지
- 로깅 미들웨어가 Authorization 헤더나 비밀번호를 남기지 않는지 (미들웨어가 있을 때만)
- 만료된 블랙리스트 정리(purge_expired_tokens)를 호출하는 곳이 있는지
"""
import ast
import os
import re
import subprocess

from _common import ROOT, SRC, Report, use_src

use_src()

SECRET_NAME = re.compile(r"(secret|password|passwd|api_key|token)", re.I)


def py_files():
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def where(path, node) -> str:
    return f"{path.relative_to(ROOT)}:{node.lineno}"


def call_name(node: ast.Call) -> str:
    f = node.func
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
        return f"{f.value.id}.{f.attr}"
    if isinstance(f, ast.Attribute):
        return f.attr
    return f.id if isinstance(f, ast.Name) else ""


def kw(node: ast.Call, name: str):
    return next((k.value for k in node.keywords if k.arg == name), None)


def main() -> None:
    r = Report("auth 정적 보안 검사")
    files = list(py_files())

    r.section(".env와 시크릿")
    tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    r.check(tracked == "", ".env가 git에 커밋되지 않음 (git ls-files .env 비어 있음)", tracked)
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines() if (ROOT / ".gitignore").exists() else []
    r.check(any(line.strip() in (".env", "/.env", ".env*") for line in gitignore), ".gitignore에 .env 포함")

    example = ROOT / ".env.example"
    sample = next((line.split("=", 1)[1].strip() for line in example.read_text(encoding="utf-8").splitlines()
                   if line.startswith("JWT_SECRET_KEY=")), None) if example.exists() else None
    if sample is None:
        r.add("해당없음", ".env.example 예시 시크릿 거부", "JWT_SECRET_KEY 항목 없음")
    else:
        from auth.infrastructure.settings import get_auth_settings

        saved = os.environ.get("JWT_SECRET_KEY")
        os.environ["JWT_SECRET_KEY"] = sample  # load_dotenv는 이미 있는 환경변수를 덮어쓰지 않는다
        get_auth_settings.cache_clear()
        try:
            get_auth_settings()
            r.check(False, ".env.example 예시 시크릿을 설정 검증이 거부", "예시값으로 서버가 뜸")
        except RuntimeError as err:
            r.check(True, ".env.example 예시 시크릿을 설정 검증이 거부", str(err))
        finally:
            if saved is None:
                os.environ.pop("JWT_SECRET_KEY", None)
            else:
                os.environ["JWT_SECRET_KEY"] = saved
            get_auth_settings.cache_clear()

    hardcoded = []
    for path, tree in files:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and call_name(node) == "jwt.encode" and len(node.args) >= 2 \
                    and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str):
                hardcoded.append(f"{where(path, node)} jwt.encode 키가 문자열 상수")
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(getattr(node, "value", None), ast.Constant):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                value = node.value.value
                for t in targets:
                    name = t.id if isinstance(t, ast.Name) else getattr(t, "attr", "")
                    if SECRET_NAME.search(name) and isinstance(value, str) and len(value) >= 8:
                        hardcoded.append(f"{where(path, node)} {name} = '{value[:6]}...'")
    r.check(not hardcoded, "시크릿·비밀번호 하드코딩 없음", "; ".join(hardcoded))

    r.section("JWT 디코딩")
    decodes = []
    for path, tree in files:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and call_name(node) == "jwt.decode":
                opts = kw(node, "options")
                unverified = isinstance(opts, ast.Dict) and any(
                    isinstance(k, ast.Constant) and k.value == "verify_signature" for k in opts.keys)
                decodes.append((where(path, node), kw(node, "algorithms") is not None or unverified))
    if not decodes:
        r.add("해당없음", "jwt.decode에 algorithms= 명시", "jwt.decode 호출 없음")
    for loc, ok in decodes:
        r.check(ok, "jwt.decode에 algorithms= 명시", loc)

    r.section("CORS")
    cors = []
    for path, tree in files:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Name) \
                    and node.args[0].id == "CORSMiddleware":
                cors.append((path, node))
    if not cors:
        r.add("해당없음", "CORS allow_origins=* 와 allow_credentials=True 동시 사용 금지", "CORSMiddleware 미구현")
    for path, node in cors:
        origins, cred = kw(node, "allow_origins"), kw(node, "allow_credentials")
        star = isinstance(origins, (ast.List, ast.Tuple)) and any(
            isinstance(e, ast.Constant) and e.value == "*" for e in origins.elts)
        with_cred = isinstance(cred, ast.Constant) and cred.value is True
        r.check(not (star and with_cred), "CORS allow_origins=* 와 allow_credentials=True 동시 사용 금지", where(path, node))

    r.section("로깅")
    middleware = [(p, t) for p, t in files if re.search(r"@app\.middleware|BaseHTTPMiddleware", p.read_text(encoding="utf-8"))]
    if not middleware:
        r.add("해당없음", "로깅 미들웨어가 Authorization·비밀번호를 남기지 않음", "미들웨어 미구현")
    for path, _ in middleware:
        text = path.read_text(encoding="utf-8")
        leaks = re.findall(r"(log\w*|print)\([^)]*(authorization|password|request\.headers|await request\.body)", text, re.I)
        r.check(not leaks, "로깅 미들웨어가 Authorization·비밀번호를 남기지 않음",
                f"{path.relative_to(ROOT)} {leaks}" if leaks else str(path.relative_to(ROOT)))

    r.section("블랙리스트 정리")
    callers = [where(p, n) for p, t in files for n in ast.walk(t)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "purge_expired_tokens"]
    if callers:
        r.add("통과", "만료된 블랙리스트 정리 호출", ", ".join(callers))
    else:
        r.add("주의", "만료된 블랙리스트 정리 호출 없음", "purge_expired_tokens를 lifespan·스케줄러 등에서 호출하지 않아 token_blacklist가 계속 쌓임")

    r.finish()


if __name__ == "__main__":
    main()
