---
name: api-client
description: 마감 직전 프론트엔드가 FastAPI 백엔드를 호출하는 규칙입니다. shared/api의 fetch 클라이언트(기본 주소 VITE_API_BASE_URL, /v1 경로, Authorization Bearer 헤더, AbortSignal), 공통 에러 응답({success, error_code, message})을 ApiError로 바꾸는 방법, 401·네트워크 오류 처리, slice infrastructure의 API 함수와 DTO → domain 변환, 백엔드 명세(../docs/reference)와 화면별 엔드포인트(../docs/design-system/api-map.md) 대조 방법을 다룹니다. API 호출 코드를 쓰거나 고칠 때, 응답 필드나 에러 코드를 확인할 때, 백엔드 명세 변경을 반영할 때 사용합니다.
---

# API 클라이언트

규칙 ID(F8, F9, F11, F14)는 `frontend-invariants`가 정본입니다.

## 1. 연결 구조

| 환경 | `VITE_API_BASE_URL` | 요청 경로 | 전달 |
| --- | --- | --- | --- |
| 개발(`npm run dev`) | 비움 | `/v1/...` | Vite proxy → `http://localhost:8001/v1/...` |
| 배포 빌드 | API 서버 주소 | `${VITE_API_BASE_URL}/v1/...` | 직접 호출 (백엔드 CORS 필요) |

설정 방법은 `frontend/README.md` "백엔드 API 연결" 절이 정본입니다. `VITE_API_BASE_URL`은 `shared/config/env.ts` 한 곳에서만 읽습니다.

## 2. shared/api 클라이언트 (F8)

`fetch`를 호출하는 곳은 이 폴더뿐입니다.

```ts
// shared/config/env.ts
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? ''

// shared/api/client.ts
import { API_BASE_URL } from '@/shared/config/env'
import { ApiError, toApiError } from './error'

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean }

let getToken: () => string | null = () => null
export function setTokenProvider(fn: () => string | null) { getToken = fn }

export async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const token = opts.auth === false ? null : getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res: Response
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    })
  } catch (e) {
    if (opts.signal?.aborted) throw e
    throw new ApiError(0, 'NETWORK_ERROR', '네트워크에 연결할 수 없습니다.')
  }
  if (!res.ok) throw await toApiError(res)
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const apiGet = <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal })
export const apiPost = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body, signal })
```
- `path`는 항상 `/v1/...`로 시작합니다.
- 토큰은 `setTokenProvider`로 주입합니다. 토큰을 **어디에 보관할지**(메모리 / `localStorage` / `sessionStorage`)는 아직 정하지 않았습니다. 정해지면 이 절에 적고, 그 전에는 임의로 정하지 않고 보고서에 "미정"으로 적습니다.
- `NETWORK_ERROR`는 프론트 전용 코드입니다. 문구는 `../docs/design-system/content.md`에 맞는 것이 있으면 그것으로 바꿉니다.

## 3. 에러 (F11)

백엔드 공통 에러 형식은 `{ "success": false, "error_code": "...", "message": "..." }`입니다(`../docs/reference/README.md`).

```ts
// shared/api/error.ts
export class ApiError extends Error {
  constructor(public status: number, public errorCode: string, message: string) { super(message) }
}

export async function toApiError(res: Response): Promise<ApiError> {
  const body = await res.json().catch(() => null)
  if (body && typeof body.error_code === 'string')
    return new ApiError(res.status, body.error_code, String(body.message ?? ''))
  return new ApiError(res.status, 'UNKNOWN', res.statusText)
}
```
- 화면 분기는 `errorCode`로 합니다. `message` 문자열 비교로 분기하지 않습니다.
- 명세상 auth 외 모듈은 에러 형식이 아직 통일되지 않았을 수 있습니다(`../docs/reference/README.md` "확인 필요"). 형식이 다르면 `UNKNOWN`으로 떨어지므로, 발견하면 보고서에 적습니다.
- `401 UNAUTHORIZED`·`TOKEN_REVOKED`는 공통으로 처리합니다(토큰 제거 → 로그인 화면 A1). 처리 위치는 `app/providers`의 인증 Context입니다.
- `429 ACCOUNT_LOCKED`는 `Retry-After` 헤더가 있으니 필요한 화면에서 읽습니다.

## 4. slice infrastructure (F9)

```ts
// entities/offer/infrastructure/offerApi.ts
import { apiGet } from '@/shared/api/client'
import type { Offer } from '../domain/offer'

type OfferDto = { id: string; price: number; discount_price: number; closes_at: string; stock: number }

export function toOffer(d: OfferDto): Offer {
  return { id: d.id, price: d.price, discountPrice: d.discount_price, closesAt: new Date(d.closes_at), stock: d.stock }
}

export async function fetchOffer(id: string, signal?: AbortSignal): Promise<Offer> {
  return toOffer(await apiGet<OfferDto>(`/v1/offers/${encodeURIComponent(id)}`, signal))
}
```
- DTO 타입은 infrastructure 파일 안에만 두고 공개 API로 내보내지 않습니다.
- DTO 필드명은 명세의 snake_case 그대로, domain은 camelCase로 바꿉니다.
- 시각 문자열은 `Date`로, 금액은 `number`(원 단위 정수)로 바꿉니다.
- 위 필드는 예시입니다. 실제 필드는 명세를 확인합니다(§5).

## 5. 명세 대조 (F14)

API 함수를 쓰기 전에 아래를 확인합니다.
1. `../docs/design-system/api-map.md`에서 화면 ID로 엔드포인트를 찾습니다.
2. `../docs/reference/<모듈>.md`에서 URI, 요청 필드, 응답 필드, null 가능 여부, 상태 코드, `error_code`를 확인합니다.
3. 필요하면 백엔드 코드(`../backend/src/<모듈>/presentation/schemas.py`, `router.py`)로 실제 응답을 확인합니다(읽기만 합니다).
4. 명세와 백엔드 코드가 다르거나, 명세에 "확인 필요"가 있으면 임의로 고르지 않고 양쪽 위치를 보고서에 적습니다.

| 백엔드 모듈 | 명세 | 관련 화면 |
| --- | --- | --- |
| auth | `../docs/reference/auth.md` | A1~A3, C6~C11, M3(회원 상세) |
| stores | `../docs/reference/stores.md` | O0, O7 |
| catalog | `../docs/reference/catalog.md` | C1, C1a, C2, O2~O6, O9~O12 |
| reservations | `../docs/reference/reservations.md` | C2(예약 생성), C3a, C5, C5a, C5b, O1 |
| payments | `../docs/reference/payments.md` | C3, C4 |
| admin | `../docs/reference/admin.md` | M1~M5 |

`/stores/{id}/products`·`/stores/{id}/offers`는 경로가 `stores`로 시작하지만 catalog 모듈, `/stores/{id}/reservations`는 reservations 모듈입니다(`../backend/src/<모듈>/presentation/router.py`).

화면 ↔ 모듈 대응은 `api-map.md`가 정본입니다. 위 표와 다르면 `api-map.md`를 따르고 이 표를 고칩니다.
