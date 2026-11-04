# API 명세서 (Reference)

마감 직전(Last Call) 백엔드의 API 명세입니다.

- **원본:** 팀 노션 페이지 "ㅇㅇㅇㅇㅇ"의 API 하위 페이지 29개 (2026-11-02 기준)
- **Method와 URI:** 노션에는 `/v1/users/me`, `/v1/users/me/points` 두 개만 적혀 있습니다. 나머지는 REST 규칙에 맞춰 이 문서에서 **제안**한 값입니다. 팀 확정 후 노션과 이 문서를 함께 고칩니다.
- **본문:** 설명, 헤더, 요청, 응답, 에러는 노션 내용을 옮겼습니다. 노션에 없거나 서로 맞지 않는 부분은 각 API의 "확인 필요"와 [이슈 목록](#팀-확인이-필요한-항목)에 모았습니다.

## 문서 구성
| 파일 | 모듈 | API 수 |
| --- | --- | --- |
| [auth.md](auth.md) | `src/auth` 회원·인증·포인트 | 5 |
| [stores.md](stores.md) | `src/stores` 상점 | 2 |
| [catalog.md](catalog.md) | `src/catalog` 상품·할인·재고 | 14 |
| [reservations.md](reservations.md) | `src/reservations` 예약·픽업 | 4 |
| [payments.md](payments.md) | `src/payments` 결제·환불 | 4 |

DB 테이블과 컬럼은 `.claude/skills/db-schema/SKILL.md`를 따릅니다.

## 전체 API 목록
권한: **공개** = 토큰 없이 호출 가능, **회원** = 로그인한 모든 사용자, **고객** = `CUSTOMER`, **상점주** = 승인된 상점주

| # | 모듈 | API | Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | auth | [회원가입](auth.md#1-회원가입) | POST | `/v1/auth/signup` | 공개 | 201 |
| 2 | auth | [로그인](auth.md#2-로그인) | POST | `/v1/auth/login` | 공개 | 200 |
| 3 | auth | [로그아웃](auth.md#3-로그아웃) | POST | `/v1/auth/logout` | 회원 | 204 |
| 4 | auth | [내 정보 조회](auth.md#4-내-정보-조회) | GET | `/v1/users/me` (노션) | 회원 | 200 |
| 5 | auth | [포인트 내역 조회](auth.md#5-포인트-내역-조회) | GET | `/v1/users/me/points` (노션) | 회원 | 200 |
| 6 | stores | [상점 개설](stores.md#1-상점-개설) | POST | `/v1/stores` | 상점주 | 201 |
| 7 | stores | [상점 폐점](stores.md#2-상점-폐점) | POST | `/v1/stores/{store_id}/close` | 상점주(본인) | 200 |
| 8 | catalog | [상품 등록](catalog.md#1-상품-등록) | POST | `/v1/stores/{store_id}/products` | 상점주(본인) | 201 |
| 9 | catalog | [상점 상품 목록](catalog.md#2-상점-상품-목록) | GET | `/v1/stores/{store_id}/products` | 공개 | 200 |
| 10 | catalog | [상품 검색](catalog.md#3-상품-검색) | GET | `/v1/products/search` | 공개 | 200 |
| 11 | catalog | [상품 상세](catalog.md#4-상품-상세) | GET | `/v1/products/{product_id}` | 공개 | 200 |
| 12 | catalog | [상품 수정](catalog.md#5-상품-수정) | PATCH | `/v1/products/{product_id}` | 상점주(본인) | 200 |
| 13 | catalog | [상품 노출 중단](catalog.md#6-상품-노출-중단) | POST | `/v1/products/{product_id}/deactivate` | 상점주(본인) | 200 |
| 14 | catalog | [할인 등록](catalog.md#7-할인-등록) | POST | `/v1/products/{product_id}/offers` | 상점주(본인) | 201 |
| 15 | catalog | [주변 할인 목록](catalog.md#8-주변-할인-목록) | GET | `/v1/offers` | 공개 | 200 |
| 16 | catalog | [상점 할인 목록](catalog.md#9-상점-할인-목록) | GET | `/v1/stores/{store_id}/offers` | 공개 | 200 |
| 17 | catalog | [할인 상세](catalog.md#10-할인-상세) | GET | `/v1/offers/{offer_id}` | 공개 | 200 |
| 18 | catalog | [할인 수정](catalog.md#11-할인-수정) | PATCH | `/v1/offers/{offer_id}` | 상점주(본인) | 200 |
| 19 | catalog | [할인 판매 중단](catalog.md#12-할인-판매-중단) | POST | `/v1/offers/{offer_id}/deactivate` | 상점주(본인) | 200 |
| 20 | catalog | [할인 재등록](catalog.md#13-할인-재등록) | POST | `/v1/offers/{offer_id}/relist` | 상점주(본인) | 201 |
| 21 | catalog | [재고 수동 조정](catalog.md#14-재고-수동-조정) | POST | `/v1/offers/{offer_id}/stock-adjustments` | 상점주(본인) | 200 |
| 22 | reservations | [예약 생성](reservations.md#1-예약-생성) | POST | `/v1/reservations` | 회원 | 201 |
| 23 | reservations | [내 예약 목록 조회](reservations.md#2-내-예약-목록-조회) | GET | `/v1/users/me/reservations` | 회원 | 200 |
| 24 | reservations | [예약 취소](reservations.md#3-예약-취소) | POST | `/v1/reservations/{reservation_id}/cancel` | 회원(본인) | 200 |
| 25 | reservations | [픽업 완료](reservations.md#4-픽업-완료) | POST | `/v1/reservations/{reservation_id}/pickup` | 상점주(해당 매장) | 200 |
| 26 | payments | [결제 요청](payments.md#1-결제-요청) | POST | `/v1/payments` | 회원 | 201 |
| 27 | payments | [결제 정보 조회](payments.md#2-결제-정보-조회) | GET | `/v1/payments/{payment_id}` | 회원(본인) | 200 |
| 28 | payments | [환불 요청](payments.md#3-환불-요청) | POST | `/v1/payments/{payment_id}/refunds` | 회원(본인) | 201 |
| 29 | payments | [환불 정보 조회](payments.md#4-환불-정보-조회) | GET | `/v1/refunds/{refund_id}` | 회원(본인) | 200 |

### URI를 정한 규칙
- 모든 경로는 노션에 있는 `/v1` 접두사를 씁니다.
- 자원은 복수형 명사(`/stores`, `/products`, `/offers`)로 씁니다.
- 부모 자원이 꼭 필요한 생성·목록은 하위 경로로 둡니다. (상품 등록 → `/stores/{store_id}/products`, 할인 등록 → `/products/{product_id}/offers`)
- 할인 수정(`PATCH /v1/offers/{offer_id}`)은 필드 수정과 함께 `is_active`로 판매 중단·재개를 받는 예외입니다.
- 상태만 바꾸는 동작(폐점, 노출 중단, 판매 중단, 재등록, 취소, 픽업)은 `POST /{id}/동사` 형태로 둡니다. 요청 본문이 있거나 부수 효과(환불, 재고 이력)가 있어서 `PATCH`로 표현하기 어렵기 때문입니다.
- 로그인한 사용자 기준 조회는 노션의 `/v1/users/me/...` 형태에 맞춥니다.
- **FastAPI 주의:** `/v1/products/search`는 `/v1/products/{product_id}`보다 **먼저** 등록해야 합니다.

## 공통 규칙

### 인증
- 헤더: `Authorization: Bearer {access_token}`
- 로그인 요청은 JSON(`application/json`, `{"email", "password"}`)입니다. Swagger에서는 로그인 응답의 `access_token`을 Authorize에 붙여 넣어 씁니다.
- 토큰 내용 (노션 로그인 페이지):

| 클레임 | 값 |
| --- | --- |
| `sub` | 사용자 ID (UUID) |
| `role` | 사용자 역할 |
| `jti` | 토큰마다 새로 만드는 UUID |
| `exp` | 발급 30분 후 |

- 로그인이 필요한 모든 API는 토큰 검증 후 `token_blacklist`를 조회합니다. 로그아웃한 토큰이면 `401 TOKEN_REVOKED`입니다.

### 역할 (`users.role`)
| 값 | 의미 | 출처 |
| --- | --- | --- |
| `CUSTOMER` | 일반 고객 | 회원가입 예시 |
| `ADMIN` | 관리자. 회원가입으로는 만들 수 없음 | 회원가입 에러 |
| 상점주 | 값 이름이 노션에 없음 (예: `OWNER`) | **확인 필요** |

### 상태 값
| 대상 | 값 | 출처 |
| --- | --- | --- |
| 할인 `discount_offers.status` | `SCHEDULED`, `ON_SALE`, `SOLD_OUT`, `CLOSED` | 할인 API |
| 예약 `pickup_reservations.status` | `PENDING_PAYMENT`, `RESERVED`(?), `CANCELLED`, `PICKED_UP` | 예약 API (**확인 필요**: `RESERVED`와 결제 완료 상태의 관계) |
| 결제 `payments.status` | `READY`, `PAID` (+ 실패 상태?) | 결제 요청, 포인트 정책 |
| 환불 `refunds.status` | `COMPLETED` (+ 다른 상태?) | 환불 API |
| 포인트 `point_log.point_type` | `EARN`, `USE`, `RESTORE`, `REVOKE` | 포인트 내역 조회 |

### 포인트 정책 (노션 포인트 내역 조회 페이지)
별도 API 없이 payments 서비스가 내부에서 처리합니다.

| point_type | 시점 | amount |
| --- | --- | --- |
| `USE` | 결제 요청 시 포인트 사용 | 음수, 100P 단위, 잔액 이하 |
| `EARN` | 결제 승인(`READY` → `PAID`) 직후 | 결제 금액 × 1% (소수점 버림) |
| `RESTORE` | 환불 시 사용 포인트 복구 | `total_price − payments.amount` |
| `REVOKE` | 환불 시 적립 포인트 회수 | 결제 금액 × 1%, 잔액 한도 |

### 에러 응답 (제안)
노션 auth 페이지는 아래 형식을 쓰고, 나머지 페이지는 상태 코드와 메시지만 적혀 있습니다. 전역 예외 핸들러로 모든 API를 이 형식으로 맞추는 것을 제안합니다.

```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "이메일 또는 비밀번호가 올바르지 않습니다." }
```

노션에 나온 `error_code`: `VALIDATION_ERROR`, `INVALID_CREDENTIALS`, `EMAIL_DUPLICATED`, `UNAUTHORIZED`, `TOKEN_REVOKED`

### 상태 코드
| 코드 | 쓰임 |
| --- | --- |
| 200 / 201 / 204 | 조회·변경 성공 / 생성 성공 / 본문 없는 성공(로그아웃) |
| 400 | 도메인 규칙 위반 (도메인의 `ValueError`) |
| 401 | 토큰 없음, 만료, 로그아웃된 토큰, 로그인 실패 |
| 403 | 역할이나 소유권 없음 (`PermissionError`) |
| 404 | 대상 없음 (`LookupError`) |
| 409 | 중복이나 상태 충돌 (노션 예약·결제·회원가입 페이지에서 사용) |
| 422 | 요청 형식 오류 (FastAPI·Pydantic 기본) |

### 페이지네이션
노션 페이지마다 형식이 다릅니다. **확인 필요**

| 페이지 | 시작 값 | 응답 필드 |
| --- | --- | --- |
| 포인트 내역 | `page=0` | `page`, `size`, `total_elements` |
| 상품·할인 목록 | `page=1` | `items`, `page`, `size`, `total` |
| 내 예약 목록 | 없음 | `reservations` |

### 날짜·시간
ISO 8601에 시간대를 붙입니다. 예: `2026-10-29T18:00:00+09:00`

## 팀 확인이 필요한 항목
노션 페이지를 옮기면서 찾은 빈칸과 불일치입니다.

### 공통
1. **Method와 URI 확정:** 위 목록의 제안 값으로 갈지 정해야 합니다.
2. **에러 형식 통일:** auth만 `success`, `error_code`, `message` 형식입니다.
3. **형식 오류 코드:** auth는 필수값 누락을 `400 VALIDATION_ERROR`로, 다른 페이지는 `422`로 적었습니다. FastAPI 기본은 422입니다.
4. **규칙 위반 코드:** 상점·카탈로그는 `400`, 예약·결제는 `409 Conflict`를 씁니다. 교안은 `ValueError → 400` 변환을 요구합니다.
5. **페이지네이션 형식:** 시작 값(0/1)과 응답 필드 이름(`total`/`total_elements`)을 하나로 정해야 합니다. 교안은 목록 API의 페이지네이션을 요구하므로 내 예약 목록에도 필요합니다.

### auth
6. **로그인:** 노션 명세(JSON, `email`)를 따릅니다. 응답 필드가 비어 있어 `access_token`, `token_type`으로 적었습니다. Swagger는 Authorize에 토큰을 붙여 넣어 사용합니다.
7. **상점주 역할 값**과 **상점주 승인 상태 저장 위치:** 상점 API에 "승인 대기 중인 상점주 계정(403)"이 있는데 `users` 테이블에 승인 상태 컬럼이 없습니다.
8. **상점주 가입 정보:** 상점명은 "가입 시 등록한 상호(`name`)"를 쓴다고 되어 있습니다. 회원가입 요청에 `business_number`가 없습니다.

### stores
9. **`approval_at`:** 노션은 "개설 시각"(datetime)으로 쓰는데 ERD는 `VARCHAR(20)`입니다. `db-schema` 스킬은 `TIMESTAMPTZ`로 맞췄습니다.
10. **재개점:** "폐점한 상점은 재개점할 수 있다"고 되어 있지만 API가 없습니다.
11. **관리자 승인 API 없음:** 상점주 계정을 승인하는 API가 없습니다.

### catalog
12. **상품 검색 응답:** 상품 필드 없이 `store_name`, `distance`, `unit`, `has_active_offer`만 있습니다.
13. **상품 상세 응답:** 단일 상품인데 `items` 배열로 감싸져 있습니다. 이 문서는 단일 객체로 적었습니다.
14. **할인 상세 `notice`, `cancel_policy`:** 저장할 컬럼이 없습니다. 어떤 규칙으로 계산할지 정해야 합니다.
15. **사유 저장 위치:** 재고 수동 조정 `reason`을 저장할 컬럼이 없습니다.
16. **재고 수동 조정 에러:** 403 메시지가 "이력만 조회할 수 있습니다"로 복사 오류로 보입니다. 남은 재고보다 많이 빼는 경우(400)가 없습니다.
17. **재고 이력 조회 API:** 403 메시지로 보아 계획이 있었던 것 같지만 페이지가 없습니다.

### reservations
18. **`pickup_code` 발급 시점:** 예약 생성 응답에 없고 픽업 완료에서 처음 나옵니다. 결제 완료 시 발급하는지 정해야 합니다.
19. **상점주용 예약 목록 없음:** 픽업 완료에 `reservation_id`가 필요한데 상점주가 자기 매장 예약을 볼 API가 없습니다.
20. **예약 취소와 환불의 관계:** 예약 취소가 환불을 자동으로 만드는지, 고객이 환불 요청을 따로 하는지 정해야 합니다.

### payments
21. **포인트 사용 입력:** 포인트 정책에는 "결제 요청 시 포인트 사용"이 있는데 결제 요청 본문에 포인트 필드가 없습니다.
22. **환불 응답 필드 설명:** 결제 조회 설명이 복사돼 있습니다(`id: 결제 ID` 등). 이 문서는 실제 응답 예시에 맞게 고쳐 적었습니다.
23. **위약금 규칙:** "취소 정책에 따라 위약금 계산"의 구체적 규칙이 없습니다.
