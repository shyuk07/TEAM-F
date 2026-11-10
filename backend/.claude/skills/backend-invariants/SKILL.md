---
name: backend-invariants
description: 마감 직전 프로젝트의 백엔드 코드가 어떤 작업에서도 지켜야 하는 불변 규칙(R1~R16)과 코드 작업 공통 완료 게이트의 정본입니다. 계층 순수성·의존 방향, 도메인 규칙 위치, 레포지토리 반환, 트랜잭션(commit) 위치, 예외·에러 응답, 추상화·DI 조립, 바운디드 컨텍스트, 스키마·명세 일치, 시크릿·테스트 규칙을 R번호로 정의하고 각 규칙의 검사 방법과 상세 위치를 안내합니다. 코드를 설계·구현·리뷰·점검·검증할 때, 발주서에 지킬 규칙을 ID로 넘길 때, 위반을 R번호로 보고할 때 사용합니다.
---

# 백엔드 불변 규칙

이 문서는 **규칙의 정본**입니다. 다른 스킬과 에이전트 명세는 규칙 문장을 다시 쓰지 않고 `R번호`로 가리킵니다.
- 규칙을 바꿀 때는 이 문서만 고칩니다.
- 이유와 원칙: `layer-architecture` / 코드 패턴: `layer-implementation` / 자동 검사: `layer-check` / DB: `db-schema`
- 발주서에는 "R1~R16 준수"처럼 ID로 적고, 위반은 `R번호`로 보고합니다.

검사 방법 표기: **자동**(`check_layers.py`가 잡음, 괄호 안은 출력 태그) / **정독**(`layer-checker`가 코드를 읽어 판정) / **실행**(`verifier`·`pre-merge-check`가 실행해 판정)

## 1. 계층

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R1 | domain은 순수 파이썬이다. fastapi, starlette, sqlalchemy, pydantic, `database`, jinja2, jwt, passlib와 다른 계층을 import하지 않는다. | 자동(`[외부의존]`, `[의존방향]`) | `layer-check` 위반 표 |
| R2 | 의존 방향은 presentation → application → domain, infrastructure → domain이다. presentation과 application은 infrastructure 구현체를 import하지 않는다. | 자동(`[의존방향]`) + 정독 | `layer-architecture` §2 |
| R3 | 도메인 규칙(검증·상태 변경·권한·소유 판단)은 엔티티 메서드에 둔다. 서비스에 비즈니스 if-else나 쿼리(`select()`)를 두지 않는다. 메서드 없는 빈약한 엔티티를 만들지 않는다. | 정독 | `layer-architecture` §3.2 |
| R4 | 레포지토리는 도메인 객체만 받고 돌려준다. `*Model`을 밖으로 내보내지 않는다. | 자동(`[레포반환]`, `[반환타입]`) + 정독 | `layer-implementation` §3 |
| R5 | `commit()`은 application 서비스만 한다. 레포지토리는 `flush()`까지 한다. | 정독 | `layer-architecture` §5.3 |

## 2. 예외와 응답

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R6 | domain·application·router에서 `HTTPException`을 만들지 않는다. 모듈 전용 도메인 예외(`<모듈>/domain/exceptions.py`)를 내고, HTTP 변환은 전역 핸들러(`src/error_handlers.py`)가 한다. `LookupError`·`PermissionError`를 그대로 raise하지 않는다. | 자동(`[HTTP예외]`) + 정독 | `layer-implementation` 예외 절 |
| R7 | 모든 에러 응답은 `{"success": false, "error_code", "message"}` 형식이고, 401에는 `WWW-Authenticate: Bearer` 헤더가 붙는다. router에서 예외를 잡아 다른 형식으로 바꾸지 않는다. | 정독 + 실행 | `../docs/reference/README.md` 에러 응답 |

## 3. 추상화와 조립

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R8 | 레포지토리와 기술 의존 기능(해싱·토큰·외부 API)은 domain에 추상(ABC)으로, infrastructure에 구현체로 둔다. application 서비스는 생성자에서 추상만 받고, 기본 구현체를 직접 만들지 않는다. | 정독 | `layer-architecture` §5 |
| R9 | 구현체 연결은 `src/container.py`에서만 한다. router·인증 의존성은 `presentation/dependencies.py`의 `provide_*`를 `Depends`로 받는다. 모든 `provide_*`는 `wire_dependencies`에 매핑되어 있어야 한다. | 정독 + 실행 | `layer-architecture` §6 |
| R10 | 추상에 선언된 메서드만 호출한다. | 정독 + 실행 | `layer-architecture` §8 |

## 4. 바운디드 컨텍스트

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R11 | 다른 모듈의 ORM 모델·레포지토리 구현체·서비스 내부를 쓰지 않는다. 상대의 추상 레포지토리, 쓰는 쪽이 정의한 포트, 상대 application 서비스 중 하나를 주입받는다. | 자동(일부) + 정독 | `layer-architecture` §3.4 |
| R12 | 모듈 간 순환 의존을 만들지 않는다. 서비스 생성자 안에서 다른 서비스를 만들지 않는다. | 정독 + 실행(`import main`) | `layer-architecture` §4 |
| R13 | 여러 모듈을 한 트랜잭션으로 묶을 때는 같은 요청 세션을 쓰고, 호출되는 쪽은 `commit=False`, 호출한 서비스가 마지막에 한 번 `commit()`한다. | 정독 | `layer-implementation` §4 |

## 5. 데이터와 명세

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R14 | `models.py`의 테이블·컬럼·타입·NULL·FK는 `db-schema`의 `schema.sql`과 같다. ID는 `uuid.UUID`, 시간은 timezone이 있는 `datetime`이다. 스키마를 바꾸면 `schema.sql`과 `db-schema/SKILL.md`를 함께 고친다. | 정독 | `db-schema` §6 |
| R15 | URI·요청/응답 필드명·상태 코드·에러 메시지는 `../docs/reference/<모듈>.md`를 따른다. 다르게 구현하면 이유를 보고한다. 응답에 비밀번호 해시 같은 민감 정보를 넣지 않는다. | 정독 + 실행 | `../docs/reference/` |

## 6. 저장소 위생과 테스트

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| R16 | `.env`·시크릿을 커밋하거나 하드코딩하지 않는다. 의존성은 `uv add`로만 추가한다. 테스트·검사를 통과시키려고 규칙을 끄거나 skip하지 않으며, DB 테스트 skip은 통과가 아니다. | 실행 | `pre-merge-check` §1·§4 |

## 7. 코드 작업 공통 완료 게이트

코드를 바꾼 작업은 아래를 모두 통과해야 완료입니다. 명령의 정본은 이 절이며, 에이전트 명세와 `pre-merge-check`는 이 절을 가리킵니다.

```bash
python3 .claude/skills/layer-check/check_layers.py   # 위반 0건 (R1, R2, R4, R6)
(cd src && uv run python -c "import main")           # 성공 (R9, R12)
uv run pytest -rs                                     # failed 0, db 마커 skip 0 (R16)
```
- 정독 규칙(R3, R5, R7~R15)은 수정자가 아닌 `layer-checker`가 판정합니다.
- 실제 동작(R7, R9, R15)은 `verifier`가 `fastapi-run`·`pre-merge-check`로 확인합니다.

## 8. 위반 보고 형식

| 심각도 | 파일:줄 | 규칙 | 내용 | 고치는 방법 |
| --- | --- | --- | --- | --- |
| 위반 / 주의 / 미구현 | `src/...:42` | R6 | router에서 `HTTPException(404)` 생성 | 도메인 예외로 바꾸고 전역 핸들러에 맡김 |
