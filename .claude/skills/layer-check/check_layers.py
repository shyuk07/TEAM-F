"""4계층 아키텍처 규칙 자동 검사.

사용법 (프로젝트 루트에서):
    python3 .claude/skills/layer-check/check_layers.py [src 경로]

검사 항목:
  1. 모든 기능 모듈에 domain/infrastructure/application/presentation 폴더가 있는가
  2. 모든 패키지 폴더에 __init__.py가 있는가
  3. 계층 간 import 방향이 규칙을 지키는가
  4. 계층별로 금지된 외부 라이브러리를 import하지 않는가

위반이 있으면 종료 코드 1, 없으면 0을 반환합니다.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

LAYERS = ("domain", "infrastructure", "application", "presentation")
NON_MODULE_DIRS = {"templates", "static", "last_call", "__pycache__"}

# 계층별로 참조하면 안 되는 다른 계층
FORBIDDEN_LAYERS = {
    "domain": {"infrastructure", "application", "presentation"},
    "infrastructure": {"application", "presentation"},
    "application": {"presentation"},
    "presentation": {"infrastructure"},
}

# 계층별로 import하면 안 되는 최상위 패키지
FORBIDDEN_PACKAGES = {
    "domain": {"fastapi", "starlette", "sqlalchemy", "pydantic", "database", "jinja2", "jwt", "passlib"},
    "infrastructure": {"fastapi", "starlette"},
    "application": {"fastapi", "starlette"},
    "presentation": set(),
}


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


def main() -> int:
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "src").resolve()
    if not src.is_dir():
        print(f"[오류] src 폴더를 찾을 수 없습니다: {src}")
        return 2

    modules = sorted(
        p.name for p in src.iterdir()
        if p.is_dir() and p.name not in NON_MODULE_DIRS and not p.name.startswith(".")
        and any((p / layer).is_dir() for layer in LAYERS)
    )
    violations: list[str] = []

    # 1·2. 폴더 구조와 __init__.py
    for mod in modules:
        mod_dir = src / mod
        if not (mod_dir / "__init__.py").exists():
            violations.append(f"[구조] {mod}/__init__.py 없음")
        for layer in LAYERS:
            layer_dir = mod_dir / layer
            if not layer_dir.is_dir():
                violations.append(f"[구조] {mod}/{layer}/ 폴더 없음")
            elif not (layer_dir / "__init__.py").exists():
                violations.append(f"[구조] {mod}/{layer}/__init__.py 없음")

    # 3·4. import 규칙
    checked = 0
    for mod in modules:
        for layer in LAYERS:
            layer_dir = src / mod / layer
            if not layer_dir.is_dir():
                continue
            for py in sorted(layer_dir.rglob("*.py")):
                if "__pycache__" in py.parts:
                    continue
                rel = py.relative_to(src)
                try:
                    tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(rel))
                except SyntaxError as err:
                    violations.append(f"[문법] {rel}:{err.lineno} 파싱 실패: {err.msg}")
                    continue
                checked += 1
                seen: set[tuple[int, str]] = set()
                for lineno, parts in imported_targets(tree, rel.parts):
                    if not parts or not parts[0]:
                        continue
                    top = parts[0]
                    if top in FORBIDDEN_PACKAGES[layer] and (lineno, top) not in seen:
                        seen.add((lineno, top))
                        violations.append(
                            f"[외부의존] {rel}:{lineno} {layer} 계층에서 '{top}' import 금지"
                        )
                    if top in modules and len(parts) > 1 and parts[1] in FORBIDDEN_LAYERS[layer]:
                        key = (lineno, f"{top}.{parts[1]}")
                        if key not in seen:
                            seen.add(key)
                            violations.append(
                                f"[의존방향] {rel}:{lineno} {layer} → {top}.{parts[1]} 참조 금지"
                            )

    print(f"검사한 모듈: {', '.join(modules) or '(없음)'}")
    print(f"검사한 파일: {checked}개")
    if violations:
        print(f"\n위반 {len(violations)}건")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("\n위반 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
