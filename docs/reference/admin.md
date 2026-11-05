# admin API

관리자 기능 9개: 상점주 승인·거부, 회원 정지·강제 탈퇴, 상점 정지·강제 폐점, 할인 상품 정지, 회원 포인트 조회·지급. 모듈: `src/admin`
규칙은 각 소유 모듈(`auth`·`stores`·`catalog`)에 있고, admin은 포트로 호출해 한 트랜잭션으로 묶는다.
테이블: `users`, `point_log`, `stores`, `discount_offers`
설계: [`docs/design/admin.md`](../design/admin.md) (D-번호는 이 설계안의 결정 표)

[← 전체 목록](README.md)

---

## 공통

- **권한:** 모든 API는 관리자(`ADMIN`) 토큰이 필요하다. 헤더 `Authorization: Bearer {access_token}`.
- **본문:** 본문이 있는 API는 `Content-Type: application/json`.
- **공통 에러** (아래 각 API 표에서는 생략한다)

| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 경로의 ID가 UUID 형식이 아님, 본문 필드 누락·타입 오류 | `필드: 오류` 형식 |
| 401 | `UNAUTHORIZED` | 토큰 없음·만료·위조 | 로그인이 필요합니다. |
| 401 | `TOKEN_REVOKED` | 로그아웃된 토큰 | 로그아웃된 토큰입니다. |
| 403 | `FORBIDDEN` | 관리자가 아님 | 접근 권한이 없습니다. |

> 401·403 메시지는 기존 auth 문구다. 명세 문구("인증이 필요합니다.", "관리자 권한이 필요합니다.")와 다르고 상태 코드는 같다(D32).

- **사유 검증:** `reason`이 비었거나 공백뿐이면 400 `VALIDATION_ERROR`이고, 메시지는 API별 명세 문구("정지 사유를 입력해 주세요." 등)다. 앞뒤 공백은 제거해 저장한다.
- **상태 값:** 회원 `PENDING`(승인 대기 상점주) / `APPROVED` / `REJECTED` / `SUSPENDED` / `WITHDRAWN`. 상점 `ACTIVE` / `SUSPENDED` / `CLOSED`(폐점이 정지보다 우선). 할인 상품은 기존 값에 `SUSPENDED` 추가.
- **해제 API 없음:** 정지 해제·재개점 API는 없다(D10). 회원 정지는 `suspended_until`이 지나면 자동으로 `APPROVED`로 간주된다.

---

## 1. 상점주 계정 승인
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/owners/{owner_id}/approve` | 관리자 | 200 OK |

승인 대기(`PENDING`) 상점주를 `APPROVED`로 바꾼다. 상점주는 가입하면 `PENDING`이고, 승인 전에는 상점을 개설할 수 없다(403).

**요청 본문:** 없음

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "email": "owner@test.com",
  "name": "마감베이커리",
  "role": "OWNER",
  "status": "APPROVED",
  "approved_at": "2026-11-05T10:00:00Z"
}
```

**에러**
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `OWNER_NOT_PENDING` | 승인 대기 상태가 아님(이미 승인·거부·정지·탈퇴) | 승인 대기 중인 상점주가 아닙니다. |
| 404 | `NOT_FOUND` | 회원이 없거나 상점주가 아님 | 상점주를 찾을 수 없습니다. |

---

## 2. 상점주 계정 거부
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/owners/{owner_id}/reject` | 관리자 | 200 OK |

승인 대기 상점주를 `REJECTED`로 바꾼다. 거부는 최종 상태이며 이후 승인할 수 없다. 거부된 상점주는 로그인은 되지만 상점을 개설할 수 없다.

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reason` | string | O | 거부 사유 |

```json
{ "reason": "사업자 정보가 확인되지 않습니다." }
```

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "email": "owner@test.com",
  "name": "마감베이커리",
  "role": "OWNER",
  "status": "REJECTED",
  "rejected_reason": "사업자 정보가 확인되지 않습니다.",
  "rejected_at": "2026-11-05T10:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 거부 사유를 입력해 주세요. |
| 400 | `OWNER_NOT_PENDING` | 승인 대기 상태가 아님 | 승인 대기 중인 상점주가 아닙니다. |
| 404 | `NOT_FOUND` | 회원이 없거나 상점주가 아님 | 상점주를 찾을 수 없습니다. |

---

## 3. 회원 정지
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/users/{user_id}/suspend` | 관리자 | 200 OK |

`APPROVED` 회원을 정지한다. `suspended_until`이 없으면 무기한이다.

- 정지된 고객은 로그인(403)과 모든 보호 API(403 "정지된 계정입니다.")가 막힌다.
- 정지된 상점주는 로그인은 되고(`status: "SUSPENDED"`), 보호 API는 403이다. 상점주이면 소유 상점도 같은 사유로 함께 정지한다(이미 정지·폐점이면 건너뜀). 회원 정지와 상점 정지는 한 트랜잭션이다.
- 정지가 끝난 회원(`suspended_until` 경과)은 다시 정지할 수 있다.

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reason` | string | O | 정지 사유 |
| `suspended_until` | datetime | X | 정지 종료 시각(시간대 포함). 없거나 `null`이면 무기한 |

```json
{ "reason": "노쇼 반복", "suspended_until": "2026-12-01T00:00:00+09:00" }
```

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "email": "user@test.com",
  "role": "CUSTOMER",
  "status": "SUSPENDED",
  "suspended_reason": "노쇼 반복",
  "suspended_at": "2026-11-05T10:00:00Z",
  "suspended_until": "2026-11-30T15:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 정지 사유를 입력해 주세요. |
| 400 | `INVALID_SUSPENSION_END` | `suspended_until`이 현재 이전 | 정지 종료 시각은 현재 이후여야 합니다. |
| 400 | `USER_ALREADY_SUSPENDED` | 이미 정지 중 | 이미 정지된 회원입니다. |
| 400 | `USER_WITHDRAWN` | 탈퇴한 회원 | 탈퇴한 회원입니다. |
| 400 | `ADMIN_ACCOUNT_PROTECTED` | 관리자 계정 | 관리자 계정은 정지할 수 없습니다. |
| 400 | `USER_NOT_SUSPENDABLE` | 승인 대기·거부된 상점주 (명세에 없음, D36) | 승인된 회원만 정지할 수 있습니다. |
| 404 | `NOT_FOUND` | 회원 없음 | 회원을 찾을 수 없습니다. |

---

## 4. 회원 강제 탈퇴
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| DELETE | `/v1/admin/users/{user_id}` | 관리자 | 200 OK |

회원을 `WITHDRAWN`으로 바꾼다(soft delete, 행은 남는다). 탈퇴한 회원의 로그인과 기존 토큰은 401이다.

- 상점주이면 소유 상점의 판매 중 할인을 모두 종료하고 상점을 폐점한다. 전부 한 트랜잭션이며, 하나라도 실패하면 탈퇴도 취소된다.
- **DELETE에 JSON 본문이 있다.** httpx 테스트는 `client.delete(..., json=)`가 아니라 `client.request("DELETE", url, json=...)`를 쓴다.

> **미연계 (reservations):** 명세는 탈퇴 회원의 `RESERVED` 예약을 취소하고, 처리되지 않은 예약이 있는 상점은 폐점을 거부한다. 현재는 예약 연동이 자리표시자(`NoReservationAdmin`)라 예약을 취소하지 않고 `cancelled_reservation_count`는 항상 `0`이며, 예약 검사는 항상 통과한다. reservations 연동 후 container 바인딩만 바꾼다.

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reason` | string | O | 탈퇴 사유 |

```json
{ "reason": "약관 위반" }
```

**응답**
```json
{
  "id": "7f1c2a9e-1b2c-4d3e-8f90-123456789abc",
  "status": "WITHDRAWN",
  "deleted_at": "2026-11-05T10:00:00Z",
  "cancelled_reservation_count": 0
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 탈퇴 사유를 입력해 주세요. |
| 400 | `USER_ALREADY_WITHDRAWN` | 이미 탈퇴 | 이미 탈퇴한 회원입니다. |
| 400 | `ADMIN_ACCOUNT_PROTECTED` | 관리자 계정 | 관리자 계정은 탈퇴시킬 수 없습니다. |
| 400 | `STORE_HAS_RESERVED_RESERVATIONS` | 상점주의 상점에 처리되지 않은 예약 있음 (D13, 현재 미연계라 발생하지 않음) | 처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다. |
| 404 | `NOT_FOUND` | 회원 없음 | 회원을 찾을 수 없습니다. |

---

## 5. 상점 정지
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/stores/{store_id}/suspend` | 관리자 | 200 OK |

상점을 정지한다. 정지된 상점과 그 상품·할인은 소유 상점주 외에는 보이지 않고(404), 신규 예약도 받지 않는다. 상점주는 정지된 상점을 직접 폐점할 수 없다(400 `STORE_SUSPENDED`).

**요청 본문:** `{ "reason": "위생 점검" }` (`reason` 필수)

**응답**
```json
{
  "id": "1a2b3c4d-...",
  "owner_id": "7f1c2a9e-...",
  "name": "마감베이커리",
  "status": "SUSPENDED",
  "suspended_reason": "위생 점검",
  "suspended_at": "2026-11-05T10:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 정지 사유를 입력해 주세요. |
| 400 | `STORE_CLOSED` | 폐점된 상점 (정지 후 폐점된 상점 포함) | 폐점된 상점입니다. |
| 400 | `STORE_ALREADY_SUSPENDED` | 이미 정지 | 이미 정지된 상점입니다. |
| 404 | `NOT_FOUND` | 상점 없음 | 상점을 찾을 수 없습니다. |

---

## 6. 상점 강제 폐점
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/stores/{store_id}/close` | 관리자 | 200 OK |

상점을 폐점하고 판매 중인 할인을 모두 종료한다(한 트랜잭션). 정지된 상점도 폐점할 수 있다. **정지 후 폐점된 상점은 폐점 상점으로 취급한다**(다른 폐점 상점과 똑같이 보이며, 정지 상점처럼 숨겨지지 않는다).

> **미연계 (reservations):** 처리되지 않은 예약 검사는 현재 항상 통과한다(4번 참고).

**요청 본문:** `{ "reason": "영업 종료 신고" }` (`reason` 필수)

**응답**
```json
{
  "id": "1a2b3c4d-...",
  "owner_id": "7f1c2a9e-...",
  "name": "마감베이커리",
  "status": "CLOSED",
  "closed_reason": "영업 종료 신고",
  "closed_at": "2026-11-05T10:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 404 | `NOT_FOUND` | 상점 없음 | 상점을 찾을 수 없습니다. |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 폐점 사유를 입력해 주세요. |
| 400 | `STORE_ALREADY_CLOSED` | 이미 폐점 | 이미 폐점된 상점입니다. |
| 400 | `STORE_HAS_RESERVED_RESERVATIONS` | 처리되지 않은 예약 있음 (현재 미연계라 발생하지 않음) | 처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다. |

---

## 7. 할인 상품 정지
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/admin/offers/{offer_id}/suspend` | 관리자 | 200 OK |

할인 상품을 정지한다. 정지된 할인은 목록에서 빠지고(상점주 본인의 목록 포함), 상세 조회는 소유 상점주만 가능하며(그 외 404), 신규 예약을 받지 않는다. 상점주는 정지된 할인을 수정·재개·판매 중단·재등록·재고 조정할 수 없다(400 `OFFER_SUSPENDED` "관리자에 의해 정지된 상품입니다."). 판매 예정·품절 할인도 정지할 수 있다.

**요청 본문:** `{ "reason": "허위 정보" }` (`reason` 필수)

**응답** (`title`은 상품명)
```json
{
  "id": "9e8d7c6b-...",
  "store_id": "1a2b3c4d-...",
  "title": "크루아상 3개 세트",
  "status": "SUSPENDED",
  "suspended_reason": "허위 정보",
  "suspended_at": "2026-11-05T10:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 정지 사유를 입력해 주세요. |
| 400 | `OFFER_ALREADY_SUSPENDED` | 이미 정지 | 이미 정지된 상품입니다. |
| 400 | `OFFER_SALES_ENDED` | 판매 중단·종료된 할인 | 판매가 종료된 상품입니다. |
| 404 | `NOT_FOUND` | 할인 없음 | 상품을 찾을 수 없습니다. |

---

## 8. 회원 포인트 잔액·이력 조회
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/admin/users/{user_id}/points` | 관리자 | 200 OK |

회원의 현재 잔액과 포인트 이력을 최신순(`created_at desc`)으로 조회한다. 탈퇴 회원도 조회할 수 있다.

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `page` | integer | X | 1 | 페이지 (1부터) |
| `size` | integer | X | 20 | 페이지 크기, 1~100 |

**응답**
```json
{
  "user_id": "7f1c2a9e-...",
  "balance": 1500,
  "history": [
    {
      "id": "c3d4e5f6-...",
      "amount": 1000,
      "type": "GRANT",
      "reason": "이벤트 보상",
      "balance_after": 1500,
      "created_by": "0a1b2c3d-...",
      "created_at": "2026-11-05T10:00:00Z"
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

- `type`: `EARN` / `USE` / `RESTORE` / `REVOKE` / `GRANT`(관리자 지급).
- `reason`·`created_by`는 관리자 지급에만 있고 시스템 이벤트는 `null`. `balance_after`는 이 컬럼 도입 전 기록이면 `null`.

**에러**
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `INVALID_PAGE` | `page < 1` 또는 `size`가 1~100 밖 | 페이지 값이 올바르지 않습니다. |
| 404 | `NOT_FOUND` | 회원 없음 | 회원을 찾을 수 없습니다. |

> 회원용 [포인트 내역 조회](auth.md#5-포인트-내역-조회)는 `page`가 0부터이고 `total_elements`를 쓴다. 이 API는 명세대로 1부터, `total`이다(README 공통 확인 필요 5번).

---

## 9. 회원 포인트 지급
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/admin/users/{user_id}/points` | 관리자 | 201 Created |

회원에게 포인트를 지급한다. 잔액 증가와 `point_log`(`GRANT`, 사유, 지급 후 잔액, 지급한 관리자) 기록이 한 트랜잭션이다. 정지된 회원에게도 지급할 수 있다.

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `amount` | integer | O | 지급 포인트, 1 이상 |
| `reason` | string | O | 지급 사유 |

```json
{ "amount": 1000, "reason": "이벤트 보상" }
```

**응답** (생성된 이력 한 건)
```json
{
  "id": "c3d4e5f6-...",
  "user_id": "7f1c2a9e-...",
  "amount": 1000,
  "type": "GRANT",
  "reason": "이벤트 보상",
  "balance_after": 1500,
  "created_by": "0a1b2c3d-...",
  "created_at": "2026-11-05T10:00:00Z"
}
```

**에러** (위에서부터 먼저 검사)
| HTTP | error_code | 상황 | 메시지 |
| --- | --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `amount < 1` | 지급 포인트는 1 이상이어야 합니다. |
| 400 | `VALIDATION_ERROR` | 사유 없음 | 지급 사유를 입력해 주세요. |
| 400 | `USER_WITHDRAWN` | 탈퇴한 회원 | 탈퇴한 회원입니다. |
| 400 | `VALIDATION_ERROR` | 잔액이 DB 정수 한도 초과 (D24) | 포인트 잔액이 한도를 넘습니다. |
| 404 | `NOT_FOUND` | 회원 없음 | 회원을 찾을 수 없습니다. |

---

## 기존 관리자 API (auth)

다음 두 API는 같은 `/v1/admin` 접두사를 쓰지만 auth 라우터에 있다(D42, 임시). 문서는 auth.md에 있다.
- `GET /v1/admin/users/{user_id}`: [관리자 회원 조회](auth.md#6-관리자-회원-조회)
- `POST /v1/admin/token-blacklist/purge`: [만료 토큰 블랙리스트 정리](auth.md#7-만료-토큰-블랙리스트-정리)

## 개발 DB 반영

이 기능은 `users`, `point_log`, `stores`, `discount_offers`에 컬럼을 추가했다(`.claude/skills/db-schema/schema.sql`). 테이블은 `create_all`로 만들어지므로 **기존 개발 DB에는 새 컬럼이 생기지 않는다.** 개발 DB를 새로 만들거나 [설계안 2.4절](../design/admin.md#24-개발-db-수동-반영용-sql-제안-실행하지-않음)의 `ALTER` SQL을 실행한다.
