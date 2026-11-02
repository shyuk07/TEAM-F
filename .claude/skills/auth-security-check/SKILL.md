---
name: auth-security-check
description: 마감 직전 프로젝트의 auth 모듈(OAuth2 로그인, JWT 발급·검증, 로그아웃 블랙리스트, 비밀번호 해싱)과 권한 처리를 점검합니다. 인증 코드를 작성하거나 고친 뒤, 또는 머지 전에 사용합니다. 일반 보안 리뷰는 내장 security-review 스킬과 함께 씁니다.
---

# 인증·보안 점검

`src/auth/` 전체와 인증 의존성을 쓰는 router를 읽고, 아래 항목을 하나씩 확인합니다. 결과는 항목별 **통과 / 위반 / 미구현**과 파일:줄로 보고합니다.

## 1. 비밀번호
- [ ] `passlib`의 `CryptContext(schemes=["bcrypt"])`로 해싱하고 평문을 저장하지 않는다
- [ ] 로그인 실패 메시지가 "아이디 없음"과 "비밀번호 틀림"을 구분하지 않는다
- [ ] 응답 스키마에 `password`, `hashed_password`가 없다

## 2. JWT 발급
- [ ] 시크릿 키를 코드에 하드코딩하지 않고 환경변수(`.env`)에서 읽는다. `.env.example`에는 예시 값만 있다
- [ ] 알고리즘을 고정한다(`HS256`). 디코딩 시 `algorithms=["HS256"]`를 명시한다
- [ ] `exp`(만료)를 넣는다. 블랙리스트 식별을 위해 `jti`(고유 ID)를 넣는 것을 권장한다
- [ ] 로그인은 `OAuth2PasswordRequestForm`을 쓰고 `{"access_token": ..., "token_type": "bearer"}`를 반환한다 (Swagger Authorize 동작 조건)

## 3. 토큰 검증 의존성
- [ ] `OAuth2PasswordBearer(tokenUrl=...)`의 경로가 실제 로그인 경로와 같다
- [ ] 만료(`ExpiredSignatureError`), 위조(`InvalidTokenError`) 모두 **401**과 `WWW-Authenticate: Bearer` 헤더로 응답한다
- [ ] 서명 검증 다음에 **블랙리스트를 조회**하고, 있으면 401을 낸다
- [ ] 토큰의 사용자가 DB에 없거나 비활성이면 401을 낸다

## 4. 로그아웃과 블랙리스트
- [ ] 로그아웃 시 토큰(또는 `jti`)과 만료 시각을 블랙리스트 테이블에 저장한다
- [ ] 같은 토큰으로 다시 요청하면 401이 나온다 (fastapi-run 스킬 시나리오 5로 실제 확인)
- [ ] 블랙리스트 판단 규칙(만료 여부 등)은 `auth/domain/token_blacklist.py`에 있고, 조회·저장은 레포지토리가 한다

## 5. 권한 (인가)
- [ ] 매장 관리자만 상품 등록·수정, 본인만 예약 취소처럼 소유권·역할 검사를 한다
- [ ] 권한 위반은 도메인·서비스에서 `PermissionError`, router에서 **403**으로 변환한다
- [ ] 다른 사용자의 ID를 경로에 넣어 데이터에 접근할 수 없다 (IDOR)

## 6. 기타
- [ ] CORS `allow_origins=["*"]`와 `allow_credentials=True`를 같이 쓰지 않는다
- [ ] 로깅 미들웨어가 `Authorization` 헤더나 비밀번호를 로그에 남기지 않는다
- [ ] `.env`가 `.gitignore`에 있고 저장소에 커밋되지 않았다 (`git ls-files .env`가 비어 있음)

점검을 마치면 내장 `security-review` 스킬로 변경분 전체를 한 번 더 확인합니다.
