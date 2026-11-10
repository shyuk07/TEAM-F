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
import { readToken } from './tokenStorage'

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean }

export async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const token = opts.auth === false ? null : readToken()
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
- 로그인·회원가입처럼 토큰을 붙이면 안 되는 요청은 `auth: false`로 보냅니다.
- `NETWORK_ERROR`는 프론트 전용 코드입니다. 문구는 `../docs/design-system/content.md`에 맞는 것이 있으면 그것으로 바꿉니다.

## 2.1 토큰 보관 (F17)

**결정:** 로그인 응답의 `access_token`을 `localStorage`에 저장하고 `Authorization: Bearer` 헤더로 보냅니다. 백엔드 현재 방식(`backend/src/auth/presentation/dependencies.py`의 `HTTPBearer`)을 그대로 씁니다. 쿠키 방식으로 바꾸면 이 절을 고칩니다.

토큰을 읽고 쓰는 곳은 `shared/api/tokenStorage.ts` 하나뿐입니다.

```ts
// shared/api/tokenStorage.ts
const KEY = 'lastcall.accessToken'

// 사생활 보호 모드·저장소 차단 환경에서는 localStorage 접근이 예외를 던진다. 그때는 로그인 상태를 유지하지 않는다.
export function readToken(): string | null {
  try { return localStorage.getItem(KEY) } catch { return null }
}
export function saveToken(token: string): void {
  try { localStorage.setItem(KEY, token) } catch { /* 저장 불가: 이번 탭에서만 로그인 */ }
}
export function clearToken(): void {
  try { localStorage.removeItem(KEY) } catch { /* 무시 */ }
}
// 다른 탭에서 로그인·로그아웃하면 이 탭도 따라가게 한다.
export function onTokenChange(cb: (token: string | null) => void): () => void {
  const handler = (e: StorageEvent) => { if (e.key === KEY || e.key === null) cb(readToken()) }
  window.addEventListener('storage', handler)
  return () => window.removeEventListener('storage', handler)
}
```

`tokenStorage.ts` 함수를 직접 부르는 곳은 두 곳뿐입니다. `shared/api/client.ts`(`readToken`으로 헤더 붙이기)와 `entities/session/infrastructure/localSessionStore.ts`(application 포트 `SessionStore`의 구현체)입니다. 나머지 코드는 `SessionStore` 포트를 `useDep(SessionStoreToken)`으로 받아 씁니다(`layer-architecture` §6.3, §6.5). 쿠키 방식으로 바꾸면 구현체와 `entities/session/wiring.ts`만 고치면 됩니다.

| 시점 | 동작 | 위치 |
| --- | --- | --- |
| 로그인 성공 (`POST /v1/auth/login`) | `session.save(access_token)` 후 응답의 `status`(APPROVED·PENDING 등)로 화면 분기 | `features/login`의 유스케이스 |
| 앱 시작 | `session.hasSession()`이면 `GET /v1/users/me`로 사용자 확인. 401이면 `session.clear()` | `app/providers`의 인증 Context |
| 로그아웃 (`POST /v1/auth/logout`) | 서버 응답과 관계없이 `session.clear()` (서버가 토큰을 블랙리스트에 올림) | `features/logout`의 유스케이스 |
| `401 UNAUTHORIZED`·`TOKEN_REVOKED` | `session.clear()` → 로그인 화면(A1) | 인증 Context (§3) |
| 비밀번호 변경·재설정 성공 | 이전 토큰은 서버에서 무효가 되므로 `session.clear()` 후 다시 로그인 | 해당 feature의 유스케이스 |
| 다른 탭 변경 | `onTokenChange`로 인증 Context 상태 갱신 (포트에 `subscribe`를 두고 구현체가 `onTokenChange`를 감쌈) | 인증 Context |

### 보안 메모: localStorage의 약점과 대책

`localStorage`는 페이지의 모든 JavaScript가 읽을 수 있습니다. 그래서 **XSS(악성 스크립트 삽입)가 한 번이라도 생기면 토큰이 밖으로 유출**되고, 공격자는 만료 전까지 다른 기기에서 그 토큰을 쓸 수 있습니다. HttpOnly 쿠키는 JS가 읽지 못해 유출은 막지만, XSS가 있으면 사용자의 브라우저 안에서 요청을 대신 보내는 것까지는 막지 못합니다. 즉 **두 방식 모두 핵심 방어는 XSS를 만들지 않는 것**이고, 차이는 유출된 토큰을 밖에서 재사용할 수 있느냐입니다.

이 프로젝트는 아래 대책으로 위험을 줄입니다.

| 대책 | 내용 | 확인 |
| --- | --- | --- |
| XSS를 만들지 않는다 | `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function` 금지. 사용자 입력(상품명·매장명·사유)은 JSX 텍스트로만 출력. 사용자 입력으로 만든 `href`·`src`는 `http(s):`만 허용 | `fe-code-review` 보안 관점 |
| 토큰을 다른 곳에 두지 않는다 | 토큰을 `console.log`, URL 쿼리, 에러 리포트, React 상태·Context 값에 넣지 않는다. 필요할 때마다 `readToken()`으로 읽는다 | F17, 리뷰 |
| 외부 스크립트를 줄인다 | 분석·광고·채팅 위젯 등 서드파티 스크립트를 넣지 않는다. 새 의존성은 사용자 승인 후 추가하고 `npm audit` 결과를 보고한다 | F15, `pre-merge-check` |
| 유효 기간을 짧게 둔다 | 백엔드 `ACCESS_TOKEN_EXPIRE_MINUTES` 기본 30분(`backend/src/auth/infrastructure/settings.py:17`). 늘리지 않는다 | 백엔드 설정 |
| 로그아웃 시 서버 무효화 | 서버가 `jti`를 블랙리스트에 올리므로 로그아웃한 토큰은 다시 쓸 수 없다 | 백엔드 동작 |
| CSP 헤더 (권장, 미적용) | Nginx에서 `Content-Security-Policy`로 허용한 출처의 스크립트만 실행 | 배포 설정 결정 필요 |

관리자 화면(M1~M5)처럼 권한이 큰 토큰도 같은 방식으로 보관합니다. 위험을 더 줄여야 하면 HttpOnly 쿠키 방식(백엔드 변경 필요)으로 옮기는 것을 사용자에게 제안합니다.

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
- `401 UNAUTHORIZED`·`TOKEN_REVOKED`는 공통으로 처리합니다(`session.clear()` → 로그인 화면 A1, §2.1). 처리 위치는 `app/providers`의 인증 Context입니다.
- `429 ACCOUNT_LOCKED`는 `Retry-After` 헤더가 있으니 필요한 화면에서 읽습니다.

## 4. slice infrastructure (F9, F18)

서버를 부르는 코드는 domain 포트(`<개체>Repository`)의 구현체로 만듭니다. 예시 코드는 `layer-architecture` §6.5(`HttpOfferRepository`)가 정본입니다.

- 구현체는 `shared/api`의 `apiGet`·`apiPost`를 쓰고, `fetch`를 직접 부르지 않습니다(F8).
- DTO 타입과 DTO → domain 변환 함수는 구현체 파일 안에만 두고 공개 API로 내보내지 않습니다.
- DTO 필드명은 명세의 snake_case 그대로, domain은 camelCase로 바꿉니다.
- 시각 문자열은 `Date`로, 금액은 `number`(원 단위 정수)로 바꿉니다.
- §6.5 예시의 필드는 예시입니다. 실제 필드는 명세를 확인합니다(§5).

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
