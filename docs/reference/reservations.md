# reservations API

픽업 예약 생성, 조회, 취소, 픽업 완료. 모듈: `src/reservations`
테이블: `pickup_reservations` (재고는 `discount_offers`, `stock_log`)

[← 전체 목록](README.md)

---

## 1. 예약 생성
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/reservations` | 회원 | 201 Created |

사용자가 할인 상품을 선택하고 수량을 입력하여 예약을 생성한다. 예약 생성 시 예약 정보와 예약 당시 상품 정보 및 금액 정보를 저장한다.

구현 참고: 할인 행을 `SELECT ... FOR UPDATE`로 잠그고 재고 차감, 예약 저장, `stock_log` 기록을 한 트랜잭션으로 처리합니다. (`db-schema` 스킬 7절)

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `offer_id` | UUID | O | 예약할 할인 상품 ID |
| `quantity` | integer | O | 예약 수량. 1~5, 남은 재고 이하 |

```json
{
  "offer_id": "550e8400-e29b-41d4-a716-446655440001",
  "quantity": 2
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 예약 ID |
| `user_id` | UUID | 예약한 회원 ID |
| `offer_id` | UUID | 할인 상품 ID |
| `quantity` | integer | 예약 수량 |
| `unit_price` | integer | 예약 당시 개당 가격 |
| `total_price` | integer | 총 결제 예정 금액 |
| `status` | string | 예약 상태 |
| `created_at` | datetime | 예약 생성 시간 |
| `store_name` | string | 매장명 |
| `product_name` | string | 상품명 |

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "user_id": "550e8400-e29b-41d4-a716-446655440003",
  "offer_id": "550e8400-e29b-41d4-a716-446655440001",
  "quantity": 2,
  "unit_price": 3000,
  "total_price": 6000,
  "status": "PENDING_PAYMENT",
  "created_at": "2025-10-29T15:00:00+09:00",
  "store_name": "마감 베이커리",
  "product_name": "샌드위치"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 400 | 잘못된 수량 입력 (`VALIDATION_ERROR`. 정수가 아니거나 1 미만, 또는 "수량은 5개 이하여야 합니다.") |
| 401 | 로그인 필요 |
| 404 | 할인 상품 없음 |
| 409 | 재고 부족(`OUT_OF_STOCK`) 또는 예약 불가 상품(`OFFER_NOT_RESERVABLE`) |
| 409 | 같은 할인 상품에 결제하지 않은 예약이 이미 있음(`PENDING_RESERVATION_EXISTS`, "같은 할인 상품에 결제하지 않은 예약이 이미 있습니다."). 같은 회원은 할인 상품마다 결제 대기 예약을 1건만 가질 수 있다. 그 예약을 취소하거나 결제하면 다시 예약할 수 있다. 상점주가 자기 상점 할인을 예약할 때도 같다 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

제한에 걸려 거절된 요청은 예약·재고·재고 기록을 바꾸지 않는다. 같은 회원이 같은 할인에 동시에 여러 번 요청해도 결제 대기 예약은 1건만 만들어진다. 여러 조건에 동시에 걸리면 수량 형식(400) → 할인 없음(404) → 예약 불가·재고 부족(409) → 결제 대기 예약 중복(409) 순서로 판단한다.

> **확인 필요**
> - 결제하지 않은 예약(`PENDING_PAYMENT`)의 재고를 언제 되돌릴지 (결제 제한 시간)
> - ~~상점주가 자기 상점 할인을 예약할 수 있는지~~ → 허용. 고객과 같은 수량·중복 제한을 적용한다(요구조건 R-REQ31).

---

## 2. 내 예약 목록 조회
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/users/me/reservations` | 회원 | 200 OK |

로그인한 사용자의 예약 목록을 조회한다. 사용자는 본인의 예약 내역만 확인할 수 있다.

**헤더**
- `Authorization: Bearer {access_token}`

**쿼리 매개변수:** 노션에 없음 (아래 "확인 필요" 참고)

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `reservations` | array | 예약 목록 |
| `reservations[].id` | UUID | 예약 ID |
| `reservations[].offer_id` | UUID | 할인 상품 ID |
| `reservations[].store_name` | string | 매장명 |
| `reservations[].product_name` | string | 상품명 |
| `reservations[].quantity` | integer | 예약 수량 |
| `reservations[].total_price` | integer | 총 금액 |
| `reservations[].status` | string | 예약 상태 |
| `reservations[].created_at` | datetime | 예약 생성 시간 |
| `reservations[].cancelled_by` | string 또는 null | 취소 주체. `CUSTOMER` 고객 직접 취소, `STORE` 매장 사정 취소, `SYSTEM` 시스템 처리, `null` 취소되지 않았거나 취소 주체를 알 수 없음(기존 취소 건) |
| `reservations[].pickup_code` | string | 픽업 코드(영문 1자 + 숫자 5자) |
| `reservations[].pickup_address` | string | 픽업 주소(예약 당시) |
| `reservations[].pickup_start` | datetime | 픽업 시작 시각 |
| `reservations[].pickup_end` | datetime | 픽업 마감 시각. 결제 완료(`RESERVED`)인데 지났으면 미수령(design/reservations.md D-46) |
| `reservations[].cancellable_until` | datetime | 고객 취소·환불 마감 시각(이 시각까지 가능, 픽업 시작 1시간 전) |
| `page` / `size` / `total` | integer | 페이지(1부터, 기본 1), 크기(1~100, 기본 20), 전체 건수. 쿼리 `status`·`page`·`size` |

```json
{
  "reservations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "offer_id": "550e8400-e29b-41d4-a716-446655440001",
      "store_name": "마감 베이커리",
      "product_name": "샌드위치",
      "quantity": 2,
      "total_price": 6000,
      "status": "RESERVED",
      "created_at": "2025-10-29T15:00:00+09:00",
      "cancelled_by": null
    }
  ]
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 401 | 로그인 필요 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요**
> - 교안은 목록 API에 필터·페이지네이션을 요구합니다. `status`, `page`, `size` 쿼리와 `page`, `size`, `total` 응답 필드 추가를 제안합니다.
> - 예시의 `RESERVED`와 예약 생성의 `PENDING_PAYMENT`의 관계 (결제 완료 후 `RESERVED`가 되는지)
> - ~~픽업할 때 보여줄 `pickup_code`, `pickup_address`, 픽업 시간이 목록이나 상세에 없습니다.~~ → 해결: 목록에 포함(프론트엔드 연동 2026-11-10)

---

## 2-1. 내 예약 한 건 조회
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/reservations/{reservation_id}` | 회원 (본인 예약) | 200 OK |

본인 예약 한 건을 조회한다. 결제 완료 화면(C4)에서 픽업 코드·픽업 시간을 보여 주는 용도다(프론트엔드 연동 2026-11-10). 응답 형식은 [2. 내 예약 목록](#2-내-예약-목록-조회)의 `reservations[]` 항목 하나와 같다.

**에러**
| HTTP | 상황 |
| --- | --- |
| 401 | 로그인 필요 |
| 403 | 본인 예약이 아님 ("본인 예약만 조회할 수 있습니다.") |
| 404 | 예약 정보 없음 |

---

## 3. 예약 취소
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/reservations/{reservation_id}/cancel` | 회원 (본인 예약) | 200 OK |

사용자가 자신의 예약을 취소한다. 예약 상태를 취소로 변경하고 취소 시각을 기록한다. 환불 관련 처리는 결제·환불 도메인과 연동한다.

구현 참고: 취소 시 재고를 되돌리고 `stock_log`에 양수로 기록합니다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `reservation_id` | UUID | 예약 ID |

**요청 본문:** 없음

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 예약 ID |
| `status` | string | 변경된 예약 상태 |
| `cancelled_at` | datetime | 예약 취소 시간 |
| `cancelled_by` | string 또는 null | 취소 주체. 이 API로는 항상 `CUSTOMER` |

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "status": "CANCELLED",
  "cancelled_at": "2025-10-29T16:00:00+09:00",
  "cancelled_by": "CUSTOMER"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 400 | 결제 완료 예약의 취소 가능 시각이 지남 (`CANCELLATION_DEADLINE_PASSED`, "취소 가능 시각이 지나 취소·환불할 수 없습니다.") |
| 401 | 로그인 필요 |
| 403 | 본인 예약이 아님 |
| 404 | 예약 정보 없음 |
| 409 | 이미 취소되었거나 취소 불가 상태 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 (예약·결제 데이터 불일치 `DATA_INCONSISTENT` 포함) |

결제 완료(`RESERVED`) 예약은 할인의 취소 가능 시각(`cancel_policy.cancellable_until` = 픽업 시작 1시간 전, [catalog 할인 상세](catalog.md#10-할인-상세))까지만 취소할 수 있다. 정확히 그 시각은 허용하고, 지나면 400이며 아무것도 바뀌지 않는다. [환불 요청](payments.md#3-환불-요청)도 같은 기준이다. 결제 대기(`PENDING_PAYMENT`) 예약은 시간과 관계없이 취소할 수 있다. 데이터 불일치(500)는 시간 제한보다 먼저 판단한다. 위약금은 0원이다.

> **확인 필요:** 결제한 예약을 취소하면 환불을 자동으로 만드는지, 고객이 [환불 요청](payments.md#3-환불-요청)을 따로 호출하는지

---

> **미수령 예약(2026-11-10 결정):** 결제 완료(`RESERVED`) 예약이 픽업 마감(`pickup_end`)이 지나도록 픽업되지 않으면 미수령으로 본다. 상태는 `RESERVED` 그대로이며 별도 상태 값은 없다. 미수령 예약은 고객 취소·환불·픽업이 모두 불가하고(기존 시간 규칙), 회원 탈퇴나 할인 판매 중단(예약 일괄 취소)에서도 자동 취소·환불·재고 복구하지 않는다(취소 건수에서 빠진다). 상점 폐점과 상점주 탈퇴를 막는 '처리되지 않은 예약'에도 세지 않는다. 목록에서 미수령을 표시하는 방식은 아직 정하지 않았다.

## 4. 픽업 완료
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/reservations/{reservation_id}/pickup` | 상점주 (해당 매장) | 200 OK |

상점주가 고객의 예약번호를 확인한 뒤 픽업 완료 처리한다. 예약 상태를 픽업 완료로 변경하고 픽업 완료 시각을 기록한다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `reservation_id` | UUID | 예약 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `pickup_code` | string | O | 예약 확인용 예약번호 |

```json
{
  "pickup_code": "A12345"
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 예약 ID |
| `pickup_code` | string | 예약번호 |
| `status` | string | 예약 상태 |
| `picked_up_at` | datetime | 픽업 완료 시간 |

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "pickup_code": "A12345",
  "status": "PICKED_UP",
  "picked_up_at": "2025-10-29T18:30:00+09:00"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 400 | 예약번호 불일치 |
| 400 | 픽업 가능 시간이 아님 (`PICKUP_OUTSIDE_WINDOW`, "픽업 가능 시간이 아닙니다.") |
| 401 | 로그인 필요 |
| 403 | 해당 매장 상점주가 아님 |
| 404 | 예약 정보 없음 |
| 409 | 이미 픽업 완료되었거나 유효하지 않은 예약 상태 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요**
> - ~~상점주가 `reservation_id`를 알 방법이 없습니다.~~ → 해결: [5. 상점주용 매장 예약 목록 조회](#5-상점주용-매장-예약-목록-조회)에서 예약 ID를 확인합니다.
> - `pickup_code` 발급 시점과 형식
> - ~~픽업 시간(`pickup_start` ~ `pickup_end`) 밖에서 처리할 수 있는지~~ → 확정: 불가. 할인의 픽업 시작부터 마감까지(양 끝 포함)만 픽업 완료할 수 있고, 밖이면 400이며 아무것도 바뀌지 않는다. 판단 순서는 403(상점주 아님) → 404 → 400(시간) → 409(상태) → 400(예약번호). 픽업 마감 후 찾아가지 않은 예약의 처리는 아직 정하지 않았다.

---

## 5. 상점주용 매장 예약 목록 조회
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/stores/{store_id}/reservations` | 상점주(본인 상점) | 200 OK |

상점주가 자기 상점의 예약을 조회한다. 픽업 완료 처리에 필요한 예약 ID를 확인하는 용도다. 상점의 모든 할인(판매 중단·마감 포함)에 걸린 예약을 대상으로 하며, 결제 대기·예약 확정·픽업 완료·취소 예약을 모두 볼 수 있다. 고객 정보(회원 ID·이메일·전화번호)와 픽업 코드는 응답에 넣지 않는다. 픽업은 고객이 제시한 코드로 확인한다. 관리자도 이 API를 쓸 수 없다. 관리자에게 정지된 상점주도 [픽업 완료](#4-픽업-완료)와 같이 본인 상점 예약은 조회할 수 있다. 탈퇴한 계정의 토큰은 401이다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `store_id` | UUID | 상점 ID |

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `status` | string | X | `PENDING_PAYMENT` / `RESERVED` / `PICKED_UP` / `CANCELLED` 중 하나. 없으면 전체 |
| `page` | integer | X | 1부터. 기본 1 |
| `size` | integer | X | 1~100. 기본 20 |

정렬은 예약 시각 내림차순(같으면 예약 ID 내림차순)이다. `total`은 `status` 조건에 맞는 전체 건수다. 예약이 없으면 빈 목록을 돌려준다.

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `reservations` | array | 예약 목록 |
| `reservations[].id` | UUID | 예약 ID |
| `reservations[].product_name` | string | 상품명(예약 당시) |
| `reservations[].quantity` | integer | 예약 수량 |
| `reservations[].total_price` | integer | 예약 금액 |
| `reservations[].status` | string | 예약 상태 |
| `reservations[].created_at` | datetime | 예약 시각 |
| `page` | integer | 현재 페이지 |
| `size` | integer | 페이지 크기 |
| `total` | integer | 조건에 맞는 전체 건수 |

```json
{
  "reservations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440002",
      "product_name": "샌드위치",
      "quantity": 2,
      "total_price": 6000,
      "status": "RESERVED",
      "created_at": "2025-10-29T15:00:00+09:00"
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

**에러**
| HTTP | error_code | 상황 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `status`·`page`·`size` 형식 오류 |
| 401 | `UNAUTHORIZED` | 로그인 필요, 탈퇴한 계정 |
| 403 | `FORBIDDEN` | 상점주가 아님(고객·관리자) / 본인 상점의 예약만 조회할 수 있습니다. (정지된 상점주도 본인 상점은 조회 가능) |
| 404 | `NOT_FOUND` | 상점을 찾을 수 없습니다. |
| 500 | | 서버 오류 |
