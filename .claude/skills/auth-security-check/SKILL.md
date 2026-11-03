---
name: auth-security-check
description: 마감 직전 프로젝트의 auth 모듈(OAuth2 로그인, JWT 발급·검증, 로그아웃 블랙리스트, 비밀번호 해싱)과 권한 처리를 점검합니다. 인증 코드를 작성하거나 고친 뒤, 또는 머지 전에 사용합니다. 일반 보안 리뷰는 내장 security-review 스킬과 함께 씁니다.
---

# 인증·보안 점검

`src/auth/` 전체와 인증 의존성을 쓰는 router를 읽고, 아래 항목을 하나씩 확인합니다. 자동 검사 스크립트를 먼저 돌리고, 스크립트가 못 보는 항목은 코드를 읽어 확인합니다.

## 결과 표기
항목마다 아래 넷 중 하나와 근거(파일:줄 또는 스크립트 출력)를 적습니다.

| 표기 | 뜻 |
| --- | --- |
| **통과** | 규칙을 지킨다 |
| **위반** | 규칙을 어긴다. 머지 전에 고친다 |
| **해당없음** | 이번 변경 범위에 그 기능이 없어 점검 대상이 아니다 |
| **미구현** | 점검 대상 기능인데 아직 코드가 없다 (예: 명세에 있는 권한 검사가 없음) |

스크립트의 **주의**는 알려진 남은 위험(7장)입니다. 위반으로 세지 않고 보고서에 그대로 옮깁니다.

## 적용 범위
| 변경 범위 | 점검할 장 |
| --- | --- |
| auth 모듈만 바꾼 PR | 1~4장, 6장의 `.env` 항목, 7장. 5장은 `require_roles` 같은 공용 의존성만 보고 나머지는 해당없음 |
| 다른 모듈의 보호된 API 추가·수정 | 3장(의존성 사용), 5장 전체 |
| `main.py` 미들웨어·CORS 변경 | 6장 전체 |
| 머지 전 전체 점검 | 전부 |

## 자동 검사 스크립트
`src/`에서 실행합니다(스크립트가 import 기준 경로를 `src/`로 맞추므로 루트에서 `uv run python .claude/...`로 실행해도 됩니다). 위반이 있으면 종료코드 1입니다.

```bash
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/static_check.py)
```
DB·서버 불필요. `.env` 커밋 여부, `.env.example` 예시 시크릿이 설정 검증에 거부되는지, `CORSMiddleware`의 `allow_origins=["*"]`+`allow_credentials=True`, `jwt.decode`의 `algorithms=` 누락, 시크릿 하드코딩, 로깅 미들웨어의 헤더·비밀번호 기록, 블랙리스트 정리 호출 여부.

```bash
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/jwt_matrix.py)
```
DB 불필요. 위조 토큰 매트릭스(alg=none 3종, 다른 시크릿, HS512, 만료, exp·jti·sub·role 누락, UUID 아닌 sub, 페이로드 변조 등)가 모두 401 예외로 거부되는지, bcrypt 해싱·더미 검증 타이밍·72바이트 절단.

```bash
(cd src && uv run python ../.claude/skills/auth-security-check/scripts/e2e_auth.py)
```
PostgreSQL 필요, 서버 불필요(ASGI 직접 호출). 로그인 실패 2종 본문 동일, 401+`WWW-Authenticate: Bearer`, 로그아웃 후 재사용 401 `TOKEN_REVOKED`, 없는 사용자 토큰 401, 해시 저장, 블랙리스트 저장, OpenAPI securitySchemes가 HTTP Bearer뿐인지, Response 스키마의 password 필드. 매번 고유 이메일(`sec-<랜덤>@example.com`)로 가입하고 끝나면 만든 행을 지웁니다(`--keep`이면 남김).

passlib이 출력하는 `(trapped) error reading bcrypt version`은 passlib 1.7.4와 bcrypt 4.x의 버전 표기 차이로 생기는 로그이며 동작과 무관합니다(스크립트는 숨김).

## 1. 비밀번호
- [ ] `passlib`의 `CryptContext(schemes=["bcrypt"])`로 해싱하고 평문을 저장하지 않는다 (`e2e_auth`)
- [ ] 로그인 실패 메시지가 "아이디 없음"과 "비밀번호 틀림"을 구분하지 않고, 없는 사용자도 더미 해시로 같은 비용을 들여 검증한다 (`e2e_auth`, `jwt_matrix`)
- [ ] 응답 스키마에 `password`, `password_hash`가 없다 (`e2e_auth`)

## 2. JWT 발급
- [ ] 시크릿 키를 코드에 하드코딩하지 않고 환경변수(`.env`)에서 읽는다. `.env.example`에는 예시 값만 있고, 그 값으로는 서버가 뜨지 않는다 (`static_check`)
- [ ] 알고리즘을 고정한다(`HS256`). 디코딩 시 `algorithms=["HS256"]`를 명시한다 (`static_check`, `jwt_matrix`)
- [ ] `exp`(만료)와 블랙리스트 식별용 `jti`(고유 ID)를 넣고, 디코딩 시 필수로 요구한다 (`jwt_matrix`)
- [ ] 로그인은 JSON 본문(`LoginRequest`: `email`, `password`)을 받고 `{"access_token": ..., "token_type": "bearer"}`를 반환한다. form 본문은 400이다

## 3. 토큰 검증 의존성
- [ ] 토큰 추출은 `HTTPBearer(auto_error=False)`를 쓰고, OpenAPI securitySchemes가 HTTP Bearer뿐이다. 로그인이 JSON이라 OAuth2 password flow를 쓰면 Swagger Authorize가 form을 보내 실패한다 (`e2e_auth`)
- [ ] 만료(`ExpiredSignatureError`), 위조(`InvalidTokenError`) 모두 **401**과 `WWW-Authenticate: Bearer` 헤더로 응답한다 (`jwt_matrix`, `e2e_auth`)
- [ ] 서명 검증 다음에 **블랙리스트를 조회**하고, 있으면 401을 낸다
- [ ] 토큰의 사용자가 DB에 없거나 비활성이면 401을 낸다 (`e2e_auth`)

## 4. 로그아웃과 블랙리스트
- [ ] 로그아웃 시 토큰의 `jti`와 만료 시각을 블랙리스트 테이블에 저장한다 (`e2e_auth`)
- [ ] 같은 토큰으로 다시 요청하면 401이 나온다 (`e2e_auth`, fastapi-run의 `smoke_auth.sh`)
- [ ] 블랙리스트 판단 규칙(만료 여부 등)은 `auth/domain/token_blacklist.py`에 있고, 조회·저장은 레포지토리가 한다

## 5. 권한 (인가)
- [ ] 매장 관리자만 상품 등록·수정, 본인만 예약 취소처럼 소유권·역할 검사를 한다
- [ ] 권한 위반은 도메인·서비스에서 `PermissionError`, 전역 핸들러에서 **403** `FORBIDDEN`으로 변환한다
- [ ] 다른 사용자의 ID를 경로에 넣어 데이터에 접근할 수 없다 (IDOR)

## 6. 기타
- [ ] CORS `allow_origins=["*"]`와 `allow_credentials=True`를 같이 쓰지 않는다 (`static_check`, CORS 미들웨어가 없으면 해당없음)
- [ ] 로깅 미들웨어가 `Authorization` 헤더나 비밀번호를 로그에 남기지 않는다 (`static_check`, 미들웨어가 없으면 해당없음)
- [ ] `.env`가 `.gitignore`에 있고 저장소에 커밋되지 않았다 (`git ls-files .env`가 비어 있음, `static_check`)

## 7. 알려진 남은 위험 (코드 수정 전까지 매번 보고)
- [ ] **로그인 시도 제한:** 연속 실패해도 429나 잠금이 없다. 무차별 대입 방어가 필요한지 팀이 정한다 (`e2e_auth`가 10회 연속 실패로 확인)
- [ ] **상점주 가입:** 누구나 `role=OWNER`로 가입할 수 있다. stores 구현 시 승인 상태(명세 "승인 대기 중인 상점주 403")를 확인하는지 본다 (`e2e_auth`)
- [ ] **블랙리스트 정리:** `purge_expired_tokens`를 호출하는 곳이 없어 `token_blacklist`가 계속 쌓인다. lifespan이나 로그아웃 시 정리 호출을 검토한다 (`static_check`)
- [ ] **bcrypt 72바이트 절단:** 72바이트를 넘는 비밀번호는 뒷부분이 무시된다. 가입 시 최대 길이를 72바이트로 제한하거나 안내한다 (`jwt_matrix`)

## 8. 변경분 전체 리뷰
점검을 마치면 내장 `security-review` 스킬로 변경분 전체를 한 번 더 확인합니다. 이 스킬은 `git diff origin/HEAD...`를 쓰는데, 클론 방식에 따라 `origin/HEAD` 심볼릭 ref가 없어 `unknown revision`으로 실패할 수 있습니다. 먼저 확인하고 없으면 만듭니다.
```bash
git rev-parse --verify -q origin/HEAD || git remote set-head origin -a
```
`set-head`가 네트워크 문제로 실패하면 `git remote set-head origin main`으로 지정하거나, `git diff origin/main...HEAD` 결과를 직접 읽어 같은 관점으로 검토합니다.
