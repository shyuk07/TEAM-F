---
name: layer-check
description: 마감 직전 프로젝트의 4계층 구조와 계층 간 import 방향을 자동으로 검사합니다. 코드를 작성하거나 수정한 뒤, PR이나 머지 전에, 또는 "계층 구조 확인", "의존성 규칙 검사"를 요청받았을 때 사용합니다.
---

# 4계층 규칙 검사

## 실행
프로젝트 루트에서 실행합니다. 외부 라이브러리 없이 표준 라이브러리만 씁니다.

```bash
python3 .claude/skills/layer-check/check_layers.py
```

종료 코드: `0` 위반 없음, `1` 위반 있음, `2` `src/` 없음.

## 검사하는 규칙
| 계층 | 참조 금지 계층 | import 금지 패키지 |
| --- | --- | --- |
| domain | infrastructure, application, presentation | fastapi, starlette, sqlalchemy, pydantic, database, jinja2, jwt, passlib |
| infrastructure | application, presentation | fastapi, starlette |
| application | presentation | fastapi, starlette |
| presentation | infrastructure | – |

- 다른 모듈의 같은 계층이나 허용된 계층 참조는 괜찮습니다. (예: `reservations.application` → `catalog.domain`)
- 기능 모듈마다 4개 계층 폴더와 `__init__.py`가 있는지도 확인합니다.
- `templates`, `static`, `last_call`은 기능 모듈이 아니어서 검사에서 뺍니다.

## 결과 처리
- `[의존방향]`: 참조 방향을 바꿉니다. 예를 들어 router가 레포지토리를 직접 만들면, 서비스가 레포지토리를 만들도록 옮깁니다.
- `[외부의존]` (domain): 프레임워크 코드를 infrastructure나 presentation으로 옮기고 domain은 순수 파이썬으로 둡니다.
- `[외부의존]` (application): `HTTPException`을 쓰고 있다면 `ValueError`나 `LookupError`를 내고 router에서 변환합니다.
- `[구조]`: 빠진 폴더나 빈 `__init__.py`를 만듭니다.

## 자동 검사가 못 잡는 것
빈약한 도메인 모델, 레포지토리가 ORM 모델을 그대로 반환하는지, 서비스에 흩어진 비즈니스 if-else는 코드를 읽어야 압니다. 이런 점검은 `layer-checker` 에이전트에 맡깁니다.
