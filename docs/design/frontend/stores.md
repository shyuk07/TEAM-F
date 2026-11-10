# stores 영역 설계안 (O0 상점 개설 · O7 상점 폐점 확인) + 이번 차수 공용 기반

- 대상 slice: `features/stores`, `entities/store`, `pages/owner-start`(O0), `pages/store-close`(O7), `app`(가드·라우트·연결), 공용 기반(`shared/lib`·`shared/api`·`shared/ui`), `widgets/owner-nav`(로그아웃 링크 1개 추가)
- 대응 화면: 상점주 O0, O7. O4(폐점 링크 위치)는 products 차수에서 구현하고 이번에는 자리 page에 링크만 둔다(D-12).
- 상태: 설계안 2차. 사용자 확정(Q-1~Q-8 전부): Q-1 상점명 칸(D-20), Q-2·Q-3 오류 문구(D-10), Q-4 안내 문구(D-6), Q-5 O7 경로·링크(D-12), Q-7 완전 일치(D-8), Q-6 정지 전제(D-22). Q-8 해소(§0).남은 임시 결정: D-7·D-9(구현 기법, 구현 때 확정), D-11·N-7(임시 문구, content.md 확정 때), D-13(배치), D-14~D-19(구현 방식), D-21(계정 name null 개설 불가 처리 — 설계자 임시).
- 정본: `../../design-system/screens.md` O0(317~333줄)·O4(391~409줄)·O7(437~450줄), `layout.md` 49~70줄, `api-map.md` 27·34줄, `states.md` 상점·회원, `content.md`, `open-issues.md` C8, `wireframe.html` O0(560~580줄)·O7(731~745줄), `../../reference/stores.md`, 기존 설계안 `app-shell.md`, `auth.md`.

## 0. 백엔드 실재 확인 (`frontend-orchestration.md` §6)

| 항목 | 확인 위치 | 결과 |
| --- | --- | --- |
| `POST /v1/stores` 201, 본문 `pickup_address`(최대 500자), 승인된 상점주만 | `backend/src/stores/presentation/router.py:23~31`, `schemas.py:7~9`, `auth/presentation/dependencies.py:92~111` | 명세(`reference/stores.md` §1)와 같다. 응답 `StoreResponse`(`schemas.py:28~38`)에는 `status`가 없고 `latitude`·`longitude`가 null 불가 |
| `GET /v1/stores/me` 200, 정지 상점주 허용(`SuspendedAllowedOwnerUser`), 상점이 없으면 404 | `router.py:36~43`, `dependencies.py:112~114`, `stores/application/query_service.py:25~30`, `stores/domain/exceptions.py:1~5` | 명세 §3과 같다. 승인 대기·거부 상점주도 이 가드를 통과해 404를 받는다(역할만 검사). 응답 `MyStoreResponse`(`schemas.py:41~56`)에 `status`가 있고 좌표·`approval_at`·`closed_at`이 null 가능 |
| `POST /v1/stores/{id}/close` 200, 응답 `{id, name, closed_at}` | `router.py:46~54`, `schemas.py:12~17`, `stores/application/service.py:30~41` | 명세 §2와 같다. 가드는 `ApprovedOwnerUser`라 **정지된 계정은 403**이다 |
| `error_code`: `STORE_ALREADY_EXISTS`, `ADDRESS_NOT_FOUND`, `STORE_DUPLICATED`, `GEOCODING_UNAVAILABLE`(503), `STORE_ALREADY_CLOSED`, `STORE_SUSPENDED`, `STORE_HAS_OPEN_OFFERS`, `STORE_HAS_RESERVED_RESERVATIONS` | `stores/domain/exceptions.py:15~110` | 명세와 이름이 같다. 공통 핸들러 변환 확인됨(Q-8 해소): `error_handlers.py:71`이 403 → `FORBIDDEN`, `error_handlers.py:75`가 404 → `NOT_FOUND`. 프론트 가정(404 && NOT_FOUND → 상점 없음, 403 ·FORBIDDEN· 표시)과 일치 |
| `STORE_HAS_RESERVED_RESERVATIONS` 메시지 | 코드 `exceptions.py:107~109`: "처리되지 않은 예약이 있는 상점은 폐점할 수 없습니다." / 명세 `reference/stores.md` §2 에러 표: "픽업 대기 중인 예약이 있어 폐점할 수 없습니다." | **다르다**(C-4). 이 검사는 현재 자리표시자라 항상 통과한다(`stores.md` §2 "미연계") |
| `TOKEN_REVOKED`는 401 | `auth/domain/exceptions.py:33~34`, `reference/auth.md` | 401 처리 대상 |
| 관리자 정지된 상점 | `stores/domain/store.py:153~158` | `status`는 폐점 > 정지 > 영업 중 순으로 계산 |

## 1. slice 목록과 계층

| 계층 | slice | 대응 화면 | 안에 두는 계층 |
| --- | --- | --- | --- |
| `shared` | `lib`(`useAsync`, `errorInfo`, `routes` 추가), `api`(401 알림 추가), `ui`(§2.3) | 전 화면 | (4계층 없음, F3) |
| `entities` | `store` | O0·O7 + products(O4·O6·O11·O12) | domain, application, presentation (infrastructure 없음, F18) |
| `features` | `stores` | O0, O7 | domain, application, infrastructure, presentation, `wiring.ts` |
| `widgets` | `owner-nav` (기존, 변경) | O0 | presentation (`OwnerLogoutLink` 추가) |
| `pages` | `owner-start` | O0 | presentation |
| `pages` | `store-close` | O7 | presentation |
| `app` | `layouts/OwnerLayout`, `layouts/OwnerStoreGate`, `providers/AuthFailureBridge`, `router/routes.tsx`, `container.ts`, `App.tsx` | | (4계층 없음) |

의존 방향: `pages → features(stores)·entities(store)·features(auth)·widgets`, `app → pages·features·entities`. features/stores는 features/auth를 import하지 않는다(F1). 두 영역이 만나는 곳은 `pages/owner-start`(계정 상태는 `useAuth`, 상점은 `useMyStore`)와 `app/layouts/OwnerStoreGate`뿐이다. `entities/store`는 계정 상태 타입을 `features/auth`에서 가져오지 않고 자기 안의 문자열 합집합(`OwnerAccountStatus`)으로 받는다(구조 호환).

### 1.1 영역 사이 연결 (F1) — 로그인 후 이동과 상점 ID 전달

| 문제 | 해결 |
| --- | --- |
| auth의 로그인 후 이동이 상점 유무를 알아야 한다(`redirect.ts:40` TODO) | `resolvePostLoginPath`는 **그대로** 상점주를 O1(`/owner/today`) 또는 `from`으로 보낸다. 도착 뒤 `app/layouts/OwnerStoreGate`가 `GET /v1/stores/me` 결과로 O0·O1을 정한다(D-7). auth는 stores를 모른다. `layout.md` 70줄 "상점주는 `GET /stores/me` 결과로 O0 또는 O1"과 결과가 같다(C-6) |
| products가 상점 ID·상태를 쓴다 | `entities/store`가 `useMyStore()`·`useOwnerStore()`와 포트 `StoreRepository`·토큰을 공개한다. products는 `useOwnerStore().id`로 읽는다. 가드가 상점 있음을 보장한 하위 라우트에서만 `useOwnerStore`를 부른다 |
| 상점 조회를 화면마다 반복하지 않는다 | `MyStoreProvider`가 `OwnerStoreGate` 안에서 **한 번** 불러 내려 준다(`react-implementation` §2 마지막 항목) |

## 2. 공용 기반

### 2.1 서버 데이터 조회 공용 훅 — `shared/lib/useAsync.ts`

`react-implementation` §2의 코드를 **그대로** 만든다(시그니처 `useAsync<T>(load: (signal: AbortSignal) => Promise<T>, key: string)`, 반환 `{status:'loading'|'success'|'error', data, error, reload}`, `reload`는 `useCallback`으로 안정). 이 설계안은 그 스킬과 다르게 바꾸지 않는다. 훅은 정리된 요청의 결과로 상태를 바꾸지 않는다(F10).

`shared/lib/errorInfo.ts`(신규): `readErrorInfo(e: unknown): {status:number; errorCode:string; message:string}`. `features/auth/application/errorInfo.ts`와 같은 동작이다. application은 `shared/api`를 import할 수 없어(F5) 구조로 읽는다. auth를 이 파일로 바꾸는 것은 제안만 한다(C-8).

### 2.2 401·`TOKEN_REVOKED` → `SessionStoreToken.clear()` 연결 (FIXME `useAuthController.ts:12` 해결)

| 항목 | 설계 |
| --- | --- |
| 위치 | 감지: `shared/api/client.ts` + 새 `shared/api/authFailure.ts`. 연결: `app/providers/AuthFailureBridge.tsx` |
| `authFailure.ts` | `setAuthFailureHandler(handler: (() => void) \| null): void`, `notifyAuthFailure(): void`. 핸들러 칸은 하나다. 등록은 해제 함수를 돌려주는 `onAuthFailure(handler): () => void` 형태로도 쓸 수 있게 한다(구현은 둘 중 하나로 정하고 이름은 `onAuthFailure`, 반환값은 해제 함수) |
| `client.ts` 변경 | `!res.ok`일 때 `ApiError`를 만든 뒤, `opts.auth !== false` **이고** `status === 401` **이고** `errorCode`가 `UNAUTHORIZED` 또는 `TOKEN_REVOKED`이면 `notifyAuthFailure()`를 한 번 부르고 같은 `ApiError`를 그대로 던진다. 403·400·404·5xx와 `NETWORK_ERROR`는 알리지 않는다(403은 세션 만료가 아니다. 정지 계정 403은 auth D-4가 처리) |
| `AuthFailureBridge` | `const session = useDep(SessionStoreToken)` 후 `useEffect(() => onAuthFailure(() => session.clear()), [session])`. `App.tsx`에서 `AuthProvider` 안(또는 형제)에 마운트. `clear()`가 구독을 불러 `useAuthController`가 `{anonymous, 'other'}`로 바꾸고 `OwnerLayout`이 A1로 보낸다(`auth.md` §3.2). 로그아웃 중 요청이 받은 401은 컨트롤러의 `loggingOut` 보호로 `loggedOut`이 유지된다 |
| 왜 훅이 아니라 클라이언트인가 | FIXME는 "공용 훅"을 말하지만, 데이터를 바꾸는 요청(O0 개설·O7 폐점)도 401을 받는다. 클라이언트 한 곳이 모든 요청을 덮는다(D-9). `useAsync`는 에러를 그대로 돌려줄 뿐이다 |
| 토큰(F17) | 이 연결은 토큰 값을 읽지 않는다. `clear()`만 부른다 |

### 2.3 `shared/ui` 컴포넌트 (D-4 확정: 이번 화면에서 쓰이는 것만)

모두 `bundle.css` 클래스만 쓴다(F12). 파일은 `shared/ui/<이름>.tsx` 하나에 컴포넌트 하나, `shared/ui/index.ts`에서 모아 내보낸다. 업무를 모른다. 마크업은 `components/<이름>/preview.html`과 같게 한다.

| 컴포넌트 | props | 렌더 | products(O4·O6·O11·O12)에서 다시 쓰는 부분 |
| --- | --- | --- | --- |
| `Button` | `variant?: 'default'\|'primary'\|'dark'`(기본 default), `size?: 'md'\|'sm'`, `pending?: boolean`, `disabled?: boolean`, `desktopOnly?: boolean`, `type?: 'button'\|'submit'`(기본 `button`), `form?: string`, `onClick?`, `children` | `<button className="btn [pri\|dark] [sm] [dk]">`. `disabled`·`pending`이면 `aria-disabled="true"`, `onClick` 무시(submit도 막음). `pending`이면 children 대신 「처리 중…」 | O6·O11 「등록」「저장」, `sm` 행 안 버튼 |
| `Input` | `label: ReactNode`, `value: string`, `onChange(value: string)`, `type?`, `autoComplete?`, `maxLength?`, `required?`(라벨 끝에 " *"), `readOnly?`(`in ro`), `error?: string \| null`, `id?` | `<label className="lbl" htmlFor>` + `<input className="in [ro]">` + 오류가 있으면 `FieldError`. `aria-invalid`, `aria-describedby`(오류 id) | O6·O11 입력 칸. 이번에 숫자·코드·여러 줄은 만들지 않는다 |
| `FieldError` | `id?: string`, `children` | `<div className="err" role="alert" id>` | O6·O11·O12 |
| `StatusTag` | `tone: 'ok'\|'hot'\|'mute'`, `children` | `<span className="tag ok\|hot\|mute">` | O4 「영업 중」「노출」「숨김」 |
| `Notice` | `children` | `<div className="warn">` (`components/Notice` 규칙) | O11·O12 |
| `Box` | `tag?: ReactNode`, `title?: string`, `tone?: 'default'\|'done'`, `children` | `<div className="box [done]">` 안에 `tag`(왼쪽 정렬) → `<div className="t">title</div>` → children 순서 | O4 |
| `CtaBar` | `children` | `<div className="cta">` | O6·O11 |
| `AppBar` | `title: string`, `logo?: boolean`, `left?: ReactNode`, `right?: ReactNode` | `<div className="bar">` + left + `<span className={logo ? 'logo' : 't'}>` + `<span className="sp"/>` + right | O4(탭형), O6·O11·O12(하위 화면 ←). `←` 링크는 `left`로 받아 shared가 라우터를 모른다 |

- 만들지 않는 것: `ListRow`, `PhotoSlot`, `BottomSheet`(products 전용), `KeyValue`(O7의 막는 항목 표는 미룸), `Skeleton`·`EmptyState`(이번 화면에 로딩 뼈대·빈 상태 없음, D-13), `SplitLayout`(디자인 시스템에 컴포넌트 폴더가 없고 `.split.h` 클래스뿐, C-7), `Chip`·`Stepper`·`TabBar` 등.
- 텍스트 링크(`link` 클래스)는 `shared/ui`로 만들지 않는다. 쓰는 곳(`OwnerLogoutLink`) 한 곳이다.
- 기존 auth 화면(`LoginForm`, `LogoutConfirmSheet`)과 placeholders를 `shared/ui`로 바꾸는 것은 이번 범위가 아니다(C-8, 제안만).

## 3. `entities/store`

### 3.1 domain

`domain/store.ts`
```ts
export type StoreStatus = 'ACTIVE' | 'SUSPENDED' | 'CLOSED'
export type Store = {
  id: string; ownerId: string; name: string; pickupAddress: string
  latitude: number | null; longitude: number | null
  createdAt: Date; approvalAt: Date | null; closedAt: Date | null
  status: StoreStatus
}
export function storeStatusLabel(s: StoreStatus): string   // ACTIVE 영업 중 / SUSPENDED 상점 정지 / CLOSED 폐점 (states.md 상점)
export function storeStatusTone(s: StoreStatus): 'ok' | 'hot' | 'mute'   // ok / hot / mute
```

`domain/storeRepository.ts` — 포트 (domain 포트, products도 쓰므로 entities)
```ts
export interface StoreRepository {
  /** GET /v1/stores/me. 404(상점 없음)이면 null. 그 밖의 오류는 던진다 */
  findMine(signal?: AbortSignal): Promise<Store | null>
}
```

`domain/ownerEntry.ts` — 가드·O0 화면 판단 (F7, 순수 함수)
```ts
export type OwnerAccountStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | 'WITHDRAWN'
export type MyStoreLookup =
  | { status: 'loading' }
  | { status: 'none' }
  | { status: 'found'; store: Store }
  | { status: 'error'; errorCode: string; message: string }

export type OwnerEntryDecision = 'loading' | 'error' | 'allow' | 'to-start' | 'to-today'
export function decideOwnerEntry(input: { lookup: MyStoreLookup; onStartPage: boolean }): OwnerEntryDecision

export type OwnerStartView = 'pending' | 'rejected' | 'open-form' | 'closed' | 'account-blocked'
export function ownerStartView(input: { accountStatus: OwnerAccountStatus; lookup: MyStoreLookup }): OwnerStartView | null

export const MY_STORE_ERROR_FALLBACK_MESSAGE = '상점 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'  // 임시 문구(D-11)
```

`decideOwnerEntry` 표 (`onStartPage` = 현재 경로가 `/owner/start`)

| lookup | onStartPage | 결과 | 의미 |
| --- | --- | --- | --- |
| loading | 무관 | `loading` | 빈 프레임 |
| error | 무관 | `error` | 오류 + 「다시 시도」 |
| none | true | `allow` | O0이 계정 상태별 안내·개설 폼을 그림 |
| none | false | `to-start` | 상점이 없으면 어느 상점주 화면도 O0로 |
| found ACTIVE | true | `to-today` | O1로 |
| found ACTIVE | false | `allow` | |
| found SUSPENDED | true | `to-today` | O1 + 정지 안내(O1에서 `StoreSuspendedNotice`) |
| found SUSPENDED | false | `allow` | `screens.md` O0 "SUSPENDED → O1 + 정지 안내" |
| found CLOSED | true | `allow` | O0이 폐점 안내를 그림 |
| found CLOSED | false | `to-start` | 폐점한 상점의 O4·O6 등은 쓸 수 없다. **O7도 포함**(폐점 뒤 O0로) |

`ownerStartView` 표 (lookup이 `none` 또는 `found CLOSED`일 때만 값이 있고, 나머지는 `null`)

| lookup | accountStatus | 결과 |
| --- | --- | --- |
| none | PENDING | `pending` |
| none | REJECTED | `rejected` |
| none | APPROVED | `open-form` |
| none | SUSPENDED, WITHDRAWN | `account-blocked` (**현재 도달 불가**: 정지 계정은 `/users/me` 403으로 로그인할 수 없다, `auth.md` C-2·D-4. WITHDRAWN은 로그인 불가) |
| found CLOSED | 무관 | `closed` |
| loading, error, found ACTIVE·SUSPENDED | 무관 | `null` |

### 3.2 application

- `application/tokens.ts`: `StoreRepositoryToken = createToken<StoreRepository>('StoreRepository')`
- `application/useMyStoreController.ts`: `useMyStoreController(): MyStoreContextValue`. `useDep(StoreRepositoryToken)` 후 `useAsync((signal) => repo.findMine(signal), 'my-store')`. 변환: `loading → {status:'loading'}`, `success(null) → {status:'none'}`, `success(store) → {status:'found', store}`, `error → {status:'error', ...readErrorInfo(error)}`. `reload`는 `useAsync.reload`.
- `application/myStoreContext.ts`:
  ```ts
  export type MyStoreContextValue = { lookup: MyStoreLookup; reload(): void }
  export const MyStoreContext: React.Context<MyStoreContextValue | null>
  export function useMyStore(): MyStoreContextValue          // Provider 밖이면 Error('MyStoreProvider 밖에서 useMyStore를 호출했습니다.')
  export function useOwnerStore(): Store                      // lookup이 found가 아니면 Error('상점이 없는 상태에서 useOwnerStore를 호출했습니다.')
  ```
  `MyStoreContext` 객체는 훅과 같은 파일에 두고 Provider 컴포넌트는 따로 둔다(Fast Refresh, `authContext.ts` 방식).

### 3.3 presentation

- `presentation/MyStoreProvider.tsx`: `useMyStoreController()` 값을 `MyStoreContext.Provider`로 내려 준다. `OwnerStoreGate`가 `key={user.id}`로 마운트해 계정이 바뀌면 다시 불러온다.

### 3.4 공개 API (`entities/store/index.ts`)

```ts
export type { Store, StoreStatus } from './domain/store'
export { storeStatusLabel, storeStatusTone } from './domain/store'
export type { StoreRepository } from './domain/storeRepository'
export { StoreRepositoryToken } from './application/tokens'
export type { MyStoreLookup, OwnerAccountStatus, OwnerEntryDecision, OwnerStartView } from './domain/ownerEntry'
export { decideOwnerEntry, ownerStartView, MY_STORE_ERROR_FALLBACK_MESSAGE } from './domain/ownerEntry'
export type { MyStoreContextValue } from './application/myStoreContext'
export { useMyStore, useOwnerStore } from './application/myStoreContext'
export { MyStoreProvider } from './presentation/MyStoreProvider'
```
구현체·wiring은 내보내지 않는다. `StoreRepository`의 구현체 `HttpStoreRepository`는 `features/stores/infrastructure`에 두고 `features/stores/wiring.ts`가 등록한다(`fsd-structure` §1.1 "구현을 맡는 entities": `store`).

## 4. `features/stores`

### 4.1 domain

| 파일 | export | 규칙 |
| --- | --- | --- |
| `domain/openStoreInput.ts` | `PICKUP_ADDRESS_MAX_LENGTH = 500`, `canSubmitOpenStore(address: string): boolean` | 앞뒤 공백을 지운 뒤 길이 1 이상 500 이하면 true. 빈 값·공백만·501자는 false. 서버 최대 500자(`schemas.py:9`) |
| `domain/closeStoreInput.ts` | `canSubmitClose(typed: string, storeName: string): boolean` | 두 값을 `normalize('NFC')`한 뒤 `===`. 앞뒤 공백·부분 일치·대소문자 다름은 false. `storeName`이 빈 문자열이면 false (D-8) |
| `domain/storeCommands.ts` | `interface StoreCommands { open(pickupAddress: string, signal?: AbortSignal): Promise<Store>; close(storeId: string, signal?: AbortSignal): Promise<void> }` | 이 영역만 쓰는 domain 포트. `Store`는 `@/entities/store` |
| `domain/storeMessage.ts` | `GEOCODING_UNAVAILABLE_MESSAGE`, `openStoreErrorMessage(info: {status; errorCode; message}): string`, `closeStoreErrorMessage(info): string` | 아래 표 |

오류 문구 (F11: 분기는 `errorCode`, 문구 출처는 표의 근거)

| 호출 | 조건 | 표시 | 근거 |
| --- | --- | --- | --- |
| 개설 | `errorCode === 'GEOCODING_UNAVAILABLE'` (또는 `status === 503`) | 「지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.」 | `screens.md` O0 오류·경고 문구 (정본) |
| 개설 | `ADDRESS_NOT_FOUND`, `STORE_DUPLICATED`, `STORE_ALREADY_EXISTS`, `VALIDATION_ERROR`, 그 밖의 오류 | `info.message`가 비어 있지 않으면 서버 메시지, 비어 있으면 「상점을 열지 못했어요. 잠시 후 다시 시도해 주세요.」 | **정본 문구 없음 → 임시**(D-10, Q-2). `NETWORK_ERROR`의 메시지는 `shared/api/client.ts`가 이미 채운다 |
| 폐점 | `STORE_HAS_OPEN_OFFERS`, `STORE_HAS_RESERVED_RESERVATIONS`, `STORE_ALREADY_CLOSED`, `STORE_SUSPENDED`, `FORBIDDEN`, 그 밖의 오류 | `info.message`가 비어 있지 않으면 서버 메시지, 비어 있으면 「상점을 폐점하지 못했어요. 잠시 후 다시 시도해 주세요.」 | 임시(D-10, Q-3). `screens.md` O7에는 오류 코드별 문구가 없다 |

### 4.2 application

- `application/tokens.ts`: `StoreCommandsToken = createToken<StoreCommands>('StoreCommands')`
- `application/openStore.ts`: `openStore(deps: { commands: StoreCommands }, input: { pickupAddress: string }, signal?): Promise<Store>`. `canSubmitOpenStore`가 false면 `Error`를 던지고 포트를 부르지 않는다. 호출 값은 `pickupAddress.trim()`.
- `application/closeStore.ts`: `closeStore(deps: { commands: StoreCommands }, input: { store: Store; typedName: string }, signal?): Promise<void>`. `canSubmitClose(typedName, store.name)`이 false면 `Error`(포트 호출 없음). 아니면 `commands.close(store.id)`.
- `application/useOpenStore.ts`: `useOpenStore(): { submit(pickupAddress: string): Promise<void>; pending: boolean; errorMessage: string | null }`
  - `useDep(StoreCommandsToken)`, `useMyStore().reload`.
  - `submit`: 이미 `pending`이면 아무것도 하지 않음(중복 제출 방지). 시작 시 `pending=true`, `errorMessage=null`. 성공이면 `reload()` 호출(가드가 O1로 보냄). 실패면 `openStoreErrorMessage(readErrorInfo(e))`를 `errorMessage`에 넣고, `STORE_ALREADY_EXISTS`이면 추가로 `reload()`(화면이 오래돼 상점이 이미 있는 경우: 가드가 O1로 보냄). 끝나면 `pending=false`. 언마운트 뒤에는 상태를 바꾸지 않는다.
- `application/useCloseStore.ts`: `useCloseStore(store: Store): { submit(typedName: string): Promise<void>; pending; errorMessage }`. 위와 같은 구조. 성공이면 `reload()`(가드가 `CLOSED`를 보고 O0로 보냄). 실패면 `closeStoreErrorMessage`. `STORE_ALREADY_CLOSED`이면 추가로 `reload()`.

### 4.3 infrastructure

| 파일 | export | 엔드포인트·변환 |
| --- | --- | --- |
| `infrastructure/storeDto.ts` (내부) | `type StoreDto`, `toStore(dto, fallbackStatus?)` | 필드 대응: `id→id`, `owner_id→ownerId`, `name→name`, `pickup_address→pickupAddress`, `latitude→latitude`, `longitude→longitude`, `created_at→createdAt(Date)`, `approval_at→approvalAt(Date\|null)`, `closed_at→closedAt(Date\|null)`, `status→status`. `status`가 `ACTIVE`·`SUSPENDED`·`CLOSED`가 아니면 `Error('알 수 없는 status: …')`(`HttpAuthGateway`의 `pick`과 같은 방식). 개설 응답은 `status`가 없으므로 `'ACTIVE'`로 채운다(`reference/stores.md` §3 "개설 직후는 항상 ACTIVE") |
| `infrastructure/httpStoreRepository.ts` | `HttpStoreRepository implements StoreRepository` | `findMine`: `apiGet<MyStoreDto>('/v1/stores/me', signal)`. `ApiError`가 `status === 404 && errorCode === 'NOT_FOUND'`이면 `null`. 그 밖의 오류는 그대로 던진다(404라도 `errorCode`가 다르면 던진다) |
| `infrastructure/httpStoreCommands.ts` | `HttpStoreCommands implements StoreCommands` | `open`: `request<StoreOpenDto>('/v1/stores', { method: 'POST', body: { pickup_address }, signal })` → `toStore`. `close`: `request<void>(\`/v1/stores/${encodeURIComponent(id)}/close\`, { method: 'POST', signal })`. 응답 본문은 쓰지 않는다(D-14) |

DTO 타입은 infrastructure 안에만 둔다(F9).

### 4.4 presentation

화면 상태별 표시. 문구 출처는 표의 마지막 열이다.

**`StoreOpenForm`** — O0 개설 폼 (`StoreOpenForm()`; props 없음). 안에서 `useOpenStore`를 쓰고 `<>` 조각으로 `.body`와 `CtaBar` 두 형제를 돌려준다(`.app` 직속 자식이어야 하는 레이아웃, `layout.md` 골격).
| 부분 | 내용 | 출처 |
| --- | --- | --- |
| 제목 박스 | `Box title="상점 개설"` 안에 폼 | wireframe O0 |
| 「상점명」 칸 | 읽기 전용 칸(`Input readOnly`, `in ro`): label 「상점명 (가입 시 상호)」, value = 계정 이름(`user.name`, Q-1 권장 (a)을 사용자 확정). props를 `StoreOpenForm({ ownerName: string })`으로 늘리고 page가 `user.name`을 넘긴다. **이름 없는 상점주는 허용하지 않는다** — null이면 칸을 숨기는 분기를 만들지 않는다. 그래도 `name`이 null로 오면 폼 대신 「계정 정보가 올바르지 않아 상점을 열 수 없어요.」 안내 개설 불가(D-21 임시) | Q-1 확정(D-20), `schemas.py:10` name 필수, `schemas.py:25` 응답 nullable |
| 입력 | `Input label="픽업 주소" required maxLength={500} autoComplete="street-address"` | `screens.md` O0 「픽업 주소 *」 |
| 오류 | `Input error={errorMessage}`. 제출 중 아님·오류 없으면 없음 | §4.1 표 |
| 버튼(본문) | `Button variant="primary" desktopOnly type="submit"`, 「상점 열기」 | `screens.md` O0 버튼, wireframe `btn pri dk` |
| 버튼(CtaBar) | `CtaBar` 안 `Button variant="primary" type="submit" form={formId}`, 「상점 열기」 | wireframe |
| 비활성 | `!canSubmitOpenStore(address)` 또는 `pending` → `disabled`/`pending`(「처리 중…」) | `Button` README |
| 안내 주석 | 개설 전 이름·주소는 변경 불가라는 안내 문구는 정본에 없어 넣지 않는다 | |
- 두 「상점 열기」 버튼은 같은 폼을 제출한다. jsdom에는 CSS가 없어 둘 다 보인다(테스트는 `getAllByRole`).
- 코드 주석 `// open-issues: C8`(상점명은 가입 시 상호 복사) 한 줄(N-6).
- 「상점명」 칸은 읽기 전용이다. 개설 요청은 그대로 `pickup_address`만 보낸다(Q-1 확정, N-2 주석은 2차에서 삭제).
- 계정 이름이 null이면 폼 대신 `Box` 안내 개설 불가를 그리는 분기를 둔다(D-21 임시). `ownerName`이 빈 값인 경우만 방어한다.

**`StoreStartNotice`** — O0 안내 (`StoreStartNotice({ view: 'pending'|'rejected'|'closed'|'account-blocked' })`, `.body`만 돌려줌)
| view | 태그 | 제목 | 설명 | 출처 |
| --- | --- | --- | --- | --- |
| pending | `StatusTag hot` 「승인 대기」 | 「승인 대기 중이에요」 | 「관리자가 확인하면 상점을 열 수 있어요.」 | wireframe 565 (`screens.md`에는 태그만, C-3) |
| rejected | `StatusTag mute` 「거절됨」 | 「가입이 거절되었습니다」 | 「다시 신청하는 기능은 아직 없어요(확인 필요).」의 「(확인 필요)」는 개발 메모라 **화면에 쓰지 않고** 「다시 신청하는 기능은 아직 없어요.」만 쓴다(D-6) | wireframe 566, `open-issues`에는 없음 |
| closed | `StatusTag mute` 「폐점」 | 「폐점한 상점이에요」 | 「이 계정으로 새 상점을 열 수 없어요.」 | wireframe 568, `screens.md` O7 경고 |
| account-blocked | `StatusTag hot` 「정지」(`states.md` 회원 SUSPENDED) | (없음) | (없음) | 정본 문구 없음. **도달 불가**(Q-6 확정: 정지 상점주는 계정도 정지되어 `/users/me` 403, `auth.md` C-2·D-4). 분기는 방어용으로 유지(N-3, D-22) |
- `Box tag={StatusTag} title={제목}` + `<div className="m">설명</div>`. 한 번에 한 박스만 그린다.

**`StoreSuspendedNotice`** — 정지 안내 (O1에서 쓸 부품, 이번에 만들고 O1 구현 때 배치)
- `Box tag={<StatusTag tone="hot">상점 정지</StatusTag>} title="관리자가 상점을 정지했어요"` + 「새 할인을 올릴 수 없어요. 기존 예약의 픽업은 처리할 수 있어요.」 (wireframe 567에서 "→ O1로 이동, 상단에 이 안내 고정" 메모는 화면에 쓰지 않음)
- **배치 근거(Q-6 확정, D-22)**: 정지 상점주는 계정도 정지되어 로그인 불가 → `found SUSPENDED → O1` 분기와 이 부품의 경로는 현재 도달 불가다(C-1 갱신). 부품 자체는 만들어 둔다: 백엔드가 실제로 계정까지 정지하는지 확인이 남아 있어(C-1 확인 필요), 반대 판정이 나면 O1 배치가 바로 필요해진다. N-5 주석은 근거를 Q-6 확정으로 갱신해 유지한다.

**`StoreCloseForm`** — O7 (`StoreCloseForm({ store: Store, onCancel(): void })`). `.body`와 `CtaBar`를 조각으로 돌려준다. 안에서 `useCloseStore(store)`.
| 부분 | 내용 | 출처 |
| --- | --- | --- |
| 경고 | `Notice` 「폐점하면 다시 열 수 없고, 이 계정으로 새 상점도 만들 수 없어요.」 | `screens.md` O7 |
| 입력 | `Input label={<>확인을 위해 상점명을 입력하세요: <b>{store.name}</b></>}`, `error={errorMessage}` | `screens.md` O7 입력 라벨 |
| 버튼 | 「취소」(`Button`, `onClick={onCancel}`) / 「폐점하기」(`Button variant="dark"`) 두 개를 CtaBar에, 같은 두 개를 본문에 `desktopOnly`로 | `screens.md` O7, `design-system-usage` §5-5 (wireframe O7에는 `dk` 버튼이 없다, C-7) |
| 비활성 | `!canSubmitClose(typed, store.name)` 또는 `pending`이면 「폐점하기」 비활성. 「취소」는 `pending` 중에도 눌린다 | `screens.md` O7 동작 메모 |
| 막는 항목 | 만들지 않는다(D-3 확정). 서버 400만 표시 | N-1 |

### 4.5 `wiring.ts` · 공개 API

```ts
// features/stores/wiring.ts
export function wireStores(): Binding[] {
  return [
    bind(StoreRepositoryToken, new HttpStoreRepository()),  // 소유한 entities 포트
    bind(StoreCommandsToken, new HttpStoreCommands()),      // 이 영역의 포트
  ]
}
```
`features/stores/index.ts`: `StoreOpenForm`, `StoreCloseForm`, `StoreStartNotice`, `StoreSuspendedNotice`. 포트 타입·토큰은 내보내지 않는다(다른 slice가 쓰지 않음). `app/container.ts`: `new Container([...wireAuth(), ...wireStores()])` (`layer-architecture` §6.7, 이 줄은 구현 단계에서 추가).

## 5. pages

**`pages/owner-start`** (O0, `index.ts`는 `OwnerStartPage`만 내보냄)
- `useAuth()`에서 `state.status === 'authenticated'`인 사용자의 `status`, `useMyStore().lookup`을 읽어 `ownerStartView(...)`를 구한다.
- 레이아웃: `<div className="app">`이 아니라 `OwnerLayout`이 이미 `.app`을 그리므로 page는 그 안의 조각이다(`app-shell.md` 상점주 셸). 위에서부터 `AppBar logo title="마감직전 상점주"` + `right={<OwnerLogoutLink />}`, 그 아래 `view`별로 `open-form → StoreOpenForm`, 그 밖 → `StoreStartNotice view`, `null → null`.
- 로그아웃 링크는 `screens.md` O0 텍스트 링크 「로그아웃」. 누르면 C10 확인 시트(`LogoutConfirmSheet`)를 연다. 어느 상태든 보인다.
- `ownerStartView`가 `open-form`이면 `Box` 두 개를 `body split h`로 놓는 wireframe 배치는 쓰지 않는다. 안내 박스는 한 번에 하나만 보이므로 단일 열로 둔다(D-13).

**`pages/store-close`** (O7, `StoreClosePage`만 내보냄)
- `useOwnerStore()`로 상점을 읽고 `useNavigate`로 `onCancel = () => navigate(ROUTES.ownerStore)`(O4로 돌아감).
- `AppBar title="상점 폐점" left={<Link to={ROUTES.ownerStore} aria-label="뒤로">←</Link>}`, 그 아래 `StoreCloseForm`.
- 폐점이 성공하면 `useCloseStore`의 `reload()` → 가드가 `CLOSED`를 보고 `/owner/start`로 보낸다(page는 `navigate`하지 않는다).
- 「뒤로」는 `content.md`에 없는 임시 문구다(`LoginPage`의 `aria-label="닫기"`와 같은 처리, D-11).

## 6. `widgets/owner-nav` 변경 (C-9)

- `OwnerLogoutLink` 신규(`widgets/owner-nav/presentation/OwnerLogoutLink.tsx`): `<button type="button" className="link">로그아웃</button>`. 누르면 `OwnerAccountButton`이 쓰는 `.dim` 겹침 + 포커스 트랩 + Esc 닫기 안에서 `LogoutConfirmSheet`를 연다. 닫으면 링크로 포커스가 돌아온다.
- 겹침 동작을 중복하지 않도록 `OwnerAccountButton` 안의 오버레이(포털·포커스 트랩·Esc)를 같은 폴더의 내부 컴포넌트(예: `OwnerDialogLayer`)로 뽑고 두 컴포넌트가 함께 쓴다. **기존 `OwnerAccountButton` 테스트는 그대로 통과해야 한다**(동작 불변 리팩터링). 공개 API에 `OwnerLogoutLink`만 추가한다.

## 7. `app` 변경

### 7.1 라우트 (D-1 확정, D-2 확정, D-12)

| 화면 | 경로 | 레이아웃 | TabBar | 요소 |
| --- | --- | --- | --- | --- |
| O0 상점 개설 | `/owner/start` (**확정**) | OwnerLayout | 없음 | `OwnerStartPage` |
| O7 상점 폐점 | `/owner/store/close` (**확정**, Q-5) | OwnerLayout | 없음 | `StoreClosePage` |

- 위 두 행은 `app-shell.md` §2 라우트 표에 반영되었다(C-5). O4 자리 page 링크는 D-12(**확정**)가 정하며, `app-shell.md` D-14의 "폐점 링크 자리만"을 대체한다.

- `shared/lib/routes.ts`: `ROUTES.ownerStart = '/owner/start'`, `ROUTES.ownerStoreClose = '/owner/store/close'` 추가.
- `app/router/routes.tsx`: `OwnerLayout` children에 두 라우트 추가(`handle` 없음). `app-shell.md` §2 라우트 표에는 두 행이 없다(C-5, 이 설계안이 정본으로 가리킨다).
- `placeholders.tsx`의 O4 자리 page(`OwnerStorePlaceholder`)에 텍스트 링크 「상점 폐점」(`screens.md` O4 텍스트 링크)을 `ROUTES.ownerStoreClose`로 추가한다(D-12). O4 구현 때 이 자리 page와 함께 사라진다. 이것은 `app-shell.md` D-14 "자리만"의 변경이다(C-5).

### 7.2 `OwnerLayout` + `OwnerStoreGate` (FIXME `OwnerLayout.tsx:12` 해결)

```text
OwnerLayout  (기존: 로그인·역할 가드 decideAccess, 'allow'일 때)
  └─ <MyStoreProvider key={user.id}>
       └─ <OwnerStoreGate>   ← 새 파일 app/layouts/OwnerStoreGate.tsx
            decideOwnerEntry({ lookup, onStartPage: pathname === ROUTES.ownerStart })
              'loading'  → <div className="app" aria-busy="true" />   (OwnerLayout 기존 loading과 같은 방식)
              'error'    → 오류 문구 + 「다시 시도」(`reload`) — OwnerLayout 'error' 분기와 같은 마크업
              'to-start' → <Navigate to={ROUTES.ownerStart} replace />
              'to-today' → <Navigate to={ROUTES.ownerToday} replace />
              'allow'    → <Outlet /> + 기존 TabBar 조건부 (OwnerLayout의 allow 렌더 이동)
```
- `OwnerLayout`의 `case 'allow'`가 지금 그리는 `<div className="app"><Outlet/>{TabBar}</div>`를 `OwnerStoreGate` 안으로 옮긴다(`.app` 프레임은 한 번만).
- 오류 문구: `lookup.message`가 비어 있지 않으면 그것, 아니면 `MY_STORE_ERROR_FALLBACK_MESSAGE`. 「다시 시도」는 기존 임시 문구를 따른다(`auth.md` D-9).
- `OwnerLayout`의 기존 FIXME(`OwnerLayout.tsx:12~14`)는 삭제한다. 가드는 계정 `status`가 PENDING·REJECTED여도 `decideAccess`는 `allow`로 두고(auth D-7 그대로), 상점 유무(`none`)로 O0에 모이게 한다. O0에서 `ownerStartView`가 계정 상태별 안내를 그린다. 계정이 PENDING·REJECTED인 상점주는 상점이 없어 어느 경로로 들어와도 O0로 간다.
- `OwnerLayout`의 TODO 임시 문구 주석(`OwnerLayout.tsx:15~17`)은 그대로 둔다.

### 7.3 로그인 후 이동 (TODO `redirect.ts:40` 처리)

`resolvePostLoginPath`의 **동작은 바꾸지 않는다**. 상점주는 O1 또는 안전한 `/owner/**` `from`으로 가고 `OwnerStoreGate`가 O0로 되돌린다(§1.1, D-7). 주석만 고친다: 상점주 부분을 지우고 관리자 부분만 남긴다(N-4). 그래서 `auth.md` D-6/N-3은 "상점주 부분 해결"로 갱신해야 한다(C-6).

### 7.4 `App.tsx`·`container.ts`

- `App.tsx`: `<AuthProvider><AuthFailureBridge /><RouterProvider/></AuthProvider>` (`AuthFailureBridge`는 `useDep`를 쓰므로 `DepsProvider` 안, 즉 `main.tsx` 구조 그대로).
- `container.ts`: `wireStores()` 한 줄. `tests/app/container.test.ts`의 `TOKENS` 목록에 `StoreRepositoryToken`, `StoreCommandsToken` 추가(같은 커밋).

## 8. F1~F19 점검 메모 (설계 시점)

| 규칙 | 설계에서 확인한 점 |
| --- | --- |
| F1, F2 | features/stores는 features/auth를 import하지 않는다. 두 영역의 접점은 pages·app. `entities/store`는 `features/auth` 타입을 쓰지 않고 `OwnerAccountStatus`로 받는다. 공개 API는 §3.4·§4.5 |
| F3, F4 | `shared/ui`는 평평한 파일. 새 slice는 4계층 이름만 |
| F5, F18 | application은 포트·토큰만. `useDep(StoreRepositoryToken)`은 entities 토큰, `StoreCommandsToken`은 stores 토큰. `HttpStoreRepository`는 stores 소유, entities에 infrastructure 없음. `application`에서 `shared/api` import 없음(`readErrorInfo`는 `shared/lib`) |
| F6, F7 | 가드 판단·O0 화면 판단·상점명 일치·주소 길이는 domain 순수 함수. 컴포넌트는 결과만 표시 |
| F8, F9 | 호출은 `shared/api` `request`·`apiGet`. DTO는 `storeDto.ts` 내부 |
| F10 | `useAsync`가 abort·정리. 요청 훅은 `pending`으로 중복 제출 방지 |
| F11 | 분기는 `errorCode`(`GEOCODING_UNAVAILABLE`, `NOT_FOUND`). 서버 `message` 노출은 정본이 없어 임시(D-10) |
| F12, F13 | 클래스·토큰만. 문구는 §4.4 출처 열. 정본에 없는 문구는 D-10·D-11로 표시 |
| F14 | URI·필드·`error_code`는 §0 |
| F17 | 401 연결은 토큰을 읽지 않고 `clear()`만 호출 |

## 9. 테스트 목록 (`tdd-workflow` §2, Red 대상)

위치는 `tests/` 아래 `src`와 같은 경로. 가짜 구현체는 `tests/<계층>/<slice>/fakes/*.fake.ts`. 새로 만들 보조: `tests/entities/store/fakes/fakeStoreRepository.fake.ts`(`findMine: vi.fn()`), `tests/features/stores/fakes/fakeStoreCommands.fake.ts`(`open`, `close`: `vi.fn()`), `tests/entities/store/fakes/stores.ts`(`activeStore`, `suspendedStore`, `closedStore`, 이름 「망원베이커리」), `tests/support/`에 `renderWithOwnerStore`(인증 가짜 + 상점 가짜 컨테이너 + `MemoryRouter`).

### 9.1 shared

**`tests/shared/lib/useAsync.test.ts`** (훅, `renderHook`)
- 처음 상태는 `loading`.
- `load`가 resolve하면 `success`와 `data`.
- `load`가 reject하면 `error`와 그 값.
- `key`가 바뀌면 `loading`으로 돌아간 뒤 다시 불러온다.
- `reload()`를 부르면 다시 불러온다(호출 횟수 2).
- 언마운트하면 `signal.aborted === true`, 이후 resolve해도 상태가 바뀌지 않는다.
- `key`가 바뀌어 앞 요청이 늦게 끝나도 앞 결과로 상태를 바꾸지 않는다.

**`tests/shared/lib/errorInfo.test.ts`**: `status`·`errorCode`가 있는 객체 → 그대로(`message` 없으면 빈 문자열) / `null`·문자열·`status` 없는 객체 → `{status:0, errorCode:'UNKNOWN', message:''}`.

**`tests/shared/api/client.test.ts`에 추가** (`fetch` 모킹, 기존 파일이 있으면 추가만)
- 401 + `UNAUTHORIZED`: 등록한 핸들러가 정확히 1번 불리고 `ApiError`가 그대로 던져진다.
- 401 + `TOKEN_REVOKED`: 핸들러 1번.
- 401 + 다른 `errorCode`(예: `INVALID_CREDENTIALS`)는 불리지 않는다.
- `auth: false` 요청의 401은 불리지 않는다(로그인 실패).
- 403·404·400·500·`NETWORK_ERROR`는 불리지 않는다.
- 등록 해제 함수를 부른 뒤에는 불리지 않는다. 핸들러가 없어도 오류 없이 던진다.

**`tests/shared/ui/*.test.tsx`** (파일 하나씩)
- `Button`: 기본 `btn`·`type="button"` / `variant primary`→`pri`, `dark`→`dark` / `size sm`→`sm` / `desktopOnly`→`dk` / `disabled`: `aria-disabled="true"`, 클릭해도 `onClick` 안 불림 / `pending`: 이름 「처리 중…」, 클릭 무시 / `type="submit"`인데 `disabled`면 폼 제출 안 됨 / `form` 속성 전달.
- `Input`: `label`과 입력이 연결(`getByLabelText`) / `required`면 라벨 끝 " *" / `error`가 있으면 `alert` 역할로 오류 표시, `aria-invalid="true"`, `aria-describedby`가 오류 id / 오류 없으면 `alert` 없음 / `readOnly`면 `in ro`와 `readonly` / `onChange`는 문자열 값을 받음 / `maxLength` 전달.
- `FieldError`: `role="alert"`, `err` 클래스. `StatusTag`: 톤별 `tag ok|hot|mute`. `Notice`: `warn` 클래스. `CtaBar`: `cta` 클래스, 자식 렌더. `Box`: `tag`→`title`→children 순서, `tone="done"`→`box done`, `title` 없으면 `.t` 없음. `AppBar`: `logo`면 `logo` 클래스, 아니면 `t`, `left`·`right` 위치.

### 9.2 `entities/store`

**`tests/entities/store/domain/store.test.ts`**
- `storeStatusLabel`: ACTIVE→「영업 중」, SUSPENDED→「상점 정지」, CLOSED→「폐점」. `storeStatusTone`: ok, hot, mute.

**`tests/entities/store/domain/ownerEntry.test.ts`** — §3.1 표의 모든 행을 `it.each`로 (`decideOwnerEntry` 10행, `ownerStartView` 표 전 행 + `accountStatus` 5종 × `none`)
- 예: `none`+`onStartPage:false` → `'to-start'`, `found CLOSED`+`onStartPage:false` → `'to-start'`, `found SUSPENDED`+`true` → `'to-today'`.
- `ownerStartView`: `none`+SUSPENDED → `'account-blocked'`, `found ACTIVE` → `null`, `loading` → `null`.

**`tests/entities/store/application/useMyStore.test.tsx`** (가짜 `StoreRepository`를 담은 `Container` + `DepsProvider` + `MyStoreProvider`)
- `findMine`이 pending이면 `lookup.status === 'loading'`.
- store를 돌려주면 `{status:'found', store}`.
- `null`을 돌려주면 `{status:'none'}`.
- `ApiError(0,'NETWORK_ERROR','…')`를 던지면 `{status:'error', errorCode:'NETWORK_ERROR', message}`.
- `reload()`를 부르면 `loading`으로 갔다가 다시 `found`. `findMine` 호출 2번.
- 언마운트하면 넘긴 `signal`이 abort.
- `MyStoreProvider` 밖에서 `useMyStore()` → `Error`. `lookup`이 `none`일 때 `useOwnerStore()` → `Error`. `found`일 때 `Store` 반환.

### 9.3 `features/stores`

**`tests/features/stores/domain/openStoreInput.test.ts`**: `''`, `'   '` → false / `'서울'` → true / `' 서울 '` → true / 500자 → true / 501자 → false / 공백만 500자 → false.

**`tests/features/stores/domain/closeStoreInput.test.ts`**: 같은 이름 → true / 앞뒤 공백 포함 → false / 한 글자 부족(「망원베이커」) → false / 빈 입력 → false / 대소문자만 다른 영문 상점명 → false / NFC·NFD로 쓴 같은 글자 → true / 상점명이 `''`이면 입력이 `''`여도 false.

**`tests/features/stores/domain/storeMessage.test.ts`**
- 개설: `{status:503, errorCode:'GEOCODING_UNAVAILABLE', message:'서버 문구'}` → 「지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.」(서버 문구가 아니라 정본 문구).
- 개설: `ADDRESS_NOT_FOUND`·`STORE_DUPLICATED`·`STORE_ALREADY_EXISTS`·`VALIDATION_ERROR`는 `message` 그대로. `message`가 빈 문자열이면 「상점을 열지 못했어요. 잠시 후 다시 시도해 주세요.」.
- 폐점: `STORE_HAS_OPEN_OFFERS`·`STORE_HAS_RESERVED_RESERVATIONS`·`STORE_ALREADY_CLOSED`·`STORE_SUSPENDED`·`FORBIDDEN`은 `message` 그대로. 빈 문자열이면 「상점을 폐점하지 못했어요. 잠시 후 다시 시도해 주세요.」.

**`tests/features/stores/infrastructure/httpStoreRepository.test.ts`** (`@/shared/api/client` 모킹)
- `findMine`: `/v1/stores/me`를 `apiGet`으로 호출. 응답 DTO(`status:'ACTIVE'`, `created_at` 문자열, 좌표 null) → `Store`(`createdAt`은 `Date`, 좌표 `null`, `closedAt` `null`).
- `closed_at` 문자열 → `closedAt: Date`, `status:'CLOSED'`.
- `ApiError(404,'NOT_FOUND')` → `null`. `ApiError(404,'UNKNOWN')` → 던짐. `ApiError(401,'UNAUTHORIZED')`·`ApiError(403,'FORBIDDEN')`·`NETWORK_ERROR` → 던짐.
- 알 수 없는 `status` 값(`'PAUSED'`) → `Error`.

**`tests/features/stores/infrastructure/httpStoreCommands.test.ts`**
- `open('서울 …')`: `request('/v1/stores', {method:'POST', body:{pickup_address:'서울 …'}, signal})`. 응답(`status` 없음) → `Store`의 `status === 'ACTIVE'`, 좌표는 숫자.
- `close('a/b')`: 경로 `/v1/stores/a%2Fb/close`, `method:'POST'`, 본문 없음. 반환 `undefined`.
- 오류는 그대로 던진다(변환하지 않음).

**`tests/features/stores/application/openStore.test.ts`**: 빈 주소 → `Error`, `commands.open` 호출 0 / `' 서울 '` → `commands.open('서울', …)` / 성공 → `Store` 반환 / 포트 오류는 그대로 던짐.
**`tests/features/stores/application/closeStore.test.ts`**: 이름 불일치 → `Error`, `commands.close` 0 / 일치 → `commands.close(store.id, …)` 1번 / 포트 오류는 그대로 던짐.

**`tests/features/stores/application/useOpenStore.test.tsx`** (가짜 `StoreCommands` + 가짜 `StoreRepository`, `MyStoreProvider`)
- 초기 `pending false`, `errorMessage null`.
- `submit` 중 `pending true`, 끝나면 false.
- 성공 → `findMine`이 다시 불린다(reload).
- `ApiError(503,'GEOCODING_UNAVAILABLE')` → `errorMessage`가 정본 문구, `findMine` 추가 호출 없음.
- `ApiError(400,'ADDRESS_NOT_FOUND', '주소를 찾을 수 없습니다.')` → `errorMessage` 그 문구.
- `ApiError(400,'STORE_ALREADY_EXISTS')` → 문구 + `findMine` 다시 불림.
- 다시 `submit`하면 이전 오류가 지워진다.
- `pending` 중 두 번째 `submit`은 포트를 한 번만 부른다.
- 언마운트 뒤 요청이 끝나도 상태를 바꾸지 않는다(경고 없음).
**`tests/features/stores/application/useCloseStore.test.tsx`**: 위와 같은 구조 + 성공 → `findMine` 다시 불림 / `STORE_HAS_OPEN_OFFERS` → 서버 문구 표시, `findMine` 추가 호출 없음 / `STORE_ALREADY_CLOSED` → 문구 + reload.

**`tests/features/stores/presentation/StoreOpenForm.test.tsx`**
- 「픽업 주소 *」 입력과 「상점 열기」 버튼 두 개(`getAllByRole`)가 있다. 「상점명」 입력은 없다.
- 입력이 비어 있으면 두 버튼 모두 `aria-disabled="true"`. 글자를 입력하면 해제.
- 비활성일 때 눌러도 `open`이 불리지 않는다.
- 입력 후 첫 번째 버튼 클릭 → `open('입력값')` 1번. 두 번째(CtaBar) 버튼도 같은 폼을 제출한다.
- 제출 중 버튼 이름이 「처리 중…」이고 두 번 클릭해도 한 번만 호출.
- `GEOCODING_UNAVAILABLE` 응답 → `alert`에 「지금은 주소를 확인할 수 없어요. 잠시 후 다시 시도해 주세요.」, 입력값은 유지된다.
- 성공 → `findMine`이 다시 불림.
- 입력에 `maxLength` 500.
**`tests/features/stores/presentation/StoreCloseForm.test.tsx`**
- 경고 문구 「폐점하면 다시 열 수 없고, 이 계정으로 새 상점도 만들 수 없어요.」가 보인다. 라벨에 「확인을 위해 상점명을 입력하세요: 망원베이커리」.
- 처음에는 「폐점하기」가 `aria-disabled`. 상점명을 정확히 입력하면 활성, 한 글자 지우면 다시 비활성.
- 비활성일 때 눌러도 `close`가 불리지 않는다.
- 활성에서 클릭 → `close(store.id)` 1번. 제출 중 「처리 중…」.
- 「취소」 클릭 → `onCancel` 호출, `close` 호출 0. 제출 중에도 「취소」는 눌린다.
- `STORE_HAS_OPEN_OFFERS`(400, 서버 문구) → `alert`에 서버 문구, 입력값 유지, 「폐점하기」는 다시 활성.
- 본문 `dk` 버튼과 CtaBar 버튼 두 벌이 있다(`getAllByRole`).
**`tests/features/stores/presentation/StoreStartNotice.test.tsx`**: view별 태그·제목·설명 문구(§4.4 표) / `pending`은 「승인 대기」 태그가 `tag hot` / `rejected`는 「(확인 필요)」 글자가 없다 / `account-blocked`는 「정지」 태그만.
**`tests/features/stores/presentation/StoreSuspendedNotice.test.tsx`**: 「상점 정지」 태그, 제목, 설명 문구.

### 9.4 widgets · pages · app

**`tests/widgets/owner-nav/presentation/OwnerLogoutLink.test.tsx`**: 「로그아웃」 버튼이 보인다 / 누르면 「로그아웃할까요?」 시트(`alertdialog`)가 열린다 / 「취소」·Esc로 닫히고 링크로 포커스가 돌아온다 / 「로그아웃」 확정 → `auth.logout` 호출. **기존 `OwnerAccountButton` 테스트는 변경 없이 통과.**

**`tests/pages/owner-start/presentation/OwnerStartPage.test.tsx`** (인증 가짜 + 상점 가짜)
- 계정 PENDING + 상점 없음 → 「승인 대기 중이에요」, 폼 없음.
- 계정 REJECTED + 상점 없음 → 「가입이 거절되었습니다」.
- 계정 APPROVED + 상점 없음 → 「픽업 주소」 입력, 「상점 열기」.
- 상점 CLOSED → 「폐점한 상점이에요」, 폼 없음.
- 계정 SUSPENDED + 상점 없음 → 「정지」 태그만(도달 불가 분기).
- 어느 경우든 「마감직전 상점주」 로고와 「로그아웃」이 있다. 「로그아웃」 → 확인 시트.
- 상점 ACTIVE일 때(가드가 오기 전 한 프레임) 본문이 비어 있다.
**`tests/pages/store-close/presentation/StoreClosePage.test.tsx`**: 「상점 폐점」 제목, 상점명이 라벨에 보인다 / 「뒤로」·「취소」 클릭 → `/owner/store`로 이동 / 폐점 성공 후 `findMine`이 다시 불린다.

**`tests/app/layouts/OwnerStoreGate.test.tsx`** (`MemoryRouter` + 라우트 + 가짜)
- 조회 중에는 `aria-busy` 프레임, `Outlet` 내용 없음.
- `none`이고 `/owner/today` → `/owner/start`로 이동(Outlet 내용 안 보임).
- `none`이고 `/owner/start` → O0 내용이 보인다(리다이렉트 없음).
- ACTIVE이고 `/owner/start` → `/owner/today`. ACTIVE이고 `/owner/store` → 보인다(TabBar 포함).
- SUSPENDED이고 `/owner/start` → `/owner/today`. SUSPENDED이고 `/owner/store` → 보인다.
- CLOSED이고 `/owner/store/close` → `/owner/start`. CLOSED이고 `/owner/start` → 보인다.
- 조회 오류 → 오류 문구(`message` 또는 기본 문구) + 「다시 시도」. 클릭하면 `findMine` 다시 호출. 서버 문구가 없으면 `MY_STORE_ERROR_FALLBACK_MESSAGE`.
- 같은 계정에서 `/owner/today` ↔ `/owner/store` 이동은 `findMine`을 다시 부르지 않는다(Provider는 한 번).
**`tests/app/layouts/OwnerLayout.test.tsx`에 추가**: 기존 케이스는 상점 가짜를 `activeStore`로 넣어 그대로 통과한다. 로그인 안 함 → A1 / CUSTOMER → 홈은 상점 조회를 시작하지 않는다(`findMine` 호출 0).
**`tests/app/router/routes.test.tsx`에 추가**: `/owner/start` → 상점주 셸 안(`OwnerLayout`), TabBar 없음 / `/owner/store/close` → 같은 셸, TabBar 없음 / 계정 APPROVED+상점 없음 + `/owner` → 최종 O0 폼 / 계정 PENDING + `/owner/today` → O0 승인 대기 / 상점 ACTIVE + `/owner` → O1 자리 page.
**`tests/app/providers/AuthFailureBridge.test.tsx`**: 마운트 후 `notifyAuthFailure()` → `FakeSessionStore.clear` 1번 / 언마운트 후에는 불려도 `clear` 안 불림 / 다시 마운트해도 한 번만(중복 등록 없음).
**`tests/app/App.test.tsx`에 추가**: 상점주가 보호 요청에서 401을 받으면(`clear` 연결) 로그인 화면(A1)으로 간다.
**`tests/app/container.test.ts`**: `TOKENS`에 `StoreRepositoryToken`, `StoreCommandsToken` 추가.
**`tests/features/auth/domain/redirect.test.ts`**: 기존 상점주→O1(`/owner/today`) 케이스가 그대로 통과(동작 불변). 상점주가 안전한 `/owner/**` `from`이면 그 경로.

### Q-1 반영 테스트 추가 (2차)

- **`tests/features/stores/presentation/StoreOpenForm.test.tsx`에 추가**: 「상점명 (가입 시 상호)」 라벨에 연결된 읽기 전용 입력(`readonly`)에 계정 이름이 보이고 편집할 수 없다 / `ownerName`이 `""`(name null 방어, D-21)이면 폼 대신 「계정 정보가 올바르지 않아 상점을 열 수 없어요.」 안내가 보이고 「픽업 주소」·「상점 열기」가 없다.
- **`StoreOpenForm`은 `props: { ownerName: string }`을 받는다**(page가 `user.name` 전달). 기존 테스트의 렌더 호출에 `ownerName: "망원베이커리"`을 추가한다.

### 9.5 E2E (설계만, `qa-verification` §4, `e2e/stores.spec.ts`; `page.route`로 API 모킹)
1. 상점주 로그인, `/v1/stores/me` 404, 계정 APPROVED → `/owner/start` 개설 폼 → 주소 입력 → 「상점 열기」 → `POST /v1/stores` 201 후 `GET /v1/stores/me` 200(ACTIVE) → `/owner/today`.
2. 개설 503 `GEOCODING_UNAVAILABLE` → 오류 문구, 입력 유지, 다시 누르면 성공.
3. 계정 PENDING → O0 「승인 대기 중이에요」, 「로그아웃」 → 확인 → `/login`.
4. 상점 CLOSED → `/owner/start`에서 「폐점한 상점이에요」, `/owner/today` 직접 이동도 O0로.
5. O4 자리 page 「상점 폐점」 → O7 → 상점명 입력 → 「폐점하기」 → 200 후 `GET /stores/me`가 CLOSED → O0 폐점 안내.
6. O7에서 400 `STORE_HAS_OPEN_OFFERS` → 서버 문구 표시, 버튼 다시 활성.
7. 보호 API가 401 `TOKEN_REVOKED` → `/login`으로 이동(토큰 삭제 확인: `localStorage`의 키가 없음).
8. 720px 이상: 「상점 열기」·「폐점하기」 버튼이 본문(`dk`)에 보이고 CtaBar는 숨겨진다.

## 10. 남길 작업 주석 (`code-annotations` §1~§3)

| ID | 위치 | 태그 | 주석 |
| --- | --- | --- | --- |
| N-1 | `features/stores/presentation/StoreCloseForm.tsx` | TODO | `// TODO: 폐점을 막는 항목(진행 중·예정 할인, 픽업 대기 예약)을 먼저 보여 주지 않고, 막는 항목이 0일 때만 버튼을 활성화하지도 않는다. 상점명이 맞으면 눌리고 서버 400 문구만 보인다.`<br>`//   왜: 막는 항목을 셀 offers·reservations 영역이 아직 없다 (docs/design/frontend/stores.md D-3, screens.md O7)`<br>`//   언제: offers 구현 시, reservations 구현 시` |
| (N-2 삭제) | — | | 2차에서 삭제. Q-1 확정(D-20)으로 「상점명」 칸을 읽기 전용 계정 이름으로 채우는 방식이 정해졌다. |
| N-3 | `entities/store/domain/ownerEntry.ts` `account-blocked` 분기 | TODO | `// TODO: 정지 상점주는 계정도 정지되어 /users/me 403이라 이 분기에 도달하지 못한다(사용자 Q-6 확정). 문구도 정해지지 않았다.`<br>`//   왜: 분기는 방어용으로 유지. 관리자의 상점 정지가 실제로 계정까지 정지하는지 백엔드 확인이 남아 있다 (docs/design/frontend/stores.md C-1, D-22)`<br>`//   언제: 결정 후 (백엔드: 정지 시 계정 정지 실제 동작 확인)` |
| N-4 | `features/auth/domain/redirect.ts` `resolvePostLoginPath` (기존 TODO 교체) | TODO | `// TODO: 관리자는 항상 홈으로 보낸다.`<br>`//   왜: 관리자 셸(M1)이 아직 없다 (docs/design/frontend/auth.md D-6). 상점주는 O1로 보내면 OwnerStoreGate가 O0·O1을 정한다 (docs/design/frontend/stores.md §7.3)`<br>`//   언제: admin 구현 시` |
| N-5 | `pages/owner-start/presentation/OwnerStartPage.tsx` 또는 `app/layouts/OwnerStoreGate.tsx` | FIXME | `// FIXME: 상점이 정지되어도 O1에 정지 안내가 고정되지 않는다. 가드는 O1로 보내기만 한다.`<br>`//   왜: O1 화면이 자리 page라 StoreSuspendedNotice를 놓을 곳이 없다 (docs/design/frontend/stores.md §4.4)`<br>`//   언제: O1 구현 시, 늦어도 배포 전` (위치는 `OwnerStoreGate`의 `'to-today'` 분기) |
| N-6 | `features/stores/presentation/StoreOpenForm.tsx` | open-issues | `// open-issues: C8 상점은 가입 시 상호를 이름으로 복사해 만든다. 이름은 입력받지 않는다.` |
| N-7 | `features/stores/domain/storeMessage.ts`, `pages/store-close`(「뒤로」), `entities/store/domain/ownerEntry.ts`(`MY_STORE_ERROR_FALLBACK_MESSAGE`, D-21 계정 name null 안내 문구) | TODO | `// TODO: 임시 문구다(상점 개설·폐점 실패 기본 문구, 서버 메시지 그대로 표시, 「뒤로」, 상점 조회 실패 문구). 정본 문구가 정해지면 바꾼다.`<br>`//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/stores.md D-10, D-11)`<br>`//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)` |
| N-8 | `StoreStartNotice.tsx` | open-issues | `// open-issues: O0 거절된 상점주의 다시 신청 기능은 아직 없다.` (rejected 분기) |
| 삭제 | `app/layouts/OwnerLayout.tsx:12~14` FIXME, `features/auth/application/useAuthController.ts:12~14` FIXME | | 같은 커밋에서 지운다. 해결 방법: §7.2(상점 가드), §2.2(401 연결) |

`placeholders.tsx` 머리 TODO는 이미 O4 자리 page 교체를 `O4 구현 시`로 추적한다. O7 링크는 그 TODO에 포함된다.

## 11. 결정 표

| D-번호 | 항목 | 값 | 임시/확정 | 근거 |
| --- | --- | --- | --- | --- |
| D-1 | O0 경로 | `/owner/start`, `OwnerLayout` 안 | **확정** | 사용자 |
| D-2 | O0 TabBar | 없음 | **확정** | 사용자 |
| D-3 | O7 범위 | 상점명 입력 확인 + 서버 400 문구 표시까지. "막는 항목을 먼저 보여 줌"은 offers·reservations 구현 때(N-1) | **확정** | 사용자 |
| D-4 | `shared/ui` | 이번 화면에서 쓰는 컴포넌트만 만든다(§2.3). auth 화면 교체는 제안만(C-8) | **확정** | 사용자 |
| D-5 | O6 업로드(multipart) | 이번 설계에 반영하지 않음 | **확정** | 사용자(참고) |
| D-6 | O0 거절됨 안내 문구 | wireframe 문구에서 「(확인 필요)」 메모를 뺀 「다시 신청하는 기능은 아직 없어요.」 | **확정** | Q-4(사용자): wireframe.html:566 문구를 정본으로 |
| D-7 | 로그인 후 O0·O1 결정 위치 | 로그인은 O1로 보내고 `app/layouts/OwnerStoreGate`가 `GET /stores/me`로 결정. features 사이 import 없음 | 임시 | F1, `layout.md` 70줄 |
| D-8 | O7 상점명 일치 | NFC 정규화 후 완전 일치(`===`), 공백 정리 없음 | **확정** | Q-7(사용자) |
| D-9 | 401·`TOKEN_REVOKED` 처리 위치 | `shared/api/client.ts`가 알리고 `app/providers/AuthFailureBridge`가 `SessionStoreToken.clear()` 호출. 훅이 아니라 클라이언트 | 임시 | FIXME `useAuthController.ts:12`, 변경 요청(POST)도 덮음 |
| D-10 | 개설·폐점 오류 문구 | 503은 `screens.md` O0 문구, 그 밖은 서버 `message`(비면 기본 문구) | **확정** | Q-2·Q-3(사용자) |
| D-11 | 임시 문구들 | 「뒤로」(aria-label), 상점 조회 실패 「상점 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.」, 개설·폐점 기본 문구 | 임시 | `content.md`에 없음 |
| D-12 | O7 진입 | `/owner/store/close`, O4 자리 page에 「상점 폐점」 링크 | **확정** | Q-5(사용자). `app-shell.md` D-14의 폐점 링크 부분은 이 행으로 대체(C-5, app-shell.md에 반영) |
| D-13 | O0 배치 | 안내 박스·폼을 단일 열로 배치(wireframe의 `split h`는 쓰지 않음). 로딩 뼈대 없음(빈 프레임) | 임시 | 한 번에 한 박스만 그림. `Skeleton`은 만들지 않음 |
| D-14 | 폐점 응답 | 쓰지 않음(`close`는 `Promise<void>`). 성공하면 `GET /stores/me`를 다시 불러 가드가 이동 | 임시 | `reference/stores.md` §2 응답 `{id,name,closed_at}`는 화면이 쓰지 않음 |
| D-15 | 상점 조회 공유 방식 | `MyStoreProvider`(entities)를 `OwnerStoreGate`에서 한 번 마운트, `key={user.id}` | 임시 | `react-implementation` §2 |
| D-16 | 포트 분리 | `StoreRepository.findMine`은 entities(products도 씀), 개설·폐점 `StoreCommands`는 `features/stores/domain` | 임시 | `layer-architecture` §6.2 |
| D-17 | O7 폐점 후 이동 | page가 이동하지 않고 reload → 가드가 `CLOSED`를 O0로 보냄 | 임시 | |
| D-18 | 양쪽 버튼(CtaBar·`dk`) | O0·O7 모두 두 벌 렌더 | 임시 | `design-system-usage` §5-5. wireframe O7에는 `dk` 없음(C-7) |
| D-19 | 개설 요청 값 | 앞뒤 공백을 지운 주소 | 임시 | 서버가 정규화(`reference/stores.md` §1) |
| D-20 | O0 「상점명」 칸 | 읽기 전용 칸: 라벨 「상점명 (가입 시 상호)」, 값 = 계정 이름. 이름 없는 상점주는 허용하지 않는다(null 숨김 분기 없음) | **확정** | Q-1(사용자) |
| D-21 | 계정 `name`이 null로 온 경우 | 가입 시 name은 필수(`schemas.py:10`)라 실제 오면 데이터 오류다. O0에서 폼 대신 「계정 정보가 올바르지 않아 상점을 열 수 없어요.」 안내(개설 불가)를 그린다. 임시 문구(N-7) | 임시(설계자) | 응답 `name`은 nullable(`schemas.py:25`)이라 방어 |
| D-22 | Q-6 전제 | 관리자의 상점 정지는 상점주 계정도 정지시킨다 → 정지 상점주는 `/users/me` 403 → O0 `account-blocked`·`SUSPENDED → O1` 분기 모두 현재 도달 불가. 분기·부품·N-3·N-5는 백엔드 확인 전까지 유지(C-1) | 확정(전제) / 백엔드 동작은 확인 필요 | Q-6(사용자: MVP 전제) |

## 12. 정합 이슈 · 차단 이슈 · 질문 목록

차단 이슈: **없음.**

### 정합 이슈

| C-번호 | 내용 | 양쪽 근거 |
| --- | --- | --- |
| C-1 | **갱신(Q-6 확정, D-22)**: 관리자의 상점 정지는 상점주 계정도 정지시키는 것으로 본다 → 정지 상점주는 `/users/me` 403으로 로그인 불가 → O0 `account-blocked`와 `found SUSPENDED → O1 + StoreSuspendedNotice` 모두 현재 도달 불가. **백엔드 확인 필요**: 상점 정지가 실제로 계정까지 정지하는지는 백엔드 구현을 완전히 확인하지 못해 확인을 남긴다. 분기·부품은 확인 전까지 유지(N-3·N-5) | `auth.md` C-2·D-4, `reference/stores.md` §3, 사용자 Q-6 / `backend/src/stores/domain/store.py:153~158` |
| C-2 | **해소(Q-1 확정, D-20)**: `screens.md` O0의 「상점명」 칸은 읽기 전용 칸으로 계정 이름 + 「(가입 시 상호)」을 표시하고 개설 요청은 `pickup_address`만 보낸다. `open-issues.md` C8 가정과 같다 | `screens.md` O0 / `reference/stores.md` §1, `schemas.py:7~10`, `open-issues.md` C8 |
| C-3 | O0 안내 박스의 제목·설명 문구(승인 대기·거절됨·정지·폐점)는 `wireframe.html`에만 있고 `screens.md`에는 태그만 있다 | `screens.md` O0 상태 태그 / `wireframe.html:565~568` |
| C-4 | `STORE_HAS_RESERVED_RESERVATIONS` 메시지가 명세와 코드가 다르다. 이 검사는 현재 항상 통과 | `reference/stores.md` §2 에러 표 / `backend/src/stores/domain/exceptions.py:107~109` |
| C-5 | `app-shell.md` §2 라우트 표에 O0·O7 행이 없고, D-14는 O4의 폐점 링크를 "자리만"으로 확정했다. 이 설계안은 `/owner/start`, `/owner/store/close`와 자리 page 링크를 추가한다. 두 설계안은 고치지 않았으므로 `app-shell.md`에 반영이 필요 | `app-shell.md` §2·D-14 / `stores.md` §7.1 |
| C-6 | `auth.md`의 D-6·D-7·N-3·N-5·N-6·C-3은 stores 구현으로 상점주 부분이 해결된다(§7.2~7.3, §2.2). `resolvePostLoginPath`는 동작을 바꾸지 않고 상점주를 O1로 보내며, 최종 O0·O1은 가드가 정한다. `layout.md` 70줄과 결과는 같고 방식만 다르다 | `auth.md` §11 주석 표, 399~405행 / `stores.md` §1.1 |
| C-7 | `wireframe.html` O7에는 `dk` 버튼이 없어 720px 이상에서 `.cta`가 사라져 버튼이 없어진다. `screens.md` O0 컴포넌트 목록의 `SplitLayout`은 `components/`에 폴더가 없고 `.split.h` 클래스뿐이다 | `wireframe.html:742` / `design-system-usage` §5-5, `bundle.css` 500~540줄(`.cta{display:none}`) |
| C-8 | 요청 범위를 넘은 추가(제안만, 이번 구현에 포함하지 않음): `features/auth/application/errorInfo.ts`를 `shared/lib/errorInfo.ts`로 합치기, `LoginForm`·`LogoutConfirmSheet`·placeholders를 `shared/ui`로 교체. `auth.md` D-10·Q-10이 "O6 설계 전에 shared/ui를 한다"고 한 것의 일부만 이번에 한다 | `auth.md` D-10 |
| C-9 | 요청 범위를 넘은 필수 추가: `widgets/owner-nav`에 `OwnerLogoutLink`(오버레이 공용화), O4 자리 page 링크. O0의 「로그아웃」 링크를 위해 필요하다. 대안(`pages/owner-start`에 오버레이를 복사)은 포커스 트랩 중복이라 채택하지 않았다 | `screens.md` O0 텍스트 링크 / `OwnerAccountButton.tsx` |

### 질문 목록

| Q-번호 | 질문 | 막는가 |
| --- | --- | --- |
| Q-1 | O0 「상점명」 칸 표시 — **해결(D-20 확정, 사용자)**: (a) 읽기 전용 칸에 계정 이름 + 「(가입 시 상호)」. 이름 없는 상점주는 허용하지 않는다(name null 숨김 분기 없음). name이 null로 오면 개설 불가 처리(D-21 임시). N-2 주석은 삭제 | 아니오 |
| Q-2 | 개설 오류 문구를 서버 `message`로 — **해결(D-10 확정, 사용자)**: 권장안 그대로(503만 정본 문구, 나머지 서버 메시지) | 아니오 |
| Q-3 | O7 오류 문구를 서버 `message`로 — **해결(D-10 확정, 사용자)**: 권장안 그대로 | 아니오 |
| Q-4 | wireframe 안내 문구를 정본으로 — **해결(D-6 확정, 사용자)**: 권장안 그대로(wireframe 문구 사용) | 아니오 |
| Q-5 | O7 경로·자리 page 링크 — **해결(D-12 확정, 사용자)**: `/owner/store/close` + O4 자리 page 「상점 폐점」 링크(app-shell.md에 반영, C-5) | 아니오 |
| Q-6 | 상점 정지가 계정도 정지시키는가 — **해결(D-22 확정, 사용자: MVP 전제)**: 정지 상점주는 계정도 정지로 본다 → 두 분기 모두 도달 불가. 백엔드 실제 동작은 백엔드 확인 필요(C-1) | 아니오 |
| Q-7 | 상점명 일치 방식 — **해결(D-8 확정, 사용자)**: NFC 정규화 후 완전 일치 | 아니오 |
| Q-8 | 공통 오류 변환 — **해소**: `error_handlers.py:71`(403 → `FORBIDDEN`), `:75`(404 → `NOT_FOUND`) 확인. 프론트 가정과 일치(§0) | 아니오 |
