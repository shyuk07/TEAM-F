"""4계층 아키텍처 규칙 자동 검사.

사용법 (프로젝트 루트에서):
    python3 .claude/skills/layer-check/check_layers.py [src 경로]

검사 대상:
  - 기능 모듈: src/ 바로 아래에서 계층 폴더(domain 등)가 하나라도 있는 폴더
  - 공용 패키지: src/common/ (4계층 폴더를 요구하지 않음)
  - src 루트 파일: main.py(조립 지점)를 뺀 나머지 (database.py, error_handlers.py 등)
  - templates, static, last_call은 검사하지 않음

위반(종료 코드에 반영):
  1. 기능 모듈에 domain/infrastructure/application/presentation 폴더와 __init__.py가 있는가
  2. 계층 간 import 방향, 계층별 금지 외부 패키지
  3. common과 src 루트 파일이 기능 모듈의 infrastructure/application/presentation을 import하지 않는가
  4. domain·application에서 HTTPException을 쓰지 않는가
  5. infrastructure 레포지토리의 find_* 메서드가 *Model을 반환 타입으로 적지 않는가

경고(종료 코드에 반영하지 않음):
  - 전역 예외 핸들러가 ValueError, LookupError, PermissionError, Exception을 그대로 잡음
  - find_* 메서드에 반환 타입 어노테이션이 없음

위반이 있으면 종료 코드 1, 없으면 0, src 폴더가 없으면 2를 반환합니다.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

LAYERS = ("domain", "infrastructure", "application", "presentation")
NON_MODULE_DIRS = {"templates", "static", "last_call", "__pycache__"}
COMMON_DIR = "common"
ROOT_EXEMPT_FILES = {"main.py"}  # 모든 모듈을 조립하는 곳이라 import 제한을 두지 않는다

# 계층별로 참조하면 안 되는 다른 계층
FORBIDDEN_LAYERS = {
    "domain": {"infrastructure", "application", "presentation"},
    "infrastructure": {"application", "presentation"},
    "application": {"presentation"},
    "presentation": {"infrastructure"},
    # 공용 코드는 기능 모듈의 domain(예외 클래스 등)만 참조할 수 있다
    COMMON_DIR: {"infrastructure", "application", "presentation"},
}

# 계층별로 import하면 안 되는 최상위 패키지
FORBIDDEN_PACKAGES = {
    "domain": {"fastapi", "starlette", "sqlalchemy", "pydantic", "database", "jinja2", "jwt", "passlib"},
    "infrastructure": {"fastapi", "starlette"},
    "application": {"fastapi", "starlette"},
    "presentation": set(),
    COMMON_DIR: set(),
}

HTTP_EXCEPTION_FORBIDDEN = {"domain", "application"}
BROAD_EXCEPTIONS = {"ValueError", "LookupError", "PermissionError", "Exception", "BaseException"}


def resolve_relative(file_parts: tuple[str, ...], level: int, module: str | None) -> list[str]:
    """상대 import를 src 기준 절대 경로 조각으로 바꾼다."""
    package = list(file_parts[:-1])  # 파일명 제외
    if level > 1:
        package = package[: len(package) - (level - 1)]
    return package + (module.split(".") if module else [])


def imported_targets(tree: ast.AST, file_parts: tuple[str, ...]) -> list[tuple[int, list[str]]]:
    targets: list[tuple[int, list[str]]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append((node.lineno, alias.name.split(".")))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = resolve_relative(file_parts, node.level, node.module)
            else:
                base = (node.module or "").split(".")
            targets.append((node.lineno, base))
            # `from catalog import domain` 같은 형태도 잡는다
            for alias in node.names:
                targets.append((node.lineno, base + [alias.name]))
    return targets


def annotation_names(node: ast.AST | None) -> list[str]:
    """어노테이션에 나오는 이름을 모은다. 문자열 어노테이션도 풀어서 본다."""
    if node is None:
        return []
    names: list[str] = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Name):
            names.append(sub.id)
        elif isinstance(sub, ast.Attribute):
            names.append(sub.attr)
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            try:
                names.extend(annotation_names(ast.parse(sub.value, mode="eval")))
            except SyntaxError:
                pass
    return names


def handler_exception_name(node: ast.AST) -> str | None:
    """`x.exception_handler(E)` 또는 `x.add_exception_handler(E, ...)`에서 E 이름을 꺼낸다."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    if node.func.attr not in ("exception_handler", "add_exception_handler") or not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Name):
        return arg.id
    if isinstance(arg, ast.Attribute):  # builtins.ValueError 같은 형태
        return arg.attr
    return None


class Checker:
    def __init__(self, src: Path):
        self.src = src
        self.violations: list[str] = []
        self.warnings: list[str] = []
        self.checked = 0
        self.modules = sorted(
            p.name for p in src.iterdir()
            if p.is_dir() and p.name not in NON_MODULE_DIRS and p.name != COMMON_DIR
            and not p.name.startswith(".")
            and any((p / layer).is_dir() for layer in LAYERS)
        )

    # ---------- 구조 ----------
    def check_structure(self) -> None:
        for mod in self.modules:
            mod_dir = self.src / mod
            if not (mod_dir / "__init__.py").exists():
                self.violations.append(f"[구조] {mod}/__init__.py 없음")
            for layer in LAYERS:
                layer_dir = mod_dir / layer
                if not layer_dir.is_dir():
                    self.violations.append(f"[구조] {mod}/{layer}/ 폴더 없음")
                elif not (layer_dir / "__init__.py").exists():
                    self.violations.append(f"[구조] {mod}/{layer}/__init__.py 없음")
        common = self.src / COMMON_DIR
        if common.is_dir() and not (common / "__init__.py").exists():
            self.violations.append(f"[구조] {COMMON_DIR}/__init__.py 없음")

    # ---------- 파일 단위 ----------
    def iter_targets(self):
        """(파일, 역할) 쌍을 돌려준다. 역할은 계층 이름 또는 common."""
        for mod in self.modules:
            for layer in LAYERS:
                layer_dir = self.src / mod / layer
                if layer_dir.is_dir():
                    for py in sorted(layer_dir.rglob("*.py")):
                        if "__pycache__" not in py.parts:
                            yield py, layer
        common = self.src / COMMON_DIR
        if common.is_dir():
            for py in sorted(common.rglob("*.py")):
                if "__pycache__" not in py.parts:
                    yield py, COMMON_DIR
        for py in sorted(self.src.glob("*.py")):
            yield py, None if py.name in ROOT_EXEMPT_FILES else COMMON_DIR

    def check_file(self, py: Path, role: str | None) -> None:
        rel = py.relative_to(self.src)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(rel))
        except SyntaxError as err:
            self.violations.append(f"[문법] {rel}:{err.lineno} 파싱 실패: {err.msg}")
            return
        self.checked += 1
        self.check_exception_handlers(tree, rel)  # 역할과 상관없이 모든 파일
        if role is None:
            return
        self.check_imports(tree, rel, role)
        if role in HTTP_EXCEPTION_FORBIDDEN:
            self.check_http_exception(tree, rel, role)
        if role == "infrastructure" and (py.name == "repositories.py" or "repositories" in rel.parts):
            self.check_repository_returns(tree, rel)

    def check_imports(self, tree: ast.AST, rel: Path, role: str) -> None:
        label = "src 루트" if len(rel.parts) == 1 else role
        seen: set[tuple[int, str]] = set()
        for lineno, parts in imported_targets(tree, rel.parts):
            if not parts or not parts[0]:
                continue
            top = parts[0]
            if top in FORBIDDEN_PACKAGES[role] and (lineno, top) not in seen:
                seen.add((lineno, top))
                self.violations.append(f"[외부의존] {rel}:{lineno} {label} 계층에서 '{top}' import 금지")
            if top in self.modules and len(parts) > 1 and parts[1] in FORBIDDEN_LAYERS[role]:
                key = (lineno, f"{top}.{parts[1]}")
                if key not in seen:
                    seen.add(key)
                    self.violations.append(f"[의존방향] {rel}:{lineno} {label} → {top}.{parts[1]} 참조 금지")

    def check_http_exception(self, tree: ast.AST, rel: Path, role: str) -> None:
        # import 줄은 [외부의존]이 잡으므로 사용 지점(Name/Attribute)만 본다.
        # common 등을 거쳐 다시 내보낸 HTTPException도 여기서 걸린다.
        lines = sorted({
            node.lineno for node in ast.walk(tree)
            if (isinstance(node, ast.Name) and node.id == "HTTPException")
            or (isinstance(node, ast.Attribute) and node.attr == "HTTPException")
        })
        for lineno in lines:
            self.violations.append(
                f"[HTTP예외] {rel}:{lineno} {role} 계층에서 HTTPException 사용 금지 (도메인 예외를 내고 핸들러에서 변환)"
            )

    def check_repository_returns(self, tree: ast.AST, rel: Path) -> None:
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.name.startswith("find_"):
                continue
            if node.returns is None:
                self.warnings.append(f"[반환타입] {rel}:{node.lineno} {node.name}()에 반환 타입 어노테이션 없음")
                continue
            models = [n for n in annotation_names(node.returns) if n.endswith("Model")]
            if models:
                self.violations.append(
                    f"[레포반환] {rel}:{node.lineno} {node.name}()의 반환 타입에 {models[0]} 사용 (도메인 객체로 변환해 반환)"
                )

    def check_exception_handlers(self, tree: ast.AST, rel: Path) -> None:
        for node in ast.walk(tree):
            name = handler_exception_name(node)
            if name in BROAD_EXCEPTIONS:
                self.warnings.append(
                    f"[넓은예외] {rel}:{node.lineno} 전역 핸들러가 내장 예외 {name}을(를) 그대로 잡음 "
                    f"(라이브러리 내부 오류도 같은 응답으로 바뀜. 프로젝트 전용 예외 클래스를 권장)"
                )

    def run(self) -> int:
        self.check_structure()
        for py, role in self.iter_targets():
            self.check_file(py, role)

        print(f"검사한 모듈: {', '.join(self.modules) or '(없음)'}")
        extra = []
        if (self.src / COMMON_DIR).is_dir():
            extra.append(f"{COMMON_DIR}/")
        roots = [p.name for p in sorted(self.src.glob("*.py")) if p.name not in ROOT_EXEMPT_FILES]
        if roots:
            extra.append("루트 파일 " + ", ".join(roots) + " (main.py는 import 제한 제외)")
        if extra:
            print(f"공용 검사: {'; '.join(extra)}")
        print(f"검사한 파일: {self.checked}개")

        if self.warnings:
            print(f"\n경고 {len(self.warnings)}건 (종료 코드에 영향 없음)")
            for w in self.warnings:
                print(f"  - {w}")
        if self.violations:
            print(f"\n위반 {len(self.violations)}건")
            for v in self.violations:
                print(f"  - {v}")
            return 1
        print("\n위반 없음")
        return 0


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "src").resolve()
    if not src.is_dir():
        print(f"[오류] src 폴더를 찾을 수 없습니다: {src}")
        return 2
    return Checker(src).run()


if __name__ == "__main__":
    sys.exit(main())
