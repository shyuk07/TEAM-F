# payments API

모의 결제와 환불. 모듈: `src/payments`
테이블: `payments`, `refunds` (포인트는 `users`, `point_log`)

[← 전체 목록](README.md)

포인트 적립·사용·복구·회수는 별도 API 없이 이 모듈의 서비스가 처리합니다. 규칙은 [README의 포인트 정책](README.md#포인트-정책-노션-포인트-내역-조회-페이지)을 따릅니다.

---

## 1. 결제 요청
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/payments` | 회원 (본인 예약) | 201 Created |

사용자가 예약한 상품에 대해 결제를 요청한다. 예약 정보를 확인한 후 결제를 진행하고 결제 결과를 반환한다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reservation_id` | UUID | O | 결제할 예약 ID |
| `use_point` | integer | X | 사용할 포인트(0 이상, 100P 단위, 기본 0). `amount = 예약 총액 − use_point`. 전액 포인트면 `amount`는 0 |

```json
{
  "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
  "use_point": 1000
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 결제 ID |
| `reservation_id` | UUID | 예약 ID |
| `amount` | integer | 결제 금액 |
| `status` | string | 결제 상태 |
| `paid_at` | datetime | 결제 완료 시간 |

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 12000,
  "status": "PAID",
  "paid_at": "2026-10-29T15:00:00+09:00"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 400 | 결제할 수 없는 예약 (`RESERVATION_NOT_PAYABLE`), 결제 실패 (`PAYMENT_FAILED`) |
| 400 | 사용 포인트가 결제 총액 초과 (`INVALID_POINT_AMOUNT`), 사용 포인트 음수(요청 검증)·포인트 단위·잔액 위반 (`VALIDATION_ERROR`) |
| 401 | 로그인 인증 필요 |
| 404 | 예약 정보 없음 |
| 409 | 이미 결제된 예약 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 |

> **확인 필요**
> - 포인트: 결제 성공 시 `amount`(포인트 사용분 제외)의 1%를 적립하고, 환불(예약 취소 포함) 시 사용 포인트 전액을 복구한 뒤 적립분을 회수한다(응답에는 포인트 필드 없음). 결제 실패 시 사용 포인트는 되돌아간다.
> - 다른 사람의 예약을 결제하려 할 때 응답 (403이 없음)
> - 모의 결제 실패를 어떻게 만들지 (`failed_at`, `failed_response` 컬럼이 있음)

---

## 2. 결제 정보 조회
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/payments/{payment_id}` | 회원 (본인 결제) | 200 OK |

결제 ID를 통해 결제 금액, 결제 상태 및 결제 완료 시간을 조회한다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `payment_id` | UUID | 결제 ID |

**요청 본문:** 없음

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 결제 ID |
| `reservation_id` | UUID | 예약 ID |
| `amount` | integer | 결제 금액 |
| `status` | string | 결제 상태 |
| `paid_at` | datetime | 결제 완료 시간 |

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "reservation_id": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 12000,
  "status": "PAID",
  "paid_at": "2026-10-29T15:00:00+09:00"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 401 | 로그인 인증 필요 |
| 403 | 결제 정보 조회 권한 없음 |
| 404 | 결제 정보 없음 |
| 422 | 결제 ID 형식 오류 |

---

## 3. 환불 요청
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/payments/{payment_id}/refunds` | 회원 (본인 결제) | 201 Created |

결제된 상품의 환불을 처리한다. 취소 정책에 따라 위약금을 계산하고 실제 환불 금액을 결정한다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `payment_id` | UUID | 결제 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reason` | string | O | 환불 사유. 앞뒤 공백(줄바꿈·탭·전각 공백 포함)을 뺀 길이가 1~200자. 공백만 있으면 400. 저장은 앞뒤 공백을 뺀 값으로 한다(단어 사이 공백은 유지). 요청 원문은 최대 1000자(남용 방지용 임시값) |

```json
{
  "reason": "개인 사정으로 예약 취소"
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 환불 ID |
| `payment_id` | UUID | 결제 ID |
| `refund_amount` | integer | 실제 환불 금액 |
| `penalty_amount` | integer | 위약금 |
| `status` | string | 환불 상태 |

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "payment_id": "660e8400-e29b-41d4-a716-446655440000",
  "refund_amount": 10000,
  "penalty_amount": 2000,
  "status": "COMPLETED"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 400 | 환불할 수 없는 결제 |
| 400 | 취소 가능 시각이 지남 (`CANCELLATION_DEADLINE_PASSED`, "취소 가능 시각이 지나 취소·환불할 수 없습니다.") |
| 401 | 로그인 인증 필요 |
| 403 | 환불 처리 권한 없음 |
| 404 | 결제 정보 없음 |
| 409 | 이미 환불 처리된 결제 |
| 422 | 요청 데이터 형식 오류 |
| 500 | 서버 오류 (예약·결제 데이터 불일치 `DATA_INCONSISTENT` 포함) |

환불 요청은 할인의 취소 가능 시각(`cancel_policy.cancellable_until` = 픽업 시작 1시간 전, [catalog 할인 상세](catalog.md#10-할인-상세))까지만 할 수 있다. 정확히 그 시각은 허용하고, 지나면 400이다. [예약 취소](reservations.md#3-예약-취소)도 같은 기준이라 어느 쪽으로도 마감을 넘길 수 없다. 위약금은 0원이다.
검사 순서: 404(결제 없음) → 403(본인 아님) → 500(데이터 불일치) → 409(이미 환불) → 400(환불할 수 없는 상태) → 400(취소 가능 시각 지남).

> **노션과 다른 점:** 노션의 응답 필드 설명은 결제 조회 설명이 복사돼 있었습니다(`id: 결제 ID`, `reservation_id`, `amount`, `paid_at`). 이 문서는 응답 예시에 맞게 고쳤습니다.
>
> **확인 필요**
> - 위약금 계산 규칙 (픽업 시간까지 남은 시간 기준 등)
> - 환불 시 예약 상태와 재고를 함께 되돌리는지, [예약 취소](reservations.md#3-예약-취소)와의 순서
> - 응답에 `completed_at` 포함 여부 (환불 정보 조회에는 있음)

---

## 4. 환불 정보 조회
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/refunds/{refund_id}` | 회원 (본인 환불) | 200 OK |

환불 ID를 통해 실제 환불 금액, 위약금 및 환불 처리 상태를 조회한다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `refund_id` | UUID | 환불 ID |

**요청 본문:** 없음

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 환불 ID |
| `payment_id` | UUID | 결제 ID |
| `refund_amount` | integer | 실제 환불 금액 |
| `penalty_amount` | integer | 위약금 |
| `status` | string | 환불 상태 |
| `completed_at` | datetime | 환불 완료 시간 |

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440000",
  "payment_id": "660e8400-e29b-41d4-a716-446655440000",
  "refund_amount": 10000,
  "penalty_amount": 2000,
  "status": "COMPLETED",
  "completed_at": "2026-10-29T16:00:00+09:00"
}
```

**에러**
| HTTP | 상황 |
| --- | --- |
| 401 | 로그인 인증 필요 |
| 403 | 환불 정보 조회 권한 없음 |
| 404 | 환불 정보 없음 |
| 422 | 환불 ID 형식 오류 |
