# catalog API

상품, 마감 할인, 재고. 모듈: `src/catalog`
테이블: `products`, `discount_offers`, `stock_log`

[← 전체 목록](README.md)

## 공통 객체

여러 API가 같은 형태를 돌려줍니다. 각 API의 응답에서 아래 이름으로 참조합니다.

### Product (상품)
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 상품 ID |
| `store_id` | UUID | 상점 ID |
| `name` | string | 상품명 |
| `category` | string \| null | 카테고리 |
| `description` | string \| null | 설명 |
| `original_price` | int | 정상 가격 |
| `is_active` | bool | 노출 여부 |
| `product_image` | string[] | 이미지 URL 목록 (최대 10개) |

### Offer (할인)
| 필드 | 타입 | 설명 | DB 컬럼 |
| --- | --- | --- | --- |
| `id` | UUID | 할인 ID | `discount_offers.id` |
| `product_id` | UUID | 상품 ID | `discount_offers.product_id` |
| `store_id` | UUID | 상점 ID | `products.store_id` (조인) |
| `store_name` | string | 상점명 | `stores.name` (조인) |
| `product_name` | string | 상품명 | `products.name` (조인) |
| `original_price` | int | 정상 가격 | `products.original_price` (조인) |
| `sale_price` | int | 할인 가격 | `discount_offers.sale_price` |
| `discount_rate` | int | 할인율(%) | 계산 값 |
| `initial_stock` | int | 최초 수량 | `discount_offers.initial_stock` |
| `remaining_stock` | int | 남은 수량 | `discount_offers.remaining_stock` |
| `is_sold_out` | bool | 품절 여부 | 계산 값 (`remaining_stock == 0`) |
| `sales_start` | datetime | 판매 시작 | `discount_offers.sales_start` |
| `sales_end` | datetime | 판매 마감 | `discount_offers.sales_end` |
| `pickup_start` | datetime | 픽업 시작 | `discount_offers.pickup_start` |
| `pickup_end` | datetime | 픽업 마감 | `discount_offers.pickup_end` |
| `status` | string | `SCHEDULED` \| `ON_SALE` \| `SOLD_OUT` \| `CLOSED` | `discount_offers.status` |
| `is_active` | bool | 활성 여부 | `discount_offers.is_active` |

> **확인 필요:** `discount_rate` 계산식 (예: `round((1 - sale_price / original_price) * 100)` 또는 버림)

---

## 1. 상품 등록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/stores/{store_id}/products` | 상점주 (본인 상점) | 201 Created |

상점주가 본인 상점에 상품을 등록합니다. 등록 시 `is_active = true`

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `store_id` | UUID | 상점 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 조건 |
| --- | --- | --- | --- |
| `name` | string | O | 1~200자 |
| `category` | string | X | 최대 80자 |
| `description` | string | X | |
| `original_price` | int | O | 0보다 큼 |
| `product_image` | string[] | X | 최대 10개 |

```json
{
  "name": "샌드위치",
  "category": "베이커리",
  "description": "당일 생산 햄치즈 샌드위치",
  "original_price": 6000,
  "product_image": ["https://example.com/images/sandwich.jpg"]
}
```

**응답:** [Product](#product-상품)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 정상 가격은 0보다 커야 합니다. |
| 400 | 승인되지 않은 상점에는 상품을 등록할 수 없습니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점에만 상품을 등록할 수 있습니다. |
| 404 | 상점을 찾을 수 없습니다. |
| 422 | 요청 형식 오류 |

> **확인 필요:** 폐점한 상점에 등록할 때의 에러 메시지 (상점 폐점 페이지에 "폐점된 상점에서는 상품을 등록할 수 없다"는 규칙이 있음)

---

## 2. 상점 상품 목록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/stores/{store_id}/products` | 공개 | 200 OK |

상점의 상품(대표 메뉴) 목록을 조회합니다.

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `store_id` | UUID | 상점 ID |

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `category` | string | X | | 카테고리 필터 |
| `is_active` | bool | X | true | 활성 상품만 조회 |
| `page` | int | X | 1 | 페이지 |
| `size` | int | X | 20 | 페이지 크기 |

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `items` | [Product](#product-상품)[] | 상품 목록 |
| `page` | int | 현재 페이지 |
| `size` | int | 페이지 크기 |
| `total` | int | 전체 개수 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 404 | 상점을 찾을 수 없습니다. |
| 422 | page는 1 이상이어야 합니다. |

> **확인 필요:** 공개 API에서 `is_active=false`(노출 중단 상품)를 누구나 볼 수 있는지. 상점주 본인만 허용하는 것을 제안합니다.

---

## 3. 상품 검색
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/products/search` | 공개 | 200 OK |

위치 기준 반경 내 상점의 상품을 키워드·카테고리로 검색합니다.

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `keyword` | string | X | | 상품명·설명 검색어 |
| `category` | string | X | | 카테고리 |
| `lat` | float | X | | 위도(-90~90). `lng`와 함께 입력 |
| `lng` | float | X | | 경도(-180~180) |
| `radius_km` | float | X | 3 | 검색 반경(0.1~20km) |
| `page` | int | X | 1 | 페이지 |
| `size` | int | X | 20 | 페이지 크기 |

**응답 (노션 원문)**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `items[].store_name` | string | 상점명 |
| `items[].distance` | float | 거리 |
| `items[].unit` | string | 거리 단위 |
| `items[].has_active_offer` | bool | 진행 중인 할인 여부 |
| `page` | int | 현재 페이지 |
| `size` | int | 페이지 크기 |
| `total` | int | 전체 개수 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | lat과 lng는 함께 입력해야 합니다. |
| 422 | radius_km 범위 오류 |

> **확인 필요**
> - 응답 항목에 상품 정보가 없습니다. 각 항목을 `{ "product": Product, "store_name", "distance", "unit", "has_active_offer" }` 형태로 하는 것을 제안합니다.
> - 위치 없이 검색하면 `distance`를 어떻게 줄지 (`null` 제안)
> - 거리 계산 방법 (위경도로 하버사인 공식 계산 등). PostGIS는 현재 스택에 없습니다.
> - **FastAPI:** 이 경로는 `/v1/products/{product_id}`보다 먼저 등록해야 합니다.

---

## 4. 상품 상세
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/products/{product_id}` | 공개 | 200 OK |

상품 상세 정보를 조회합니다.

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `product_id` | UUID | 상품 ID |

**응답**
[Product](#product-상품)의 모든 필드에 아래 필드를 더합니다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `store_name` | string | 상점명 |
| `pickup_address` | string | 픽업 주소 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 404 | 상품을 찾을 수 없습니다. |

> **노션과 다른 점:** 노션은 상품 하나를 `items` 배열로 감싸고 그 옆에 `store_name`, `pickup_address`를 두었습니다. 상세 API라서 단일 객체로 적었습니다.

---

## 5. 상품 수정
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/products/{product_id}` | 상점주 (본인 상점) | 200 OK |

상품 정보를 부분 수정합니다. 보낸 필드만 변경합니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `product_id` | UUID | 상품 ID |

**요청 본문:** 모든 필드가 선택이고, 최소 1개 필드가 필요합니다.
| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `name` | string | 1~200자 |
| `category` | string | 최대 80자 |
| `description` | string | |
| `original_price` | int | 0보다 큼 |
| `product_image` | string[] | 최대 10개 |

```json
{
  "original_price": 6500
}
```

**응답:** [Product](#product-상품)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 수정할 항목이 없습니다. |
| 400 | 정상 가격은 진행 중인 할인 가격보다 커야 합니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 상품만 수정할 수 있습니다. |
| 404 | 상품을 찾을 수 없습니다. |

---

## 6. 상품 노출 중단
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/products/{product_id}/deactivate` | 상점주 (본인 상점) | 200 OK |

상품을 비활성화(`is_active = false`)합니다. 물리 삭제는 하지 않습니다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `product_id` | UUID | 상품 ID |

**요청 본문:** 없음

**응답:** [Product](#product-상품) (`is_active`는 `false`)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 진행 중인 할인 판매가 있어 비활성화할 수 없습니다. |
| 400 | 이미 비활성화된 상품입니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 상품만 변경할 수 있습니다. |
| 404 | 상품을 찾을 수 없습니다. |

> **확인 필요:** 다시 노출하는 API가 없습니다. 필요하면 `POST /v1/products/{product_id}/activate`를 제안합니다.

---

## 7. 할인 등록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/products/{product_id}/offers` | 상점주 (본인 상점) | 201 Created |

등록된 상품에 할인 판매를 등록합니다. `remaining_stock`은 `initial_stock`으로 초기화하고 `stock_log`에 최초 입고를 기록합니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `product_id` | UUID | 상품 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 조건 |
| --- | --- | --- | --- |
| `sale_price` | int | O | `0 < x < original_price` |
| `initial_stock` | int | O | 1~9999 |
| `sales_start` | datetime | X | 기본값은 현재 시각 |
| `sales_end` | datetime | O | `sales_start`보다 뒤 |
| `pickup_start` | datetime | O | `pickup_end`보다 앞 |
| `pickup_end` | datetime | O | `sales_end` 이후 |

```json
{
  "sale_price": 3000,
  "initial_stock": 10,
  "sales_end": "2026-10-29T20:00:00+09:00",
  "pickup_start": "2026-10-29T19:00:00+09:00",
  "pickup_end": "2026-10-29T21:00:00+09:00"
}
```

**응답:** [Offer](#offer-할인)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 할인 가격은 정상 가격보다 낮아야 합니다. |
| 400 | 판매 마감 시간은 판매 시작 시간 이후여야 합니다. |
| 400 | 픽업 마감 시간은 판매 마감 시간 이후여야 합니다. |
| 400 | 비활성화된 상품은 할인 등록할 수 없습니다. |
| 400 | 이미 진행 중인 할인 판매가 있습니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 상품만 할인 등록할 수 있습니다. |
| 404 | 상품을 찾을 수 없습니다. |

> **확인 필요:** 등록 시 `status` 결정 규칙 (`sales_start`가 미래면 `SCHEDULED`, 아니면 `ON_SALE`로 제안)

---

## 8. 주변 할인 목록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/offers` | 공개 | 200 OK |

위치 기준 반경 내 할인 상품을 조회합니다. 기본값으로 판매 중(`ON_SALE`)만 보여줍니다.

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `lat` | float | X | | 위도 |
| `lng` | float | X | | 경도 |
| `radius_km` | float | X | 3 | 반경(0.1~20km) |
| `category` | string | X | | 카테고리 |
| `keyword` | string | X | | 상품명 검색어 |
| `status` | string | X | `ON_SALE` | `SCHEDULED` / `ON_SALE` / `SOLD_OUT` / `CLOSED` |
| `sort` | string | X | `sales_end` | `distance` / `price` / `sales_end` / `discount_rate` |
| `page` | int | X | 1 | 페이지 |
| `size` | int | X | 20 | 페이지 크기 |

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `items[].offer` | [Offer](#offer-할인) | 할인 정보 |
| `items[].distance` | float | 거리 |
| `items[].unit` | string | 거리 단위 |
| `page` | int | 현재 페이지 |
| `size` | int | 페이지 크기 |
| `total` | int | 전체 개수 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | lat과 lng는 함께 입력해야 합니다. |
| 400 | distance 정렬은 위치 정보가 필요합니다. |
| 422 | 허용되지 않는 status 값입니다. |

> **확인 필요:** 정렬 방향 (`price`는 오름차순, `discount_rate`는 내림차순, `sales_end`는 마감 임박순으로 제안)

---

## 9. 상점 할인 목록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/stores/{store_id}/offers` | 공개 | 200 OK |

특정 상점의 할인 목록을 조회합니다.

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `store_id` | UUID | 상점 ID |

**쿼리 매개변수**
| 이름 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `status` | string | X | `ON_SALE` | `SCHEDULED` / `ON_SALE` / `SOLD_OUT` / `CLOSED` |
| `page` | int | X | 1 | 페이지 |
| `size` | int | X | 20 | 페이지 크기 |

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `items` | [Offer](#offer-할인)[] | 할인 목록 |
| `page` | int | 현재 페이지 |
| `size` | int | 페이지 크기 |
| `total` | int | 전체 개수 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 404 | 상점을 찾을 수 없습니다. |

---

## 10. 할인 상세
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| GET | `/v1/offers/{offer_id}` | 공개 | 200 OK |

구매 결정에 필요한 할인 상세 정보를 조회합니다.

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `offer` | [Offer](#offer-할인) | 할인 정보 |
| `description` | string | 상품 설명 |
| `product_image` | string[] | 상품 이미지 |
| `pickup_address` | string | 픽업 주소 |
| `latitude` | float | 상점 위도 |
| `longitude` | float | 상점 경도 |
| `notice` | string | 안내 문구 |
| `cancel_policy.cancellable_until` | datetime | 취소 가능 시각 |
| `cancel_policy.description` | string | 취소 정책 설명 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 404 | 할인 판매를 찾을 수 없습니다. |

> **확인 필요:** `notice`, `cancel_policy`를 저장할 컬럼이 없습니다. 고정 문구인지, 규칙으로 계산하는지(예: `cancellable_until = pickup_start − 1시간`) 정해야 합니다. 환불 위약금 규칙과 같은 기준을 써야 합니다.

---

## 11. 할인 수정
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| PATCH | `/v1/offers/{offer_id}` | 상점주 (본인 상점) | 200 OK |

예약이 한 건도 없을 때만 할인 정보를 수정합니다. 예약이 있으면 [재등록](#13-할인-재등록)을 사용합니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |

**요청 본문:** 모든 필드가 선택입니다.
| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `sale_price` | int | `0 < x < original_price` |
| `initial_stock` | int | 1~9999 |
| `sales_start` | datetime | |
| `sales_end` | datetime | |
| `pickup_start` | datetime | |
| `pickup_end` | datetime | |

**응답:** [Offer](#offer-할인)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요. |
| 400 | 종료된 할인은 수정할 수 없습니다. |
| 400 | 할인 가격은 정상 가격보다 낮아야 합니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 할인만 수정할 수 있습니다. |
| 404 | 할인 판매를 찾을 수 없습니다. |

> **확인 필요:** 시간 필드를 일부만 바꿀 때도 할인 등록과 같은 시간 순서 검증을 하는지, `initial_stock`을 바꾸면 `remaining_stock`도 같은 값으로 바꾸는지

---

## 12. 할인 판매 중단
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/offers/{offer_id}/close` | 상점주 (본인 상점) | 200 OK |

할인을 즉시 중단(`is_active = false`, `status = CLOSED`)합니다. `cancel_reservations = true`이면 기존 예약을 상점주 사유로 취소·전액 환불 요청합니다(예약/결제 모듈 연계).

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 조건 |
| --- | --- | --- | --- |
| `reason` | string | O | 최대 200자 |
| `cancel_reservations` | bool | X | 기본값 `false` |

```json
{
  "reason": "재료 소진",
  "cancel_reservations": true
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `offer` | [Offer](#offer-할인) | 중단된 할인 |
| `cancelled_reservation_count` | int | 취소된 예약 수 |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 이미 중단된 할인입니다. |
| 400 | 픽업 완료된 예약이 있어 일괄 취소할 수 없습니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 할인만 중단할 수 있습니다. |
| 404 | 할인 판매를 찾을 수 없습니다. |

> **확인 필요**
> - `reason`을 저장할 컬럼이 없습니다.
> - `cancel_reservations = false`일 때 기존 예약은 그대로 픽업할 수 있는지

---

## 13. 할인 재등록
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/offers/{offer_id}/relist` | 상점주 (본인 상점) | 201 Created |

기존 할인을 비활성화하고 새 가격·수량으로 신규 할인을 생성합니다. 한 트랜잭션으로 처리하며 기존 예약은 유지합니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 기존 할인 ID |

**요청 본문:** [할인 등록](#7-할인-등록)과 같습니다.

**응답:** 새로 만든 [Offer](#offer-할인)

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 이미 중단된 할인은 재등록할 수 없습니다. |
| 400 | 할인 가격은 정상 가격보다 낮아야 합니다. |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 할인만 재등록할 수 있습니다. |
| 404 | 할인 판매를 찾을 수 없습니다. |

---

## 14. 재고 수동 조정
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/offers/{offer_id}/stock-adjustments` | 상점주 (본인 상점) | 200 OK |

상점주가 실제 재고에 맞춰 남은 수량을 증감합니다. 증가 시 `initial_stock`도 함께 늘립니다.

구현 참고: 할인 행을 `with_for_update()`로 잠그고, 조정 결과를 `stock_log`에 기록합니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 조건 |
| --- | --- | --- | --- |
| `amount` | int | O | 0 제외. `+` 입고, `-` 차감 |
| `reason` | string | X | 최대 200자 |

```json
{
  "amount": -2,
  "reason": "포장 파손"
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |
| `initial_stock` | int | 조정 후 최초 수량 |
| `remaining_stock` | int | 조정 후 남은 수량 |
| `is_sold_out` | bool | 품절 여부 |
| `status` | string | 할인 상태 |
| `log_id` | UUID | 생성된 `stock_log` ID |

**에러**
| HTTP | 메시지 |
| --- | --- |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 이력만 조회할 수 있습니다. (노션 원문) |
| 404 | 할인 판매를 찾을 수 없습니다. |

> **확인 필요**
> - 403 메시지가 조회 API의 문구로 보입니다. "본인 상점의 재고만 조정할 수 있습니다."를 제안합니다.
> - 남은 재고보다 많이 빼는 경우(400), `amount = 0`(400 또는 422), 중단된 할인을 조정하는 경우 에러가 없습니다.
> - 재고가 0이 되면 `SOLD_OUT`, 0에서 늘면 `ON_SALE`로 바꾸는지
> - `reason`을 저장할 컬럼이 `stock_log`에 없습니다.
