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
| `original_price` | int | O | 1 이상 99,999,999 이하 (1억 이상 거부) |
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
| 400 | 정상 가격은 1억 원 미만이어야 합니다. |
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
| GET | `/v1/products` | 공개 | 200 OK |

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

**응답**
검색 조건(검색어·카테고리·반경)에 맞는 상품을 하나 이상 가진 상점을 상점 단위로 묶어 돌려줍니다. `page`·`size`·`total`은 **상점 수** 기준입니다.

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `items[].store` | object | 상점 정보 |
| `items[].store.id` | UUID | 상점 ID |
| `items[].store.name` | string | 상점명 |
| `items[].store.pickup_address` | string | 픽업 주소 |
| `items[].store.latitude` | float \| null | 위도 (좌표가 없으면 null) |
| `items[].store.longitude` | float \| null | 경도 (좌표가 없으면 null) |
| `items[].distance` | float \| null | 거리 (위치 없이 검색하면 null) |
| `items[].unit` | string | 거리 단위 (`km`) |
| `items[].products` | [Product](#product-상품)[] | 그 상점의 조건 일치 상품 전부. 각 항목은 Product 필드 + 아래 `has_active_offer` |
| `items[].products[].has_active_offer` | bool | 진행 중인 할인 여부 |
| `page` | int | 현재 페이지 (상점 기준) |
| `size` | int | 페이지 크기 (상점 수) |
| `total` | int | 전체 상점 수 |

```json
{
  "items": [
    {
      "store": {
        "id": "22222222-2222-2222-2222-222222222222",
        "name": "월드컵 베이커리",
        "pickup_address": "서울시 마포구 월드컵북로 1",
        "latitude": 37.5563,
        "longitude": 126.9236
      },
      "distance": 0.42,
      "unit": "km",
      "products": [
        {
          "id": "11111111-1111-1111-1111-111111111111",
          "store_id": "22222222-2222-2222-2222-222222222222",
          "name": "모둠 식빵",
          "category": "베이커리",
          "description": "오늘 구운 식빵 5종",
          "original_price": 12000,
          "is_active": true,
          "product_image": ["https://example.com/bread.jpg"],
          "has_active_offer": true
        }
      ]
    }
  ],
  "page": 1,
  "size": 20,
  "total": 1
}
```

> **변경 근거:** 노션 원문은 `store_name`·`distance`·`unit`·`has_active_offer`만 있었으나, 사용자 결정으로 상품과 상점 정보를 함께 보여주되 상점 단위로 묶는 구조(`store` + `products[]`)로 바꿨습니다.

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | lat과 lng는 함께 입력해야 합니다. |
| 422 | radius_km 범위 오류 |

> **확정(2026-11-06):**
> - 위치(`lat`·`lng`) 없이 검색하면 반경 필터 없이 노출 중인 상점 전체를 대상으로 하고 `distance`는 `null`입니다. `unit`은 항상 `km`, 거리는 소수 둘째 자리까지입니다. `radius_km`만 보내면 무시합니다(단 0.1~20 범위 밖이면 400).
> - 거리는 위경도 하버사인 공식으로 계산합니다(PostGIS 없음). 좌표가 없는 상점은 위치를 지정하면 제외되고, 지정하지 않으면 `latitude`·`longitude`가 `null`로 나옵니다.
> - `store` 객체는 `id`, `name`, `pickup_address`, `latitude`, `longitude`입니다.
> - 상점 정렬: 위치가 있으면 가까운 순, 없으면 상점명 순입니다. `products[]`는 상품명 순이고 개수 상한은 없습니다.
> - 검색어는 부분 일치·대소문자 무시(상품명·설명), 최대 100자이며, 앞뒤 공백을 뺀 뒤 빈 문자열(공백만 입력)이면 검색어 조건 없이 조회합니다. 카테고리는 정확 일치입니다. 폐점·정지 상점, 노출 중단 상품, 정지된 할인은 나오지 않습니다.
> - `has_active_offer`는 예정·판매 중·품절 상태의 할인이 있으면 true입니다.
> - 형식·범위 오류는 이 프로젝트 공통 규칙에 따라 422 대신 400 `VALIDATION_ERROR`입니다.

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
| `original_price` | int | 1 이상 99,999,999 이하 (1억 이상 거부) |
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


## 6-1. 상품 재노출
| Method | URI | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/products/{product_id}/activate` | 상점주 (본인 상점) | 200 OK |

노출 중단된 상품을 다시 노출합니다(`is_active = true`). 예전 할인은 되살아나지 않습니다. 노출 상태 전환은 수정(`PATCH`)이 아니라 이 EP와 §6으로만 합니다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `product_id` | UUID | 상품 ID |

**요청 본문:** 없음

**응답:** [Product](#product-상품) (`is_active`는 `true`)

**에러** (검사 순서: 상품 존재 → 소유자 → 폐점 → 이미 노출 중)
| HTTP | error_code | 메시지 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `product_id`가 UUID 형식이 아님 |
| 400 | `STORE_CLOSED` | 폐점된 상점에서는 상품을 다시 노출할 수 없습니다. |
| 400 | `PRODUCT_ALREADY_ACTIVE` | 이미 노출 중인 상품입니다. |
| 401 | `UNAUTHORIZED` | 인증이 필요합니다. |
| 403 | `FORBIDDEN` | 본인 상점의 상품만 변경할 수 있습니다. |
| 404 | `NOT_FOUND` | 상품을 찾을 수 없습니다. |

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
| `items[].distance` | float \| null | 거리 (위치 없이 조회하면 null) |
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

> **확정(2026-11-06):** 위치 없이 조회하면 반경 필터 없이 조회하고 `distance`는 `null`입니다. 검색어는 상품명 부분 일치·대소문자 무시이며, 공백만 입력하면 검색어 조건 없이 조회합니다. 정렬 방향은 `distance`·`price`·`sales_end` 오름차순(가까운 순·낮은 가격순·마감 임박순), `discount_rate` 내림차순입니다. 동률이면 `sales_end` 오름차순, 그다음 `id` 순입니다.

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
| `status` | string (반복 가능) | X | `SCHEDULED`, `ON_SALE`, `SOLD_OUT` | `SCHEDULED` / `ON_SALE` / `SOLD_OUT` / `CLOSED`. 여러 번 주면 OR로 조회 (`?status=ON_SALE&status=SCHEDULED`). 생략하면 진행 중인 할인 전체(마감 전·중단 안 됨), `CLOSED`는 명시해야 조회 |
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
| Method | URI | 권한 | 성공 |
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
| `description` | string \| null | 상품 설명. 상품 설명이 비어 있으면 null |
| `product_image` | string[] | 상품 이미지 |
| `pickup_address` | string | 픽업 주소 |
| `latitude` | float \| null | 상점 위도. 상점이 좌표 없이 개설되면 null |
| `longitude` | float \| null | 상점 경도. 상점이 좌표 없이 개설되면 null |
| `notice` | string | 안내 문구(고정 문구) |
| `cancel_policy.cancellable_until` | datetime | 취소 가능 시각. `pickup_start` − 1시간 |
| `cancel_policy.description` | string | 취소 정책 설명(고정 문구) |

인증 없이 누구나 조회합니다. 판매 중단·마감·품절된 할인, 비활성 상품의 할인, 폐점 상점의 할인도 조회되며 상태는 `offer.status`·`offer.is_active`로 구분합니다. 환불 위약금 규칙은 `cancellable_until`과 같은 기준을 따릅니다.

**응답 예시**
```json
{
  "offer": { "...": "Offer 17개 필드" },
  "description": "오늘 구운 식빵 5종 모둠",
  "product_image": ["https://example.com/bread.jpg"],
  "pickup_address": "서울시 마포구 월드컵북로 1",
  "latitude": 37.5563,
  "longitude": 126.9236,
  "notice": "마감 시간이 가까운 상품으로 수량이 한정되어 있습니다. 픽업 시간 안에 매장을 방문해 예약 확인 코드를 보여주세요. 픽업 시간이 지나면 수령할 수 없습니다.",
  "cancel_policy": {
    "cancellable_until": "2026-11-04T17:00:00+09:00",
    "description": "픽업 시작 1시간 전까지 취소할 수 있습니다. 이후에는 취소가 제한되거나 위약금이 부과될 수 있습니다."
  }
}
```

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 잘못된 UUID 형식(`VALIDATION_ERROR`) |
| 404 | 할인 판매를 찾을 수 없습니다. |

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

**요청 본문:** 모든 필드가 선택이며 `null`은 허용하지 않습니다. 보낸 필드만 바뀝니다.
| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `sale_price` | int | `0 < x < original_price` |
| `initial_stock` | int | 1~9999. 늘리거나 줄인 만큼 `remaining_stock`도 같이 바뀌며, 이미 줄어든 수량보다 작게 줄일 수 없음. 바뀌면 재고 이력(`stock_log`, 사유 "할인 수정")에 증감량이 기록됨 |
| `sales_start` | datetime | timezone 필수 |
| `sales_end` | datetime | 판매 시작 이후, 현재 시각 이후 |
| `pickup_start` | datetime | |
| `pickup_end` | datetime | 판매 마감 이후, 픽업 시작 이후 |
| `is_active` | bool | `false`=판매 중단, `true`=재개. **다른 필드와 함께 보낼 수 없음** |

시간·가격 규칙은 보내지 않은 필드의 기존 값과 합친 결과로 [할인 등록](#7-할인-등록)과 같게 검증합니다. 수정 후 `status`는 시각·재고로 다시 계산됩니다. 예약 여부는 예약 기능이 생기기 전까지 항상 "예약 없음"으로 처리됩니다.

> **재개 조건:** 마감 전, 상품이 활성이고 상점이 폐점이 아니며, 같은 상품에 다른 진행 중 할인이 없어야 합니다. 할인 중단은 이 API의 `is_active=false` 또는 [할인 판매 중단](#12-할인-판매-중단)으로 합니다. 중단된 할인은 [재등록](#13-할인-재등록)할 수 없습니다.

**응답:** [Offer](#offer-할인)

**에러**
| HTTP | `error_code` | 메시지 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 수정할 항목이 없습니다. / 항목은(는) null일 수 없습니다. / 할인 가격은 정상 가격보다 낮아야 합니다. / 판매 마감 시간은 판매 시작 시간 이후여야 합니다. / 판매 마감 시간은 현재 시각 이후여야 합니다. / 픽업 마감 시간은 판매 마감 시간 이후여야 합니다. / 픽업 마감 시간은 픽업 시작 시간 이후여야 합니다. / 최초 수량은 현재까지 줄어든 수량(n개)보다 작을 수 없습니다. / `is_active`와 다른 필드 동시 전송 |
| 400 | `OFFER_HAS_RESERVATIONS` | 예약이 있는 할인은 수정할 수 없습니다. 재등록을 이용하세요. |
| 400 | `OFFER_CLOSED` | 종료된 할인은 수정할 수 없습니다. / 이미 중단된 할인입니다. |
| 400 | `OFFER_ENDED` | 판매가 끝난 할인은 중단할 수 없습니다. / 판매가 끝난 할인은 재개할 수 없습니다. |
| 400 | `OFFER_ALREADY_ACTIVE` | 이미 활성화된 할인입니다. |
| 400 | `PRODUCT_INACTIVE` | 비활성화된 상품의 할인은 재개할 수 없습니다. |
| 400 | `OFFER_ALREADY_OPEN` | 이미 진행 중인 할인 판매가 있습니다. |
| 400 | `STORE_CLOSED` | 폐점된 상점에서는 할인을 재개할 수 없습니다. |
| 401 | `UNAUTHORIZED` | 인증이 필요합니다. |
| 403 | `FORBIDDEN` | 본인 상점의 할인만 수정할 수 있습니다. |
| 404 | `NOT_FOUND` | 할인 판매를 찾을 수 없습니다. |

---

## 12. 할인 판매 중단
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/offers/{offer_id}/deactivate` | 상점주 (본인 상점) | 200 OK |

할인을 즉시 중단합니다(`is_active = false`, `status = CLOSED`). 상품은 바꾸지 않습니다. `cancel_reservations`가 `true`이면 기존 예약을 상점주 사유로 취소하고 전액 환불을 요청합니다(예약·결제 모듈 연계). 물리 삭제는 하지 않습니다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `offer_id` | UUID | 할인 ID |

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `reason` | string | O | 중단 사유 (1~200자, 공백만 불가). 현재 저장하지 않습니다 |
| `cancel_reservations` | boolean | | 기본 `false`. `true`이면 기존 예약을 상점주 사유로 취소하고 전액 환불 요청 |

**응답:** `{"offer": Offer, "cancelled_reservation_count": int}`. `offer`는 [Offer](#offer-할인)와 같은 필드이며 `status`는 `CLOSED`, `is_active`는 `false`입니다.

**에러**
| HTTP | 메시지 |
| --- | --- |
| 400 | 이미 중단된 할인입니다. (`OFFER_CLOSED`) |
| 400 | 픽업 완료된 예약이 있어 일괄 취소할 수 없습니다. (`cancel_reservations=true`일 때만) |
| 400 | 검증 오류 (`reason` 누락·빈 값·공백만·201자 이상, 본문 없음, 잘못된 UUID) |
| 401 | 인증이 필요합니다. |
| 403 | 본인 상점의 할인만 중단할 수 있습니다. |
| 404 | 할인 판매를 찾을 수 없습니다. |

> **확인 필요:**
> - `reason`은 현재 저장하지 않습니다(후속에 컬럼 추가).
> - `cancel_reservations=false`이면 예약은 유지됩니다.
> - 예약 모듈 구현 전까지는 `cancel_reservations=true`여도 실제 취소·환불 없이 `cancelled_reservation_count`는 항상 0입니다.
> - 판매 마감이 지난 활성 할인도 중단할 수 있습니다.
> - 중단한 할인은 마감 전이고 다른 진행 중 할인이 없고 상품이 활성이면 [할인 수정](#11-할인-수정)의 `is_active=true`로 재개할 수 있으나 취소된 예약은 복구되지 않습니다.

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
