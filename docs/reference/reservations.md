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
| `quantity` | integer | O | 예약 수량 |

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
| 400 | 잘못된 수량 입력 |
| 401 | 로그인 필요 |
| 404 | 할인 상품 없음 |
| 409 | 재고 부족 또는 예약 불가 상품 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요**
> - 결제하지 않은 예약(`PENDING_PAYMENT`)의 재고를 언제 되돌릴지 (결제 제한 시간)
> - 상점주가 자기 상점 할인을 예약할 수 있는지

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
      "created_at": "2025-10-29T15:00:00+09:00"
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
> - 픽업할 때 보여줄 `pickup_code`, `pickup_address`, 픽업 시간이 목록이나 상세에 없습니다.

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

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "status": "CANCELLED",
  "cancelled_at": "2025-10-29T16:00:00+09:00"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 401 | 로그인 필요 |
| 403 | 본인 예약이 아님 |
| 404 | 예약 정보 없음 |
| 409 | 이미 취소되었거나 취소 불가 상태 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요:** 결제한 예약을 취소하면 환불을 자동으로 만드는지, 고객이 [환불 요청](payments.md#3-환불-요청)을 따로 호출하는지

---

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
| 401 | 로그인 필요 |
| 403 | 해당 매장 상점주가 아님 |
| 404 | 예약 정보 없음 |
| 409 | 이미 픽업 완료되었거나 유효하지 않은 예약 상태 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요**
> - 상점주가 `reservation_id`를 알 방법이 없습니다. 상점주용 예약 목록 API(예: `GET /v1/stores/{store_id}/reservations`)가 필요하거나, `pickup_code`만으로 처리하는 방식(예: `POST /v1/stores/{store_id}/pickups`)을 검토해야 합니다.
> - `pickup_code` 발급 시점과 형식
> - 픽업 시간(`pickup_start` ~ `pickup_end`) 밖에서 처리할 수 있는지
