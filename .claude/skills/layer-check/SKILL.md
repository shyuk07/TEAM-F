---
name: layer-check
description: 마감 직전 프로젝트의 4계층 구조와 계층 간 import 방향을 자동으로 검사합니다. 코드를 작성하거나 수정한 뒤, PR이나 머지 전에, 또는 "계층 구조 확인", "의존성 규칙 검사"를 요청받았을 때 사용합니다.
---

# 4계층 규칙 검사

## 실행
프로젝트 루트에서 실행합니다. 외부 라이브러리 없이 표준 라이브러리(`ast`)만 씁니다.

```bash
python3 .claude/skills/layer-check/check_layers.py            # 기본: ./src
python3 .claude/skills/layer-check/check_layers.py 다른/src    # 복사한 트리 등 다른 경로
```

종료 코드: `0` 위반 없음, `1` 위반 있음, `2` `src/` 없음. **경고는 종료 코드에 영향을 주지 않습니다.**

## 검사 대상
| 대상 | 판단 기준 | 검사 내용 |
| --- | --- | --- |
| 기능 모듈 | `src/` 바로 아래에서 계층 폴더가 하나라도 있는 폴더 (auth, stores, catalog, reservations, payments) | 4개 계층 폴더와 `__init__.py`, import 방향, 금지 패키지 |
| 공용 패키지 | `src/common/` | `__init__.py`, import 방향 (4계층 폴더는 요구하지 않음) |
| src 루트 파일 | `database.py`, `error_handlers.py` 등 | common과 같은 import 규칙 |
| 조립 지점 | `src/main.py`, `src/container.py` | import 제한 없음 (모든 모듈의 라우터·모델·구현체를 모으는 곳) |
| 제외 | `templates`, `static`, `last_call` | 검사하지 않음 |

전역 예외 핸들러 경고는 위치와 상관없이 `src/` 아래 모든 `.py`에서 찾습니다.

## 위반 (종료 코드 1)
| 계층 | 참조 금지 계층 | import 금지 패키지 |
| --- | --- | --- |
| domain | infrastructure, application, presentation | fastapi, starlette, sqlalchemy, pydantic, database, jinja2, jwt, passlib |
| infrastructure | application, presentation | fastapi, starlette |
| application | infrastructure, presentation | fastapi, starlette |
| presentation | infrastructure | – |
| common, src 루트 파일 | 기능 모듈의 infrastructure, application, presentation | – |

- 다른 모듈의 같은 계층이나 허용된 계층 참조는 괜찮습니다. (예: `reservations.application` → `catalog.domain`)
- common은 기능 모듈의 domain(예외 클래스 등)만 참조할 수 있습니다. 기능 모듈은 어느 계층에서든 common을 import할 수 있지만, domain에서는 프레임워크에 기대지 않는 순수 코드만 가져다 씁니다.
- application에서 `sqlalchemy`(`AsyncSession`)는 허용합니다. 서비스가 세션을 받아 레포지토리를 만들고 `commit()`하는 것이 이 프로젝트의 패턴입니다.
- `[HTTP예외]`: domain·application에서 `HTTPException` 이름을 쓰면 위반입니다. `from fastapi import HTTPException`은 import 줄에서 `[외부의존]`으로 이미 잡히고, common 등을 거쳐 다시 가져온 경우도 사용 지점에서 잡습니다.
- `[레포반환]`: infrastructure의 `repositories.py`에서 `find_*` 메서드의 반환 타입 어노테이션에 `*Model`이 들어 있으면 위반입니다. (`UserModel | None`, `list[UserModel]`, 문자열 어노테이션 포함)

## 경고 (종료 코드에 영향 없음)
- `[넓은예외]`: `@app.exception_handler(...)`나 `app.add_exception_handler(...)`가 내장 `ValueError`, `LookupError`, `PermissionError`, `Exception`을 그대로 잡습니다. 라이브러리 내부에서 난 같은 예외도 400·403·404로 바뀌어 원인이 가려질 수 있습니다. 현재 `error_handlers.py`는 API 명세(`docs/reference/README.md`의 상태 코드 표)대로 의도한 것이므로 경고로만 남깁니다. 고친다면 프로젝트 전용 예외 클래스(예: `DomainError(ValueError)`)를 두고 그것만 잡습니다.
- `[반환타입]`: `find_*` 메서드에 반환 타입 어노테이션이 없어 `[레포반환]`을 판단할 수 없습니다.

## 결과 처리
- `[의존방향]`: 참조 방향을 바꿉니다. 예를 들어 router가 레포지토리를 직접 만들면, 서비스가 레포지토리를 만들도록 옮깁니다. common이 기능 모듈 구현을 참조하면 그 코드를 해당 모듈로 옮깁니다.
- `[외부의존]` (domain): 프레임워크 코드를 infrastructure나 presentation으로 옮기고 domain은 순수 파이썬으로 둡니다.
- `[외부의존]`·`[HTTP예외]` (application): `ValueError`, `LookupError`, `PermissionError`나 도메인 예외를 내고 전역 예외 핸들러(`src/error_handlers.py`) 또는 router에서 HTTP 응답으로 바꿉니다.
- `[레포반환]`: 레포지토리 안에서 `_to_domain()`으로 도메인 객체로 바꿔 반환합니다.
- `[구조]`: 빠진 폴더나 빈 `__init__.py`를 만듭니다.

## 자동 검사가 못 잡는 것
빈약한 도메인 모델, 반환 타입을 적지 않은 레포지토리가 실제로 무엇을 반환하는지, 서비스에 흩어진 비즈니스 if-else, 에러 응답 형식과 401 헤더는 코드를 읽어야 압니다. 이런 점검은 `layer-checker` 에이전트에 맡깁니다.
