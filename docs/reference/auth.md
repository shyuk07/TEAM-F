# auth API

회원가입, 로그인, 로그아웃, 내 정보, 프로필·비밀번호 변경, 비밀번호 재설정, 자진 탈퇴, 포인트 내역, 관리자 회원 조회, 블랙리스트 정리. 모듈: `src/auth`
테이블: `users`, `token_blacklist`, `point_log`, `password_reset_codes`

포인트 소멸(`EXPIRE`)은 회원 탈퇴 처리(자진·관리자 강제)에서만 발생한다. 별도 API는 없다.

[← 전체 목록](README.md)

---

## 1. 회원가입
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/signup` | 공개 | 201 Created |

새 회원을 등록한다. 비밀번호는 bcrypt로 해싱해 `users.password_hash`에 저장하고, 가입 시 `users_point`는 0으로 시작한다.

**헤더**
- `Content-Type: application/json`

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `email` | string | O | 이메일. 중복 불가 |
| `password` | string | O | 비밀번호 |
| `name` | string | O | 이름 (상점주는 상호). 공백만이거나 100자 초과면 400 |
| `phone` | string | O | 전화번호. 공백만이거나 100자 초과면 400 |
| `role` | string | O | `CUSTOMER` 또는 상점주. `ADMIN`은 입력 불가 |

```json
{
  "email": "user@test.com",
  "password": "password123",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "role": "CUSTOMER"
}
```

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "email": "user@test.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "role": "CUSTOMER",
  "users_point": 0,
  "created_at": "2026-10-29T18:00:00+09:00",
  "status": "APPROVED"
}
```

- `status`: 계정 상태. 상점주(`OWNER`)는 `PENDING`(승인 대기)으로 가입되고, 관리자가 [승인](admin.md#1-상점주-계정-승인)해야 상점을 개설할 수 있다. 그 외 역할은 `APPROVED`.

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 필수값 누락(이름·전화번호 포함), 형식 오류, `role`에 `ADMIN` 입력 |
| 409 | `EMAIL_DUPLICATED` | 이미 가입된 이메일 |

```json
{ "success": false, "error_code": "EMAIL_DUPLICATED", "message": "이미 가입된 이메일입니다." }
```

> **확인 필요:** 상점주 `role` 값 이름(코드는 `OWNER`), 상점주 가입 시 `business_number` 입력 여부. (승인 대기 상태 저장 위치는 해결됨: `users.status`)

---

## 2. 로그인
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/login` | 공개 | 200 OK |

이메일과 비밀번호로 로그인하고 JWT 액세스 토큰을 발급한다. 요청은 JSON이다.
토큰 내용: `sub`(사용자 id), `role`, `jti`(토큰마다 새 UUID), `exp`(발급 30분 후)

**헤더**
- `Content-Type: application/json`

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `email` | string | O | 이메일 |
| `password` | string | O | 비밀번호 |

```json
{ "email": "user@test.com", "password": "password123" }
```

**응답**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "status": "APPROVED"
}
```

- `status`: 로그인 시점의 계정 상태 `APPROVED` / `PENDING` / `REJECTED` / `SUSPENDED`. 정지 기간이 끝났으면 `APPROVED`. 정지 사유·기간은 응답에 없다. JWT 클레임은 바뀌지 않는다.
- **로그인 잠금(REQ-13):** 같은 계정으로 연속 5회 실패하면 마지막 실패부터 10분 동안 잠긴다. 잠긴 동안에는 비밀번호가 맞아도 429로 거부한다. 잠금 중의 시도는 실패 횟수에 넣지 않고 잠금 시간도 늘리지 않으며, 잠금이 끝나면 횟수를 0부터 다시 센다. 로그인에 성공하거나 비밀번호 재설정을 마치면 실패 횟수가 0이 되고(재설정은 잠금도 해제) 가입되지 않은 이메일과 탈퇴 회원에는 잠금이 없다(기존처럼 401). 잠긴 사실은 비밀번호가 맞을 때만 알리고, 틀리면 잠겨 있어도 401 `INVALID_CREDENTIALS`이다(REQ-13-1).
- 승인 대기·거부된 상점주는 로그인할 수 있다(상점 개설은 403).
- **정지된 상점주는 로그인할 수 있고** `status: "SUSPENDED"`를 받는다(정지 중 픽업 처리를 위한 설계 D35·D39). 단 보호 API는 403이다. 정지된 고객은 로그인 자체가 403이다(아래 표).

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `email` 또는 `password` 누락 (form 등 JSON이 아닌 본문 포함) |
| 401 | `INVALID_CREDENTIALS` | 이메일 또는 비밀번호 불일치, **탈퇴한 회원**(없는 계정과 같은 응답) |
| 403 | `FORBIDDEN` | 정지된 고객 계정 ("정지된 계정입니다.") |
| 429 | `ACCOUNT_LOCKED` | 연속 5회 실패로 잠긴 계정에 **맞는 비밀번호**로 시도. 비밀번호가 틀리면 401 `INVALID_CREDENTIALS`. 응답 헤더 `Retry-After: <남은 초>`, `WWW-Authenticate`는 없다 |

확인 순서(비밀번호가 맞을 때): 탈퇴(401) → 잠금(429) → 정지(403).

```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다." }
```

429 예시 (`Retry-After: 540`):
```json
{ "success": false, "error_code": "ACCOUNT_LOCKED", "message": "로그인 시도가 너무 많아 계정이 잠겼습니다. 9분 뒤에 다시 시도해 주세요." }
```

> **노션 명세(JSON)를 따름:** Swagger는 Authorize 버튼에 로그인으로 받은 `access_token`을 붙여 넣어 사용한다(Bearer 토큰 입력 방식. OAuth2 form 로그인은 쓰지 않는다).

---

## 3. 로그아웃
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/logout` | 회원 (정지된 회원도 가능) | 204 No Content |

정지된 회원도 로그아웃할 수 있다(정지 회원은 로그아웃 외 보호 API가 403). 탈퇴·폐기·위조 토큰은 401이다.

요청 토큰의 `jti`와 `exp`를 `token_blacklist(jti, expires_at)`에 저장해 토큰을 무효화한다. 로그인이 필요한 모든 API는 토큰을 확인할 때 블랙리스트도 함께 조회하므로, 로그아웃한 토큰으로 다시 요청하면 401을 반환한다.

시연 순서: 로그인 → `GET /v1/users/me` (200) → 로그아웃 (204) → 같은 토큰으로 `GET /v1/users/me` (401)

**헤더**
- `Authorization: Bearer {access_token}`

**요청 본문:** 없음

**응답:** 없음 (본문 없이 상태 코드만 반환)

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 이미 로그아웃된 토큰 |

```json
{ "success": false, "error_code": "TOKEN_REVOKED", "message": "로그아웃된 토큰입니다." }
```

---

## 4. 내 정보 조회
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/users/me` (노션) | 회원 | 200 OK |

로그인한 회원의 정보와 현재 포인트 잔액(`users_point`)을 조회한다. 결제 전에 사용할 수 있는 포인트를 확인하는 데 사용한다. (사용자 스토리 12)

**헤더**
- `Authorization: Bearer {access_token}`

**요청 본문:** 없음

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "email": "user@test.com",
  "name": "홍길동",
  "phone": "010-1234-5678",
  "role": "CUSTOMER",
  "users_point": 1540,
  "created_at": "2026-10-29T18:00:00+09:00",
  "status": "APPROVED"
}
```

- `status`: 계정 상태 (`PENDING` / `APPROVED` / `REJECTED` / `SUSPENDED` / `WITHDRAWN`).

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료, 탈퇴한 회원의 토큰 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |
| 403 | `FORBIDDEN` | 정지된 계정 |

```json
{ "success": false, "error_code": "UNAUTHORIZED", "message": "로그인이 필요합니다." }
```

> **정지·탈퇴 회원 (모든 보호 API 공통):** 로그인이 필요한 모든 API는 정지된 회원에게 403 `FORBIDDEN` "정지된 계정입니다.", 탈퇴한 회원의 토큰에 401 `UNAUTHORIZED` "유효하지 않은 토큰입니다."를 반환한다. 관리자 정지·탈퇴는 [admin.md](admin.md) 3·4번.

---

## 5. 포인트 내역 조회
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/users/me/points` (노션) | 회원 | 200 OK |

로그인한 회원의 포인트 잔액과 적립·사용 내역(`point_log`)을 최신순으로 조회한다. (사용자 스토리 11·12)
적립·사용·복구·회수는 별도 API 없이 payments 서비스가 내부에서 처리한다. 정책은 [README의 포인트 정책](README.md#포인트-정책-노션-포인트-내역-조회-페이지)을 따른다.

**헤더**
- `Authorization: Bearer {access_token}`

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `type` | string | X | | `EARN` / `USE` / `RESTORE` / `REVOKE` / `GRANT` / `EXPIRE` |
| `page` | integer | X | 0 | 페이지 (0부터) |
| `size` | integer | X | 20 | 페이지 크기, 최대 100 |

예시: `/v1/users/me/points?type=EARN&page=0&size=20`

**응답**
```json
{
  "users_point": 1540,
  "logs": [
    { "id": "c3d4e5f6-...", "amount": 40, "point_type": "EARN", "balance_after": 1540, "created_at": "2026-10-29T18:32:10+09:00" },
    { "id": "b2c3d4e5-...", "amount": -1000, "point_type": "USE", "balance_after": 1500, "created_at": "2026-10-29T18:31:00+09:00" }
  ],
  "page": 0,
  "size": 20,
  "total_elements": 2
}
```

- `point_type`: `EARN` / `USE` / `RESTORE` / `REVOKE` / `GRANT` / `EXPIRE`. `EXPIRE`는 탈퇴로 소멸한 잔액(음수)이다.
- `balance_after`(정수, nullable): 변경 직후 잔액. 이 필드 도입 전 내역은 `null`.

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `type` 값이 목록에 없음, `page`·`size` 범위 오류 |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |

```json
{ "success": false, "error_code": "VALIDATION_ERROR", "message": "type은 EARN, USE, RESTORE, REVOKE, GRANT, EXPIRE 중 하나여야 합니다." }
```

> **확인 필요:** 이 API만 `page`가 0부터 시작하고 `total_elements`를 씁니다. 다른 목록 API는 1부터, `total`입니다.

---


## 6. 관리자 회원 조회
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/admin/users/{user_id}` | 관리자(`ADMIN`) | 200 OK |

관리자가 회원 한 명의 정보를 조회한다. 응답 형식은 [내 정보 조회](#4-내-정보-조회)와 같고, 비밀번호 해시와 사업자번호는 포함하지 않는다.

> 노션 명세에 없는 API로, auth 설계안(`docs/design/auth.md` D-관리자조회, 2026-11-04 확정)에 따라 추가했다. 관리자 계정은 회원가입으로 만들 수 없고 [관리자 계정 생성](#관리자-계정-생성) 방식으로만 만든다. (2026-11-05 복원: admin 설계 `docs/design/admin.md` D42에 따라 auth 라우터에 둔다. 응답에는 회원 상태 `status`가 포함된다.)

**헤더**
- `Authorization: Bearer {access_token}` (관리자 토큰)

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `user_id` | UUID | 조회할 회원 ID |

**요청 본문:** 없음

**응답:** [내 정보 조회](#4-내-정보-조회)의 응답과 같음

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `user_id`가 UUID 형식이 아님 |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |
| 403 | `FORBIDDEN` | 관리자가 아님 |
| 404 | `NOT_FOUND` | 회원이 없음 |

```json
{ "success": false, "error_code": "FORBIDDEN", "message": "접근 권한이 없습니다." }
```

---

## 7. 만료 토큰 블랙리스트 정리
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/admin/token-blacklist/purge` | 관리자(`ADMIN`) | 200 OK |

로그아웃으로 쌓인 `token_blacklist` 행 중 만료 시각(`expires_at`)이 지난 행을 삭제하고 삭제한 개수를 돌려준다. 만료된 토큰은 서명 검증 단계에서 이미 거부되므로, 이 작업은 저장 공간 정리용이다. 서버 시작 시 자동으로 실행되지는 않는다.

> 노션 명세에 없는 API로, auth 설계안(D-블랙리스트정리, 2026-11-04 확정)에 따라 추가했다.

**헤더**
- `Authorization: Bearer {access_token}` (관리자 토큰)

**요청 본문:** 없음

**응답**
```json
{ "deleted_count": 12 }
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |
| 403 | `FORBIDDEN` | 관리자가 아님 |

---

## 8. 프로필 변경
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/users/me` | 회원 | 200 OK |

이름·전화번호를 바꾼다. 보낸 값만 바뀌며 둘 중 하나는 반드시 보내야 한다. 이메일·역할은 바꿀 수 없다(보내도 무시). 변경 뒤에도 이름·전화번호가 모두 채워져 있어야 한다(관리자 제외).

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `name` | string | X | 공백만이거나 100자 초과면 400 |
| `phone` | string | X | 공백만이거나 100자 초과면 400 |

**응답:** [내 정보 조회](#4-내-정보-조회)와 같음

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 변경할 항목 없음, 형식 오류, 변경 뒤 이름·전화번호 중 빈 값 |
| 401 | `UNAUTHORIZED` / `TOKEN_REVOKED` | 토큰 없음·만료·로그아웃·비밀번호 변경으로 무효 |
| 403 | `FORBIDDEN` | 정지된 계정 |

---

## 9. 비밀번호 변경
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/users/me/password` | 회원 | 204 No Content |

현재 비밀번호를 확인하고 새 비밀번호로 바꾼다(새 비밀번호 규칙은 가입과 같다. 현재와 같아도 허용). **이 요청에 쓴 토큰만 유지되고, 그 전에 발급된 다른 토큰은 `401 TOKEN_REVOKED`가 된다.**

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `current_password` | string | O | 현재 비밀번호 |
| `new_password` | string | O | 새 비밀번호 (8자 이상, 72바이트 이하) |

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `CURRENT_PASSWORD_MISMATCH` | 현재 비밀번호 불일치 ("현재 비밀번호가 올바르지 않습니다.") |
| 400 | `VALIDATION_ERROR` | 필수값 누락, 새 비밀번호 규칙 위반 |
| 401 | `UNAUTHORIZED` / `TOKEN_REVOKED` | 토큰 없음·만료·무효 |
| 403 | `FORBIDDEN` | 정지된 계정 |

---

## 10. 비밀번호 재설정 코드 요청
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/password-reset/request` | 공개 | 204 No Content |

가입된 이메일이면 6자리 숫자 재설정 코드(유효 15분)를 만든다. 새 코드를 발급하면 이전 코드는 무효가 되고, 새 코드는 틀린 횟수 0회에서 시작한다. 단 직전 코드를 발급한 지 **60초 안에** 다시 요청하면 새 코드를 만들지 않고 기존 코드를 그대로 두며 코드도 다시 보내지 않는다. **가입 여부와 무관하게 항상 204**이며(탈퇴 회원 포함) 응답으로 가입 여부를 알 수 없다. 응답 시간 차이로도 가입 여부를 짐작하기 어렵게 한다(완전 방지는 아니다, REQ-27-1). 코드 전달은 응답을 보낸 뒤에 이뤄진다. 코드는 해시로 저장한다.

> **임시(개발용) 전달:** 코드는 서버 로그(`auth.password_reset`)에 남는다. 실제 메일 발송으로 교체하기 전에는 배포하지 않는다(auth 설계 D-재설정전달).

**요청 본문:** `{ "email": "user@test.com" }`

**에러:** 400 `VALIDATION_ERROR`(`email` 누락)

---

## 11. 비밀번호 재설정 확인
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/password-reset/confirm` | 공개 | 204 No Content |

코드가 맞으면 비밀번호를 바꾸고 코드를 지운다(1회용). **이전에 발급된 모든 토큰이 무효**(`401 TOKEN_REVOKED`)가 된다. 코드는 5번 틀리면 맞는 코드도 거부한다(만료 15분 정각 포함). 성공하면 로그인 실패 횟수와 잠금도 초기화된다(REQ-13-2).

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `email` | string | O | 이메일 |
| `code` | string | O | 6자리 숫자(`^\d{6}$`). 형식이 다르면 400 `VALIDATION_ERROR`이고 횟수에 세지 않음 |
| `new_password` | string | O | 새 비밀번호. 규칙 위반이면 400이고 코드·횟수는 그대로 |

**에러**
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `INVALID_RESET_CODE` | 코드 불일치·만료·횟수 초과, 미가입·탈퇴 회원(구분하지 않음) | 재설정 코드가 올바르지 않거나 만료되었습니다. |
| 400 | `VALIDATION_ERROR` | 필수값 누락, 코드 형식, 새 비밀번호 규칙 위반 | |

---

## 12. 회원 탈퇴 (자진)
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/users/me/withdraw` | 회원 (정지된 회원 불가) | 200 OK |

비밀번호를 확인하고 탈퇴한다(DELETE는 본문이 비표준이라 POST). 한 트랜잭션에서 순서대로: 결제 대기·예약 완료 예약 취소(환불·사용 포인트 복구) → (상점주면) 판매 중 할인 종료와 상점 폐점 → 회원 `WITHDRAWN` 처리와 **남은 포인트 소멸(`EXPIRE`)**. 이후 로그인과 기존 토큰은 401이다. 탈퇴하면 그 회원의 비밀번호 재설정 코드도 삭제된다(REQ-35-1). 관리자 강제 탈퇴([admin.md 4](admin.md#4-회원-강제-탈퇴))와 같은 규칙이다.

**요청 본문:** `{ "password": "password123" }`

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "status": "WITHDRAWN",
  "deleted_at": "2026-11-05T10:00:00Z",
  "cancelled_reservation_count": 1
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `CURRENT_PASSWORD_MISMATCH` | 비밀번호 불일치 |
| 400 | `ADMIN_ACCOUNT_PROTECTED` | 관리자 계정 |
| 400 | `STORE_HAS_RESERVED_RESERVATIONS` | 상점주의 상점에 다른 고객의 처리되지 않은 예약 있음(전체 롤백) |
| 400 | `VALIDATION_ERROR` | 비밀번호 누락 |
| 401 | `UNAUTHORIZED` / `TOKEN_REVOKED` | 토큰 없음·만료·무효 |
| 403 | `FORBIDDEN` | 정지된 계정 |
| 500 | `DATA_INCONSISTENT` | 예약·결제 데이터 불일치(전체 롤백) |

---

## 관리자 계정 생성
API가 아니라 서버 시작 시 동작이다(D-관리자생성, 2026-11-04 확정). `.env`에 `ADMIN_EMAIL`과 `ADMIN_PASSWORD`를 둘 다 설정하면, 서버가 시작할 때 관리자 계정이 없으면 하나 만든다.

| 상황 | 동작 |
| --- | --- |
| 두 값 모두 없음 | 아무것도 하지 않음 |
| 한 값만 있음 | 서버 시작 중단 |
| 비밀번호가 `change-me`로 시작 | 서버 시작 중단 |
| 이미 같은 이메일의 관리자가 있음 | 아무것도 하지 않음(비밀번호도 바꾸지 않음) |
| 같은 이메일의 일반 회원이 있음 | 관리자로 바꾸지 않고 서버 시작 중단 |

비밀번호 규칙은 회원가입과 같다(8자 이상, 72바이트 이하).

> 관리자 회원 조회(6절)와 만료 토큰 정리(7절)는 auth에 있고, 그 밖의 관리자 API(상점주 승인·거부, 정지, 강제 탈퇴, 포인트 지급 등)는 admin 모듈 소관이다(`docs/reference/admin.md`, `docs/design/admin.md`).

## 포인트 변경 (API 없음)
포인트 사용·적립·복구·회수·소멸은 **공개 API로 제공하지 않는다**(D-포인트비공개). 공개하면 사용자가 자기 포인트를 직접 늘릴 수 있기 때문이다. 결제·환불을 처리하는 payments 모듈이 `AuthApplicationService`의 포인트 메서드를 같은 트랜잭션(`commit=False`)으로 호출한다. 연동 방법은 `docs/design/auth.md` §6.1을 따른다.
