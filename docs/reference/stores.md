# stores API

상점 개설과 폐점. 모듈: `src/stores`
테이블: `stores` (상점주 정보는 `users`)

[← 전체 목록](README.md)

---

## 1. 상점 개설
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/stores` | 상점주 (관리자 승인 완료) | 201 Created |

관리자 승인을 받은 상점주가 상점을 개설한다.

- 상점명은 가입 시 등록한 상호(`name`)로 자동 설정되며 입력받지 않는다.
- 주소는 서버에서 좌표로 변환하며, 변환에 실패하면 개설할 수 없다.
- 상점주 1인당 하나의 상점만 개설할 수 있다.
- 개설 후 상점명과 주소는 변경할 수 없다.
- 개설 시각이 `approval_at`에 저장된다.

**헤더**
- `Content-Type: application/json`
- `Authorization: Bearer {access_token}`

**요청 본문**
| 필드 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `pickup_address` | string | O | 픽업 주소 (최대 500자) |

```json
{
  "pickup_address": "서울특별시 강남구 테헤란로 123"
}
```

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 상점 ID |
| `owner_id` | UUID | 상점주 ID |
| `name` | string | 상점명 (상점주 상호) |
| `pickup_address` | string | 픽업 주소 |
| `latitude` | double | 위도 (서버 변환) |
| `longitude` | double | 경도 (서버 변환) |
| `created_at` | datetime | 생성 시각 |
| `approval_at` | datetime | 개설 시각 |
| `closed_at` | datetime \| null | 폐점 시각. 개설 시 `null` |

**에러**
| HTTP | error_code | 메시지 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | 주소를 입력해 주세요. (빈 값·공백만) |
| 400 | `ADDRESS_NOT_FOUND` | 주소를 찾을 수 없습니다. (지오코딩 결과 0건) |
| 400 | `STORE_ALREADY_EXISTS` | 이미 개설된 상점이 있습니다. |
| 400 | `STORE_DUPLICATED` | 동일한 상점명과 주소의 상점이 이미 존재합니다. |
| 401 | `UNAUTHORIZED` | 로그인이 필요합니다. (명세 문구 "인증이 필요합니다."와 다름, 공용 auth 문구 유지) |
| 403 | `FORBIDDEN` | 승인 대기 중인 상점주 계정입니다. / 승인이 거부된 상점주 계정입니다. / 정지된 계정입니다. |
| 403 | `FORBIDDEN` | 접근 권한이 없습니다. (상점주가 아님. 명세 문구 "상점주 권한이 필요합니다."와 다름, 공용 auth 문구 유지) |
| 503 | `GEOCODING_UNAVAILABLE` | 주소 변환 서비스를 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해 주세요. (명세에 없음, 설계 D29) |

- **검사 순서:** 주소 → 상점명 → 이미 개설 → 동일 상점명·주소 → 지오코딩. 앞 검사가 실패하면 지오코딩을 호출하지 않는다(설계 D40). 명세 표와 달리 "주소를 찾을 수 없습니다"가 "이미 개설"보다 뒤에 온다(둘 다 400).
- **동일 상점명·주소:** 유니코드 NFC 정규화, 앞뒤·연속 공백 정리 후 정확히 일치하면 중복이다(대소문자 구분). 폐점·정지 상점도 포함한다. DB 제약 `uq_stores_name_address`가 동시 요청에서도 보장한다(설계 D32·D33). 응답의 `pickup_address`는 정규화된 입력값이다.
- **지오코딩:** 카카오 로컬 API 주소 검색(`GET https://dapi.kakao.com/v2/local/search/address.json`, 헤더 `Authorization: KakaoAK {REST API 키}`, `query`·`size=1`). 응답의 첫 번째 결과(`x`=경도, `y`=위도)를 쓴다. 타임아웃 5초, 재시도 없음. 결과 0건이면 400 `ADDRESS_NOT_FOUND`이며, 주소가 아닌 키워드형 입력(가게 이름 등)도 0건이 될 수 있다. 네트워크 오류·타임아웃·카카오 오류 응답(401 키 오류, 429 한도 초과, 5xx 등)·키 미설정은 503이다. 서버는 키 없이도 시작되며(경고 로그), 이때 상점 개설만 503이다(설계 D28·D29, D48~D53).
- **설정 (`.env`):** `KAKAO_REST_API_KEY` (필수, Kakao Developers 앱의 REST API 키), `KAKAO_GEOCODE_URL`, `KAKAO_TIMEOUT_SECONDS` (선택). 예시는 `.env.example`.

> **확인 필요**
> - 실제 키로 한 번 호출해 `size=1` 파라미터와 오류 상태 코드가 가정과 같은지 확인한다(설계 §16).
> - 이 기능 이전에 개설된 상점은 좌표가 `null`이다(백필 없음, 설계 C20).
> - ~~주소 → 좌표 변환 방법~~ (해결됨: 카카오 로컬 API, 2026-11-06 네이버에서 교체)
> - ~~상점주 승인 상태를 어디에 저장할지~~ (해결됨: `users.status`, 승인은 [admin.md 1번](admin.md#1-상점주-계정-승인))
> - "1인 1상점" 규칙에 맞춰 `db-schema` 스킬의 `schema.sql`에 `stores.owner_id UNIQUE`를 넣었습니다

---

## 2. 상점 폐점
| Method | URI (제안) | 권한 | 성공 |
| --- | --- | --- | --- |
| POST | `/v1/stores/{store_id}/close` | 상점주 (본인 상점) | 200 OK |

상점주가 본인 상점을 폐점한다.

- 진행 중이거나 예정된 할인 판매, 또는 픽업 대기 중인 예약이 있으면 폐점할 수 없다.
- 폐점 시 `closed_at`이 기록된다.
- 폐점된 상점에서는 상품 및 할인 판매를 등록할 수 없다.

**헤더**
- `Authorization: Bearer {access_token}`

**경로 매개변수**
| 이름 | 타입 | 설명 |
| --- | --- | --- |
| `store_id` | UUID | 상점 ID |

**요청 본문:** 없음

**응답**
| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `id` | UUID | 상점 ID |
| `name` | string | 상점명 |
| `closed_at` | datetime | 폐점 시각 |

**응답 예시**
```json
{
  "id": "1a2b3c4d-...",
  "name": "마감베이커리",
  "closed_at": "2026-11-05T10:00:00Z"
}
```

- "진행 중이거나 예정된 할인"은 판매 중·판매 예정·품절, 그리고 **관리자가 정지한 할인**을 포함한다(`is_active`이고 `sales_end`가 지나지 않은 할인). 판매 중단(`deactivate`)했거나 판매 기간이 끝난 할인은 막지 않는다.
- 관리자가 정지한 할인은 상점주가 판매 중단할 수 없으므로, 그 할인의 `sales_end`가 지나거나 관리자가 [강제 폐점](admin.md#6-상점-강제-폐점)할 때까지 상점주는 폐점할 수 없다. 관리자 정지를 폐점으로 우회하지 못하게 하려는 의도된 동작이다(설계 D25).

**에러** (인증 → 404 → 소유 → 아래 순서로 먼저 검사)
| HTTP | error_code | 메시지 |
| --- | --- | --- |
| 400 | `VALIDATION_ERROR` | `store_id`가 UUID 형식이 아님 |
| 400 | `STORE_ALREADY_CLOSED` | 이미 폐점된 상점입니다. |
| 400 | `STORE_SUSPENDED` | 관리자에 의해 정지된 상점입니다. (명세에 없음, 관리자 정지 기능으로 추가) |
| 400 | `STORE_HAS_OPEN_OFFERS` | 진행 중이거나 예정된 할인 판매가 있어 폐점할 수 없습니다. |
| 400 | `STORE_HAS_RESERVED_RESERVATIONS` | 픽업 대기 중인 예약이 있어 폐점할 수 없습니다. (현재 미연계, 아래 참고) |
| 401 | `UNAUTHORIZED` | 로그인이 필요합니다. |
| 403 | `FORBIDDEN` | 승인 대기 중인 상점주 계정입니다. / 승인이 거부된 상점주 계정입니다. |
| 403 | `FORBIDDEN` | 정지된 계정입니다. |
| 403 | `FORBIDDEN` | 접근 권한이 없습니다. (상점주가 아님) |
| 403 | `FORBIDDEN` | 본인 상점만 폐점할 수 있습니다. |
| 404 | `NOT_FOUND` | 상점을 찾을 수 없습니다. |

> **미연계 (reservations):** 픽업 대기 예약 검사는 현재 자리표시자(`NoPickupPendingReservations`)라 항상 통과한다. reservations 연동 후 `src/container.py`의 바인딩만 바꾼다.
>
> **알려진 경합 (설계 D22, 후속):** 할인 등록은 상점 행을 잠그지 않으므로, 폐점 확인과 커밋 사이에 같은 상점주가 할인을 등록하면 폐점된 상점에 할인이 남을 수 있다.
