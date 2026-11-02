# auth API

회원가입, 로그인, 로그아웃, 내 정보, 포인트 내역. 모듈: `src/auth`
테이블: `users`, `token_blacklist`, `point_log`

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
| `name` | string | X | 이름 (상점주는 상호) |
| `phone` | string | X | 전화번호 |
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
  "created_at": "2026-10-29T18:00:00+09:00"
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 필수값 누락, 형식 오류, `role`에 `ADMIN` 입력 |
| 409 | `EMAIL_DUPLICATED` | 이미 가입된 이메일 |

```json
{ "success": false, "error_code": "EMAIL_DUPLICATED", "message": "이미 가입된 이메일입니다." }
```

> **확인 필요:** 상점주 `role` 값 이름, 상점주 가입 시 `business_number` 입력 여부, 상점주 승인 대기 상태를 어디에 저장할지

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
  "token_type": "bearer"
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `email` 또는 `password` 누락 (form 등 JSON이 아닌 본문 포함) |
| 401 | `INVALID_CREDENTIALS` | 이메일 또는 비밀번호 불일치 |

```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다." }
```

> **노션 명세(JSON)를 따름:** Swagger는 Authorize 버튼에 로그인으로 받은 `access_token`을 붙여 넣어 사용한다(Bearer 토큰 입력 방식. OAuth2 form 로그인은 쓰지 않는다).

---

## 3. 로그아웃
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/auth/logout` | 회원 | 204 No Content |

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
  "created_at": "2026-10-29T18:00:00+09:00"
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |

```json
{ "success": false, "error_code": "UNAUTHORIZED", "message": "로그인이 필요합니다." }
```

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
| `type` | string | X | | `EARN` / `USE` / `RESTORE` / `REVOKE` |
| `page` | integer | X | 0 | 페이지 (0부터) |
| `size` | integer | X | 20 | 페이지 크기, 최대 100 |

예시: `/v1/users/me/points?type=EARN&page=0&size=20`

**응답**
```json
{
  "users_point": 1540,
  "logs": [
    { "id": "c3d4e5f6-...", "amount": 40, "point_type": "EARN", "created_at": "2026-10-29T18:32:10+09:00" },
    { "id": "b2c3d4e5-...", "amount": -1000, "point_type": "USE", "created_at": "2026-10-29T18:31:00+09:00" }
  ],
  "page": 0,
  "size": 20,
  "total_elements": 2
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `type` 값이 목록에 없음, `page`·`size` 범위 오류 |
| 401 | `UNAUTHORIZED` | 토큰 없음 또는 만료 |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 |

```json
{ "success": false, "error_code": "VALIDATION_ERROR", "message": "type은 EARN, USE, RESTORE, REVOKE 중 하나여야 합니다." }
```

> **확인 필요:** 이 API만 `page`가 0부터 시작하고 `total_elements`를 씁니다. 다른 목록 API는 1부터, `total`입니다.
