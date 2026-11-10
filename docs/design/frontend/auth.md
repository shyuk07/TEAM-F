# auth 영역 설계: 로그인·세션·셸 가드·로그아웃

- 대상: `features/auth`(영역), `entities/session`, `pages/login`, `widgets/owner-nav`의 계정 메뉴(O8)·로그아웃 확인(C10), `app`의 가드·조립
- 대응 화면: A1 로그인(정식), O8 계정 메뉴(로그아웃 한 줄), C10 로그아웃 확인. 범위 밖: A2 회원가입, A3 비밀번호 재설정, C6~C9·C11, 고객 셸, 관리자(M1~)
- 상태: 설계안 3차(구현 반영). 사용자 확정: D-1, D-2, D-4(임시 처리로 확정), D-14. 그 밖의 설계자 값(D-3, D-5~D-10)은 "임시"이며 구현을 막지 않는다. 구현을 막는 남은 항목은 없다(§11). app-shell.md Q-2는 D-1 확정으로 해소된다.
- 정본: `../../reference/auth.md` §2·§3·§4, `../../design-system/screens.md` A1·C10·O8, `layout.md` 69~72줄, `content.md` 5~12줄, `components/{Input,Button,BottomSheet}/README.md`, `frontend/.claude/skills/{fsd-structure,layer-architecture,api-client,react-implementation,tdd-workflow,code-annotations}`
- 백엔드 실재 확인(`frontend-orchestration.md` §6): `backend/src/auth/presentation/router.py:34`(`/v1` 접두사), `:58` 로그인, `:65` 로그아웃(정지 회원 허용), `:101` `GET /v1/users/me`, `schemas.py`(`TokenResponse`, `UserResponse`), `dependencies.py:39`·`:106`(`/users/me`는 정지 회원 403), `error_handlers.py:33~38`(401·429 처리). 로그인 요청·응답, `error_code`는 명세와 같다. 다른 점은 C-2.
- 기존 코드 현황: `app/container.ts`는 빈 배열, `OwnerLayout` 가드는 항상 통과, `/login`은 `LoginPlaceholder`, `OwnerAccountButton`은 동작 없음, `shared/api`·`shared/lib/di` 완료, features·entities·pages 없음

## 1. 계층 배치와 slice

| slice | 계층 | 이유 |
| --- | --- | --- |
| `entities/session` | application(포트·토큰) | `SessionStore`를 auth 구현체가 만들고, 앱·위 계층이 포트로 받음. 구현체는 두지 않음(`fsd-structure` §1.1, `api-client` §2.1) |
| `features/auth` | domain, application, infrastructure, presentation, `wiring.ts` | 영역. 로그인·로그아웃·내 정보 확인과 인증 Context |
| `pages/login` | presentation | A1 라우트 하나 |
| `widgets/owner-nav` (기존) | presentation 추가(`OwnerAccountMenu`) | O8·C10. 상점주 셸 전용 블록. `features/auth`의 훅·시트를 가져다 씀 |
| `app` | `container.ts`(`wireAuth()` 한 줄), `App.tsx`(Provider), `layouts/OwnerLayout.tsx`(가드), `router/routes.tsx` | |

- `entities/user`는 만들지 않는다(D-5). `User` 타입은 `features/auth/domain`에 두고 공개 API로 내보낸다. 두 번째 영역(stores 등)이 필요로 할 때 내린다(`fsd-structure` §4).
- 인증 Context는 `app/providers`가 아니라 `features/auth`에 둔다(D-14 확정, C-1 해소). widgets·pages가 현재 사용자와 로그아웃을 써야 하는데, 위 계층인 app을 아래 계층이 import할 수 없다(F1).

## 2. 파일 목록과 export

### 2.1 `entities/session`

| 계층 | 파일 | export |
| --- | --- | --- |
| application | `application/ports.ts` | `interface SessionStore { save(token: string): void; clear(): void; hasSession(): boolean; subscribe(listener: (hasSession: boolean) => void): () => void }` |
| application | `application/tokens.ts` | `SessionStoreToken = createToken<SessionStore>('SessionStore')` |
| 공개 API | `index.ts` | `type SessionStore`, `SessionStoreToken` |

`subscribe` 계약(`api-client` §2.1 마지막 줄을 따라 포트에 둠, C-6): 세션이 **같은 탭의 `clear()`** 로 없어지거나 **다른 탭에서** 바뀌었을 때만 `listener(hasSession)`을 부른다. 같은 탭의 `save()`는 부르지 않는다(저장한 쪽이 이미 알고 있으므로 이중 갱신을 막는다). 반환값은 구독 해제 함수.

### 2.2 `features/auth`

**domain** (순수 TypeScript, F6)

| 파일 | export |
| --- | --- |
| `domain/user.ts` | `type Role = 'CUSTOMER' \| 'OWNER' \| 'ADMIN'`, `type AccountStatus = 'PENDING' \| 'APPROVED' \| 'REJECTED' \| 'SUSPENDED' \| 'WITHDRAWN'`, `type User = { id: string; email: string; name: string \| null; phone: string \| null; role: Role; status: AccountStatus; point: number; createdAt: Date }`, `roleLabel(role: Role): string`, `isOwnerPath(path: string): boolean` |
| `domain/authState.ts` | `type AuthState = { status: 'loading' } \| { status: 'anonymous'; cause: 'loggedOut' \| 'other' } \| { status: 'authenticated'; user: User } \| { status: 'error'; errorCode: string; message: string }`, `type AccessDecision = 'loading' \| 'allow' \| 'login' \| 'login-without-from' \| 'home' \| 'error'`, `decideAccess(state: AuthState, required: Role): AccessDecision` |
| `domain/redirect.ts` | `type LoginLocationState = { from: string }`, `isSafeInternalPath(path: string): boolean`, `readFrom(state: unknown): string \| null`, `loginRedirectState(cause: 'loggedOut' \| 'other', currentPath: string): LoginLocationState \| undefined`, `resolvePostLoginPath(user: User, from: string \| null): string` |
| `domain/loginInput.ts` | `canSubmitLogin(email: string, password: string): boolean` |
| `domain/loginMessage.ts` | `INVALID_CREDENTIALS_MESSAGE`(`이메일 또는 비밀번호가 올바르지 않습니다.`), `LOGIN_FALLBACK_MESSAGE`(임시, D-9), `loginErrorMessage(e: { errorCode: string; message: string }): string` |

**application**

| 파일 | export |
| --- | --- |
| `application/ports.ts` | `interface AuthGateway { login(email: string, password: string, signal?: AbortSignal): Promise<LoginResult>; logout(signal?: AbortSignal): Promise<void>; findMe(signal?: AbortSignal): Promise<User> }`, `type LoginResult = { accessToken: string; status: AccountStatus }` |
| `application/tokens.ts` | `AuthGatewayToken = createToken<AuthGateway>('AuthGateway')` |
| `application/login.ts` | `login(deps: { auth: AuthGateway; session: SessionStore }, input: { email: string; password: string }): Promise<User>` |
| `application/logout.ts` | `logout(deps: { auth: AuthGateway; session: SessionStore }): Promise<void>` |
| `application/restoreSession.ts` | `restoreSession(deps, signal: AbortSignal): Promise<AuthState \| null>` (취소되면 `null`) |
| `application/errorInfo.ts` | `readErrorInfo(e: unknown): { status: number; errorCode: string; message: string }` — **내부 파일, 공개 API 아님**. application·presentation은 F5 때문에 infrastructure·`shared/api`의 `ApiError`를 import할 수 없어 오류를 구조(`status`·`errorCode`·`message`)로 읽는다. 회귀 테스트 `tests/features/auth/application/errorInfo.test.ts`를 추가한다 |
| `application/authContext.ts` | `type AuthContextValue = { state: AuthState; login(email: string, password: string): Promise<User>; logout(): Promise<void>; reload(): void }`, `AuthContext`, `useAuth(): AuthContextValue`(Provider 밖이면 throw) |
| `application/useAuthController.ts` | `useAuthController(): AuthContextValue`(상태 전이 전체) |

**infrastructure** (`implements`, DTO는 파일 안에서만)

| 파일 | export |
| --- | --- |
| `infrastructure/httpAuthGateway.ts` | `class HttpAuthGateway implements AuthGateway` |
| `infrastructure/localSessionStore.ts` | `class LocalSessionStore implements SessionStore` (`tokenStorage`의 `saveToken`·`clearToken`·`readToken`·`onTokenChange` 사용. `tokenStorage`를 직접 부르는 두 곳 중 하나, F17) |

**presentation**

| 파일 | export |
| --- | --- |
| `presentation/AuthProvider.tsx` | `AuthProvider({ children })` — `useAuthController()` 값을 `AuthContext`로 제공 |
| `presentation/LoginForm.tsx` | `LoginForm()` — 이메일·비밀번호·오류·「로그인」 |
| `presentation/LogoutConfirmSheet.tsx` | `LogoutConfirmSheet({ onClose }: { onClose(): void })` — C10 시트 |

**`wiring.ts`**: `wireAuth(): Binding[]` = `bind(AuthGatewayToken, new HttpAuthGateway())`, `bind(SessionStoreToken, new LocalSessionStore())`

### 2.3 공개 API

`features/auth/index.ts`: `type User`, `Role`, `AccountStatus`, `AuthState`, `AccessDecision`, `type AuthGateway`, `AuthGatewayToken`, `decideAccess`, `readFrom`, `loginRedirectState`, `resolvePostLoginPath`, `roleLabel`, `useAuth`, `AuthProvider`, `LoginForm`, `LogoutConfirmSheet`. (구현체·wiring·DTO·`login`/`logout`/`restoreSession` 함수는 내보내지 않음)

`entities/session/index.ts`: §2.1. `pages/login/index.ts`: `LoginPage`. `widgets/owner-nav/index.ts`: 기존 그대로(내부에 `OwnerAccountMenu`를 두되 내보내지 않음).

## 3. 동작 규칙

### 3.1 domain

- `isSafeInternalPath(p)`: `/`로 시작하고, `//`·`/\`로 시작하지 않고, `://`을 포함하지 않고, 경로가 `/login`(또는 `/login?…`)이 아니면 true. 빈 문자열·외부 주소·상대 경로는 false(open redirect와 로그인 무한 이동 방지).
- `readFrom(state)`: `{ from: string }`이고 `from`이 `isSafeInternalPath`이면 `from`, 아니면 `null`.
- `loginRedirectState(cause, currentPath)`: `cause === 'loggedOut'`이면 `undefined`(직접 로그아웃했으면 돌아갈 곳이 없음), 아니면 `{ from: currentPath }`(`currentPath`는 `pathname + search + hash`).
- `isOwnerPath(p)`: `p === '/owner'` 또는 `p.startsWith('/owner/')`. `/ownerx`는 false.
- `resolvePostLoginPath(user, from)` (먼저 `from`이 안전하지 않으면 `null`로 본다):

| 역할 | from | 결과 |
| --- | --- | --- |
| OWNER | `isOwnerPath(from)` | `from` |
| OWNER | 그 외·`null` | `ROUTES.ownerToday` (D-6) |
| CUSTOMER | 안전하고 `isOwnerPath`가 아님 | `from` |
| CUSTOMER | 그 외·`null` | `ROUTES.home` |
| ADMIN | 무엇이든 | `ROUTES.home` (M1 구현 전, D-6) |

- `decideAccess(state, required)`: `loading`→`'loading'`, `anonymous`(`cause 'other'`)→`'login'`, `anonymous`(`'loggedOut'`)→`'login-without-from'`, `error`→`'error'`, `authenticated`이고 `user.role === required`→`'allow'`(`status`는 보지 않음, D-7), 역할이 다르면 `'home'`(D-2).
- `canSubmitLogin(email, password)`: `email.trim() !== ''`이고 `password !== ''`(비밀번호는 trim하지 않음). 형식 검사는 하지 않는다(백엔드가 `min_length=1`만 검사, 화면 명세에 형식 오류 문구가 없음). 입력 오류 문구를 새로 만들지 않고 「로그인」 버튼을 비활성(`aria-disabled`)으로 둔다(`Button` README).
- `loginErrorMessage({errorCode, message})`: `INVALID_CREDENTIALS`이면 `INVALID_CREDENTIALS_MESSAGE`(화면 명세 문구 고정, F13), 그 외 `message`가 비어 있지 않으면 `message`(`content.md` 6줄: 계정·보안 서버 오류는 합니다체 그대로. 429 `ACCOUNT_LOCKED`, 403 `FORBIDDEN` 정지 문구, `NETWORK_ERROR`), 비어 있으면 `LOGIN_FALLBACK_MESSAGE`.
- `roleLabel`: `OWNER`→`상점주`, `CUSTOMER`→`고객`, `ADMIN`→`관리자`(`screens.md` A1 역할 목록, 와이어프레임 O8 「owner1@example.com · 상점주」).

### 3.2 application

**`login(deps, input)`**
1. `deps.auth.login(email, password)` → `{accessToken}`. 실패하면 그대로 throw(저장하지 않음).
2. `deps.session.save(accessToken)` (이후 `findMe`가 `shared/api` 클라이언트의 토큰 헤더를 쓰므로 저장이 먼저다).
3. `deps.auth.findMe()` → `User`. 실패하면 `deps.session.clear()` 후 **같은 오류를 다시 throw**(토큰만 남은 반쪽 로그인 상태를 만들지 않음). 정지 상점주는 로그인 200 뒤 `/users/me`가 403이라 여기서 막힌다(C-2, D-4, Q-4).
4. `User`를 돌려준다.

**`logout(deps)`**: `try { await deps.auth.logout() } catch { /* 서버 실패와 관계없이 계속 */ } finally { deps.session.clear() }` (`api-client` §2.1 표). 서버 호출이 끝난 뒤에 `clear()`가 불린다(헤더에 토큰이 필요). 항상 resolve한다.

**`restoreSession(deps, signal)`**
| 조건 | 결과 |
| --- | --- |
| `!session.hasSession()` | `{status:'anonymous', cause:'other'}`, `findMe` 호출 안 함 |
| `findMe` 성공 | `{status:'authenticated', user}` |
| 오류의 `status`가 401 또는 403 (401: `UNAUTHORIZED`·`TOKEN_REVOKED`, 403: 정지 계정, D-4 임시) | `session.clear()` 후 `{anonymous, 'other'}` |
| `signal.aborted` | `null` (호출한 쪽이 상태를 바꾸지 않음) |
| 그 외(`NETWORK_ERROR`, 5xx, `UNKNOWN`) | `{status:'error', errorCode, message}`, 세션은 지우지 않음(일시 장애로 로그아웃시키지 않음) |

**`useAuthController()`** (모든 상태 전이는 여기만)
- 초기 상태: `session.hasSession()`이면 `{loading}`, 아니면 `{anonymous, 'other'}`(동기 계산).
- 세션이 없는 첫 마운트에서는 `restoreSession`을 부르지 않는다(초기 상태가 이미 `anonymous`이므로 상태 전이로 인한 가드 깜빡임을 막는다). 다른 탭 로그인은 `subscribe(true)` → `reload()`로 처리한다.
- 마운트·`reload()`: `AbortController`를 만들어 `restoreSession`을 부르고 `null`이 아닐 때만 상태를 바꾼다. 정리 함수에서 `abort()`(F10).
- `login(email, pw)`: `login` 유스케이스 호출, 성공하면 `{authenticated}`로 바꾸고 `User` 반환. 실패하면 상태를 바꾸지 않고 throw.
- `logout()`: ref 플래그를 켜고 `logout` 유스케이스 호출 → `{anonymous, 'loggedOut'}`로 바꾸고 플래그를 끈다. 플래그가 켜진 동안 `subscribe` 콜백은 무시한다(`clear()`가 일으키는 `'other'` 중간 상태가 가드의 `from` 저장을 일으키지 않게).
- `session.subscribe`: `hasSession === false`이면 `{anonymous, 'other'}`(다른 탭 로그아웃, 같은 탭 401 `clear()`), `true`이면 `reload()`(다른 탭 로그인). 정리 시 해제.
- 반환 값 객체는 `useMemo`로 안정화한다(Context 소비자 불필요 렌더 방지).
- 다른 영역 훅이 받은 401은 이 번 범위에서 처리하지 않는다. 방법은 §8 N-5.

### 3.3 infrastructure

| 메서드 | 엔드포인트 | 요청 | 응답 DTO → domain |
| --- | --- | --- | --- |
| `login` | `POST /v1/auth/login` (`request(..., { auth: false })`) | `{ email, password }` | `{ access_token, token_type, status }` → `LoginResult { accessToken, status }`. `token_type` 버림. `status`가 4개(`APPROVED·PENDING·REJECTED·SUSPENDED`) 밖이면 `Error` |
| `logout` | `POST /v1/auth/logout` | 본문 없음 | 204 → `undefined` |
| `findMe` | `GET /v1/users/me` | | `{ id, email, name, phone, role, users_point, created_at, status }` → `User { id, email, name, phone, role, status, point: users_point, createdAt: new Date(created_at) }`. `name`·`phone`은 `null` 허용. `role`·`status`가 알려진 값이 아니면 `Error` |

`LocalSessionStore`: `save`→`saveToken`, `clear`→`clearToken` 후 같은 탭 구독자에게 `false` 통지, `hasSession`→`readToken() !== null`, `subscribe`→구독자 집합에 등록 + `onTokenChange(cb(readToken() !== null))`를 한 번만 걸고 마지막 구독 해제 때 같이 해제. 같은 탭 `save()`는 통지하지 않는다(§2.1).

### 3.4 presentation

**A1 `pages/login/presentation/LoginPage.tsx`**
- `useAuth().state`와 `useLocation().state`를 읽는다(page가 라우터를 읽음).
  - `authenticated` → `<Navigate replace to={resolvePostLoginPath(user, readFrom(location.state))} />` (이미 로그인한 채 `/login`에 와도, 로그인에 성공해도 이 한 곳에서 이동한다. 로그인 성공 시 별도 `navigate` 호출 없음)
  - `loading` → 아무것도 그리지 않음(`<div className="app" aria-busy="true" />`)
  - `anonymous`·`error` → 화면
- 구성(`screens.md` A1, `wireframe.html` 165~179줄): AppBar(`.bar`)에 「✕」 → `ROUTES.home` 링크(접근 이름 「닫기」, D-8). `.body`: `<h1>로그인</h1>`, `LoginForm`, 텍스트 링크 「비밀번호 재설정」. `.cta`: 「계정이 없나요?」, 버튼 「회원가입」, 텍스트 링크 「사장님이신가요? 입점 신청」. 이 세 개는 도착 화면(A2·A3)이 없으므로 이동하지 않는 자리다(남길 주석 N-1).
- 제목은 「로그인」 고정. 진입 경로별 한 줄(「예약을 이어가려면…」)은 고객 흐름이 없어 그리지 않는다(N-2).
- 상태별 표시

| 상태 | 표시 |
| --- | --- |
| loading(세션 확인 중) | 빈 프레임 |
| anonymous | 빈 폼 |
| error(`/users/me` 실패) | 빈 폼(로그인을 다시 하면 복구됨) |
| 제출 중 | 「로그인」→「처리 중…」, `aria-disabled="true"`, 중복 제출 무시 |
| 제출 실패 | 비밀번호 칸 아래 `err`(역할 `alert`)에 `loginErrorMessage` 문구. 입력값은 유지. 다시 제출하면 지움 |
| 빈·권한 없음 | 해당 없음 |

**`LoginForm`**: `<form noValidate>`. 라벨 「이메일」(`type="email"`, `autoComplete="username"`), 「비밀번호」(`type="password"`, `autoComplete="current-password"`). 사용하는 클래스는 `bundle.css`의 `lbl`, `in`, `err`, `btn pri`(F12). `shared/ui`에 Input·Button이 없으므로 마크업과 클래스를 직접 쓴다(D-10). 비밀번호를 상태·로그에 남기지 않는 것은 입력 칸 값 외에는 없다(F17은 토큰 대상이지만 같은 원칙).

**O8·C10 `widgets/owner-nav/presentation/OwnerAccountButton.tsx` + `OwnerAccountMenu.tsx`**
- `OwnerAccountButton`(기존 마크업 `<button type="button" class="acct">계정</button>` 유지)이 `menu: 'closed' | 'account' | 'logout'` 상태를 가진다. `aria-haspopup="dialog"`, `aria-expanded`.
- 열면 `.app` 프레임 안에 포털로 `.dim > .sheet`를 그린다(버튼의 `closest('.app')`가 포털 대상. 없으면 `document.body`). 라우트는 만들지 않는다(D-3).
- 메뉴 시트(`role="dialog"`, `aria-modal="true"`, 이름 「계정 메뉴」 — D-9 임시): 제목 `user.name ?? user.email`, 보조 한 줄 `${user.email} · ${roleLabel(user.role)}`, 한 줄 `.li` 버튼 「로그아웃」(오른쪽 `›`). `user`는 `useAuth().state`가 `authenticated`일 때만 있으며 없으면 제목·보조 줄을 그리지 않는다. 「내 정보」(C8)·「비밀번호 변경」(C9) 행은 그리지 않는다(D-3, N-4).
- 닫기: `Esc`, 딤 영역 클릭. 닫으면 포커스를 「계정」 버튼으로 돌린다. 열면 첫 버튼으로 포커스를 옮긴다.
- 「로그아웃」 → `LogoutConfirmSheet`(`menu: 'logout'`).
- **`LogoutConfirmSheet`(C10)**: `role="alertdialog"`. 질문 「로그아웃할까요?」(`content.md` 5·12줄), 버튼 「로그아웃」(`btn dark`)·「취소」(`btn`). 처리 중에는 「처리 중…」 + `aria-disabled`, 중복 클릭 무시. 확인하면 `useAuth().logout()` 뒤 `onClose()`. 이동은 하지 않는다(상태가 `anonymous`가 되면 가드가 `/login`으로 보낸다, §4). 「취소」는 서버를 부르지 않고 닫는다.
- 구현 세부: 딤(`.dim`)은 `OwnerAccountButton`이 메뉴 시트와 확인 시트를 번갈아 감싸는 한 겹이다(시트마다 딤을 만들지 않음). 확인 시트가 열리면 첫 포커스는 「취소」다. 시트가 열린 동안 포커스는 시트 안에 머문다. `OwnerAccountMenu`는 `onLogout` prop을 받는다(「로그아웃」 행을 누르면 호출, 확인 시트 전환은 `OwnerAccountButton`이 함).
- 와이어프레임의 부연 문구(「진행 중인 예약은 그대로 남아요…」)는 고객 기준이라 넣지 않는다(Q-7).
- 이 시트는 `LogoutConfirmSheet`가 `features/auth`에 있어 이후 고객 셸(C10, C1로 이동)도 같은 시트를 쓴다.

## 4. 셸 가드 (`app/layouts/OwnerLayout.tsx`)

`const decision = decideAccess(useAuth().state, 'OWNER')`로 분기한다(판단은 domain, F7).

| decision | 렌더 |
| --- | --- |
| `loading` | `<div className="app" aria-busy="true" />` (Outlet·TabBar 없음) |
| `allow` | 기존 구조(`.app` > `Outlet` + 조건부 TabBar) |
| `login` | `<Navigate to={ROUTES.login} replace state={loginRedirectState('other', pathname+search+hash)} />` |
| `login-without-from` | `<Navigate to={ROUTES.login} replace />` |
| `home` | `<Navigate to={ROUTES.home} replace />` (CUSTOMER·ADMIN, D-2) |
| `error` | `.app` 안에 `err`로 `state.message`, 버튼 「다시 시도」(`useAuth().reload()`, 문구 임시 D-9) |

- `App.tsx`: `<AuthProvider><RouterProvider router={router} /></AuthProvider>`. `AuthProvider`는 `DepsProvider`(main.tsx) 안쪽이다. 라우터 밖이므로 라우터 훅을 쓰지 않는다.
- `routes.tsx`: `LoginPlaceholder`를 `LoginPage`(`@/pages/login`)로 바꾼다. 나머지 라우트·`handle`·`*`는 그대로. `/owner` 리다이렉트는 가드 밖이므로 그대로 두고, 비로그인이면 `/owner/today`에서 가드가 `/login`으로 보낸다.
- 가드는 상점주 셸에만 있다. 고객 셸은 이후 고객 설계에서 같은 `decideAccess(…, 'CUSTOMER')`로 만든다.
- 세션이 도중에 없어지면(다른 탭 로그아웃, 같은 탭 401 `clear()`) `state`가 `anonymous`가 되고 가드가 `/login`으로 보낸다.

## 5. 정합 이슈

| C | 내용 | 근거 | 처리 |
| --- | --- | --- | --- |
| C-1 | `api-client` §2.1·§3은 인증 Context 위치를 `app/providers`로 적었다. widgets(O8 메뉴)·pages(A1)가 현재 사용자를 읽어야 하는데 아래 계층이 app을 import할 수 없다(F1) | `api-client/SKILL.md` §2.1 표, §3 / `frontend-invariants` F1 | **해소**: 오케스트레이터가 `api-client` §2.1·§3을 고쳤다(인증 Context = `features/auth`의 `AuthProvider`, `App.tsx`에서 마운트). D-14 확정 |
| C-2 | 로그인은 정지 상점주에게 토큰과 `status: "SUSPENDED"`를 준다(정지 중 픽업 처리 목적). 그러나 `GET /v1/users/me`는 정지 계정을 403으로 막아 프론트가 역할을 알 수 없다. JWT에 `role` 클레임은 있으나 프론트는 토큰을 해독하지 않는다 | `reference/auth.md` §2 104줄·§4 192줄, `backend/src/auth/presentation/router.py:101~103`, `dependencies.py:39·106` | **임시 처리 확정(D-4), 백엔드 확인 필요**: 403은 세션을 지우고 로그인 실패로 처리. 정지 중 픽업 처리(`reference/auth.md` §2 D35·D39)는 이번에 불가하다. 가능하게 하려면 백엔드에 정지 허용 내 정보 조회가 필요하다(프론트에서 정하지 않음) |
| C-3 | `screens.md` A1: 상점주는 로그인 뒤 O0 또는 O1(`GET /v1/stores/me` 결과). stores 영역이 없어 판정할 수 없다 | `screens.md` A1, `layout.md` 70줄 | 임시로 항상 O1(D-6). 남길 주석 N-3 |
| C-4 | `api-map.md`의 A1·C10·O8 행에는 `GET /v1/users/me`가 없는데 가드(세션 복원)와 O8 헤더(이름·이메일·역할)가 이를 쓴다 | `api-map.md` 7·12·13줄, `api-client` §2.1 | 화면 명세는 고치지 않는다. 이 설계안이 그 호출의 근거다(제안만) |
| C-5 | `bundle.css`의 `.in`은 `<div>` 모양(글자색 `--muted`)이다. `<input class="in">`에 쓰면 입력 글자가 흐리게 보일 수 있고 `Input` README에 `input` 요소 마크업이 없다 | `bundle.css` 265~274줄, `components/Input/README.md` | 구현에서 실제 화면을 보고 보고한다. CSS 복사본은 고치지 않는다(F12). 어긋나면 디자인 시스템 쪽 수정을 제안 |
| C-6 | `layer-architecture` §6.3의 `SessionStore` 예시는 3개 메서드이고 `api-client` §2.1은 `subscribe`를 포트에 두라고 한다 | 두 스킬 | **해소**: 오케스트레이터가 `layer-architecture` §4·§6.3에 `subscribe`를 추가했다. `subscribe` 계약(§2.1)은 이 설계안이 상세 정본 |
| C-7 | 요청 범위가 "O8의 다른 항목(C9 등) 자리만 둘지"를 결정 항목으로 두었다. `screens.md` O8은 연결 화면에 C8·C9·C10·O4를 적었고 와이어프레임은 행 3개다 | `screens.md` O8, `wireframe.html` 276~291줄 | D-3: 이번에는 로그아웃 행만. 근거: 이동할 화면이 없는 행은 죽은 버튼이 된다 |

## 6. 골격 (`tdd-workflow` §3)

**그대로 만들 것**(타입·상수·포트·토큰·공개 API·wiring·컨텍스트 객체)

| 파일 | 내용 |
| --- | --- |
| `entities/session/application/ports.ts`, `tokens.ts`, `index.ts` | §2.1 그대로 |
| `features/auth/domain/user.ts` | 타입. `roleLabel`·`isOwnerPath`는 비움 |
| `features/auth/domain/authState.ts` | 타입. `decideAccess` 비움 |
| `features/auth/domain/redirect.ts` | 타입. 함수 4개 비움 |
| `features/auth/domain/loginInput.ts`, `loginMessage.ts` | 상수 2개는 실제 값(`INVALID_CREDENTIALS_MESSAGE`, `LOGIN_FALLBACK_MESSAGE`). 함수 비움 |
| `features/auth/application/ports.ts`, `tokens.ts` | §2.2 그대로 |
| `features/auth/application/errorInfo.ts` | 내부 파일(공개 API 아님). `readErrorInfo`는 실제 구현. 회귀 테스트 `tests/features/auth/application/errorInfo.test.ts` |
| `features/auth/application/authContext.ts` | `AuthContext = createContext<AuthContextValue \| null>(null)` 실제. `useAuth` 비움 |
| `features/auth/wiring.ts`, `index.ts` | §2.2·§2.3 그대로 |
| `app/container.ts` | `...wireAuth()` 한 줄 추가(빈 배열 → 한 줄). 기존 TODO 주석은 이 단계에서 지운다 |

**본문을 비울 것**(`void <인자>; throw new Error('not implemented: <이름>')` 또는 `return null`)

| 파일 | export |
| --- | --- |
| `application/login.ts`, `logout.ts`, `restoreSession.ts`, `useAuthController.ts` | 함수·훅 |
| `infrastructure/httpAuthGateway.ts`, `localSessionStore.ts` | 클래스(생성자는 실제, 메서드 본문 비움) |
| `presentation/AuthProvider.tsx` | `return <>{children}</>`(통과만. 이래야 기존 `App` 테스트가 골격 단계에서 통과) |
| `presentation/LoginForm.tsx`, `LogoutConfirmSheet.tsx` | `return null` |
| `pages/login/presentation/LoginPage.tsx`, `pages/login/index.ts` | `return null` |
| `widgets/owner-nav/presentation/OwnerAccountMenu.tsx` | `return null` (`OwnerAccountButton` 본문은 Green에서 바꿈. 골격에서는 그대로) |

**골격 단계에서 건드리지 않는 기존 파일**(기존 테스트를 유지하려고 Green에서 교체): `app/App.tsx`, `app/layouts/OwnerLayout.tsx`, `app/router/routes.tsx`, `OwnerAccountButton.tsx`. 이렇게 하면 골격 단계에서 `npm run test`의 기존 테스트가 모두 통과하고, Red에서 가드·A1·계정 메뉴 테스트가 케이스 단위로 실패한다.

신규 파일 약 26개(entities 3, domain 6, application 8, infrastructure 2, presentation 3, wiring 1, index 1, pages 2, widgets 1 포함) + 수정 1개(`container.ts`).

## 7. 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

공통 가짜 구현체는 `tests/features/auth/fakes/`에 둔다(`fakeSessionStore.fake.ts`: `save`·`clear`·`hasSession`·`subscribe`가 `vi.fn`이고 `emit(has)`로 구독자를 부름 / `fakeAuthGateway.fake.ts`: `login`·`logout`·`findMe`를 테스트가 원하는 값·`ApiError`로 설정). 렌더 보조는 `tests/support/renderWithAuth.tsx`(`DepsProvider` + 가짜 두 개 + `AuthProvider`, 필요하면 `createMemoryRouter`). 오류는 `new ApiError(status, errorCode, message)`로 만든다. 사용자 객체 고정값은 `tests/features/auth/fakes/users.ts`(`ownerUser`, `customerUser`, `adminUser`).

### (a) `tests/features/auth/domain/redirect.test.ts` — 28

| 대상 | 케이스(입력 → 기대) |
| --- | --- |
| `isSafeInternalPath` (10) | `/owner/today` true / `/` true / `/owner/offers?x=1#a` true / `//evil.com` false / `/\evil` false / `https://evil.com` false / `owner/today` false / `''` false / `/login` false / `/login?x=1` false |
| `readFrom` (6) | `{from:'/owner/offers'}` → `'/owner/offers'` / `null` → `null` / `undefined` → `null` / `'x'` → `null` / `{from:1}` → `null` / `{from:'//evil.com'}` → `null` |
| `resolvePostLoginPath` (10) | OWNER+`null` → `ROUTES.ownerToday` / OWNER+`/owner/offers` → 그대로 / OWNER+`/owner` → `/owner` / OWNER+`/` → ownerToday / OWNER+`/ownerx` → ownerToday / CUSTOMER+`null` → `/` / CUSTOMER+`/offers/1` → 그대로 / CUSTOMER+`/owner/today` → `/` / ADMIN+`/owner/today` → `/` / OWNER+`//evil.com` → ownerToday |
| `loginRedirectState` (2) | `('other','/owner/offers?x=1')` → `{from:'/owner/offers?x=1'}` / `('loggedOut', 아무거나)` → `undefined` |

### (b) `tests/features/auth/domain/authState.test.ts` — 9

`decideAccess(state, 'OWNER')`: loading → `'loading'` / anonymous other → `'login'` / anonymous loggedOut → `'login-without-from'` / error → `'error'` / authenticated OWNER APPROVED → `'allow'` / authenticated OWNER PENDING → `'allow'`(D-7) / authenticated OWNER SUSPENDED → `'allow'` / CUSTOMER → `'home'` / ADMIN → `'home'`.

### (c) `tests/features/auth/domain/loginInput.test.ts` — 5, `loginMessage.test.ts` — 5, `user.test.ts` — 5

- `canSubmitLogin`: `('a@b.c','pw')` true / `('','pw')` false / `('   ','pw')` false / `('a@b.c','')` false / `('a@b.c','  ')` true(비밀번호 공백은 값으로 침).
- `loginErrorMessage`: `INVALID_CREDENTIALS`+임의 서버 문구 → 정확히 `이메일 또는 비밀번호가 올바르지 않습니다.` / `ACCOUNT_LOCKED`+서버 문구 → 서버 문구 / `FORBIDDEN`+`정지된 계정입니다.` → 서버 문구 / `NETWORK_ERROR`+문구 → 그 문구 / 어떤 코드든 `message === ''` → `LOGIN_FALLBACK_MESSAGE`.
- `roleLabel`: OWNER → `상점주` / CUSTOMER → `고객` / ADMIN → `관리자`. `isOwnerPath`: `/owner`·`/owner/today` true, `/ownerx`·`/` false (5개 묶음).

### (d) application — `login.test.ts` 5, `logout.test.ts` 4, `restoreSession.test.ts` 8 (가짜 포트, React 없음)

- `login`: 성공 → `auth.login('a@b.c','pw')` 호출, `session.save('t1')` 호출, `findMe` 호출 순서가 login → save → findMe, `User` 반환 / `auth.login`이 401 `INVALID_CREDENTIALS`로 reject → `session.save` 호출 안 됨, 같은 `ApiError`로 reject / `findMe`가 403 `FORBIDDEN`으로 reject → `session.clear` 호출, 같은 `ApiError`로 reject / `findMe`가 401 → `session.clear` 호출, reject / `findMe`가 `NETWORK_ERROR` → `session.clear` 호출, reject.
- `logout`: 성공 → `auth.logout` 후 `session.clear`(호출 순서) / `auth.logout`이 401 `TOKEN_REVOKED`로 reject → `session.clear` 호출, resolve / `NETWORK_ERROR`로 reject → clear 호출, resolve / 두 호출 모두 한 번씩.
- `restoreSession`: 세션 없음 → `{anonymous,'other'}`, `findMe` 미호출 / 성공 → `{authenticated, user}` / 401 `UNAUTHORIZED` → clear + `{anonymous,'other'}` / 401 `TOKEN_REVOKED` → 같음 / 403 → clear + `{anonymous,'other'}` / `NETWORK_ERROR` → `{error, errorCode:'NETWORK_ERROR', message}`, clear 안 함 / 500 → error, clear 안 함 / 이미 abort된 `signal` → `null`.

### (e) `tests/features/auth/application/useAuthController.test.tsx` — 12 (`renderHook` + `DepsProvider` 가짜 컨테이너)

1. 세션 없음 → 동기로 `{anonymous,'other'}`, `findMe` 미호출
2. 세션 있음 → 처음 `{loading}` → `findMe` 성공 후 `{authenticated}`
3. 세션 있음 + 401 → `{loading}` → `{anonymous,'other'}`, `session.clear` 호출
4. 세션 있음 + 네트워크 오류 → `{error}` → `reload()` 후 성공 → `{authenticated}`
5. `login()` 성공 → `{authenticated}`, 반환 `User`
6. `login()` 실패(401) → 상태 그대로 `{anonymous,'other'}`, 호출한 쪽에서 reject를 받음
7. 로그인된 상태에서 `logout()` → 최종 `{anonymous,'loggedOut'}`이고, 렌더 기록 중 `{anonymous,'other'}`가 한 번도 없음(ref 플래그)
8. 인증된 상태에서 `fakeSessionStore.emit(false)` → `{anonymous,'other'}`
9. anonymous 상태에서 `emit(true)` → `{loading}` → `{authenticated}`(다른 탭 로그인)
10. 언마운트 시 진행 중이던 `findMe`가 받은 `signal.aborted === true`, 이후 상태 갱신 경고 없음
11. `StrictMode`로 감싸도 최종 `{authenticated}`
12. `useAuth()`를 Provider 밖에서 호출 → throw (메시지에 `AuthProvider`)

### (f) infrastructure — `httpAuthGateway.test.ts` 9, `localSessionStore.test.ts` 7

`httpAuthGateway`는 `vi.mock('@/shared/api/client')`로 `request`·`apiGet`·`apiPost`를 바꾼다(`layer-architecture` §6.8).
- `login`: `/v1/auth/login`에 `{email,password}`를 POST, `auth:false`로 호출 / `{access_token:'t', token_type:'bearer', status:'APPROVED'}` → `{accessToken:'t', status:'APPROVED'}`(`token_type` 없음) / `status:'WEIRD'` → reject
- `logout`: `/v1/auth/logout` POST, 본문 없음, 반환 `undefined`
- `findMe`: 전체 DTO → `User`(`createdAt`은 `Date`, `point`는 `users_point`) / `name:null`·`phone:null` 유지 / `role:'WEIRD'` → reject
- `signal` 전달 확인(세 메서드), 401 `ApiError`는 그대로 전파(2개, 총 9)

`localSessionStore`는 jsdom `localStorage`를 실제로 쓴다.
- 처음 `hasSession()` false / `save('t')` 후 true이고 `localStorage['lastcall.accessToken']`가 `'t'` / `clear()` 후 false
- `subscribe`: 같은 탭 `clear()` → 리스너 `false`로 1회 / 같은 탭 `save()` → 리스너 호출 없음 / `StorageEvent`(key 일치, 값 있음) → `true` / 다른 key의 `StorageEvent` → 호출 없음 / 해제 후 이벤트 → 호출 없음

### (g) presentation

**`tests/pages/login/LoginPage.test.tsx` — 14** (`createMemoryRouter` + `renderWithAuth`, `userEvent`)
1. anonymous: 제목 「로그인」(heading 1개), 라벨 「이메일」「비밀번호」, 「로그인」 버튼이 `aria-disabled="true"`
2. 두 칸에 입력하면 「로그인」 `aria-disabled` 해제
3. 「회원가입」 버튼, 「비밀번호 재설정」, 「사장님이신가요? 입점 신청」, 「계정이 없나요?」 문구가 있다. 누르면 URL이 바뀌지 않는다
4. 「✕」(이름 「닫기」)의 `href`가 `/`
5. 제출 성공(OWNER): `auth.login('a@b.c','pw')` 호출, URL `/owner/today`
6. `location.state = {from:'/owner/offers'}`로 진입해 OWNER 로그인 → `/owner/offers`
7. `from`이 `/owner/offers`인데 CUSTOMER로 로그인 → `/`
8. 401 `INVALID_CREDENTIALS` → 폼 안에 `이메일 또는 비밀번호가 올바르지 않습니다.`(role alert), 입력값 유지, URL 그대로 `/login`
9. 429 `ACCOUNT_LOCKED` → 서버 `message`를 표시
10. 로그인 200 + `findMe` 403(정지) → 서버 `message` 표시, `session.clear` 호출, `/login`에 머묾
11. `NETWORK_ERROR` → 그 문구 표시
12. 제출 중: 「처리 중…」, `aria-disabled`, 버튼을 두 번 눌러도 `auth.login` 1회. 오류 뒤 다시 제출하면 오류 문구가 사라졌다가 결과에 따라 다시 나타남
13. 이메일 칸에서 `{enter}`로 제출
14. 이미 로그인(OWNER)한 상태로 `/login` 진입 → `/owner/today`로 이동 / CUSTOMER → `/` / 세션 확인 중(`findMe` 미해결) → 폼도 이동도 없음(`aria-busy`)

**`tests/widgets/owner-nav/presentation/OwnerAccountMenu.test.tsx` — 11** (`OwnerAccountButton`을 `.app` 프레임 안에 렌더, `renderWithAuth`로 OWNER 인증 상태)
1. 「계정」 버튼: `aria-haspopup="dialog"`, `aria-expanded="false"`, 메뉴 없음
2. 클릭 → `aria-expanded="true"`, 대화상자에 이름, `owner@test.com · 상점주`, 「로그아웃」 행
3. 대화상자가 `.app` 프레임 안(`closest('.app')`)에 있다
4. `name`이 `null`이면 제목이 이메일
5. `Esc` → 닫힘, 포커스가 「계정」 버튼으로 복귀
6. 딤 영역 클릭 → 닫힘
7. 「로그아웃」 행 → 「로그아웃할까요?」 확인 시트, 버튼 「로그아웃」「취소」
8. 「취소」 → 시트가 닫히고 `auth.logout` 미호출
9. 「로그아웃」 확인 → `auth.logout` 1회, `session.clear` 1회, 인증 상태가 `{anonymous,'loggedOut'}`
10. 확인 중: 「처리 중…」 + `aria-disabled`, 연타해도 `auth.logout` 1회
11. 서버가 401 `TOKEN_REVOKED`로 거절해도 `session.clear` 호출, 시트 닫힘

**`tests/app/layouts/OwnerLayout.test.tsx` (가드)** — 신규 8
1. 세션 확인 중(`findMe` 미해결) → 본문(`Outlet`)도 TabBar도 없음, `aria-busy`
2. anonymous(other) → `/login`으로 이동, `router.state.location.state`가 `{from:'/owner/today'}`
3. 쿼리가 있는 경로 `/owner/today?x=1` → `from`이 `/owner/today?x=1`
4. 직접 로그아웃(`loggedOut`) → `/login`으로 이동, `location.state`가 `null`
5. CUSTOMER → `/`로 이동
6. ADMIN → `/`로 이동
7. 승인 대기(PENDING) OWNER → 본문이 보임(D-7)
8. `error` → `err` 문구와 「다시 시도」, 누르면 재시도 성공 후 본문이 보임. 또 인증된 뒤 `fakeSessionStore.emit(false)` → `/login` + `from`

### (h) 기존 테스트 변경 (단언은 약화하지 않고 렌더 환경만 바꾼다)

| 파일 | 변경 | 단언 |
| --- | --- | --- |
| `tests/app/container.test.ts` | `TOKENS`에 `SessionStoreToken`, `AuthGatewayToken` 추가(같은 커밋, D-5 규칙) | 기존 3개 그대로 |
| `tests/app/App.test.tsx` | 변경 없음(세션 없음 → `/`는 가드 밖이라 「마감 직전」 그대로, 네트워크 호출 없음). jsdom `localStorage`가 비어 있음을 `beforeEach`에서 `localStorage.clear()`로 보장 | 그대로 |
| `tests/app/layouts/OwnerLayout.test.tsx` 기존 4개 | `renderLayout`이 가짜 컨테이너(OWNER 인증 가짜 게이트웨이 + 세션 있음)와 `AuthProvider`로 감싸고, 첫 단언 전에 `await screen.findByText('본문')`으로 인증 완료를 기다린다. `expect` 4개(마지막 형제·TabBar 없음·`app` 클래스·「오늘」 링크 2개)는 글자 그대로 유지 | 그대로 |
| `tests/app/router/routes.test.tsx` | `renderAt`이 같은 가짜 컨테이너·`AuthProvider`를 쓰고 `/owner/*` 케이스는 `await screen.findByRole('heading', …)`. `/owner`·`/`·`/nope`·`/owner/nope` 케이스는 가드 밖이므로 동기 그대로. `/login` 케이스는 anonymous 가짜로 두고 `heading` 「로그인」을 단언(이전: heading 존재만)하며 셸 없음 단언 두 개는 그대로. 신규: `/owner/today` anonymous → `/login`(+1), `/owner/store` CUSTOMER → `/`(+1), `/login` OWNER 인증 → `/owner/today`(+1) | 기존 단언 모두 유지, 3개 추가 |
| `tests/widgets/owner-nav/presentation/OwnerNav.test.tsx`의 「OwnerAccountButton」 케이스 | 클릭하면 메뉴가 열려 `useAuth`를 쓰므로 이 한 케이스만 `renderWithAuth`로 감싼다. 「접근 이름 「계정」인 button」과 「클릭해도 URL이 바뀌지 않는다」 단언은 그대로 | 그대로 |
| 나머지 `tests/shared/**`, `tests/widgets/owner-nav/domain/**` | 변경 없음 | |

### (i) E2E — `e2e/auth.spec.ts` 신규 8, `e2e/owner-shell.spec.ts` 수정

실서버가 없으므로 `page.route`로 `/v1/auth/login`, `/v1/auth/logout`, `/v1/users/me`를 응답한다(기존 파일 머리 주석 「모킹·실서버 없음」을 「백엔드 응답은 `page.route`로 대체」로 고친다). 헬퍼 `tests/e2e-support/auth.ts`(또는 `e2e/support/auth.ts`)에 `mockOwnerSession(page)`(`addInitScript`로 `localStorage['lastcall.accessToken']='t'` + `/v1/users/me` OWNER 200)를 둔다.
1. 비로그인 `/owner/today` → `/login`, 제목 「로그인」
2. 로그인 성공(OWNER) → `/owner/today`, 「O1 오늘」. `localStorage`에 토큰 저장, 이후 `/v1/users/me` 요청 헤더가 `Authorization: Bearer t…`
3. 비로그인 `/owner/offers` → `/login` → 로그인 → `/owner/offers`로 복귀(D-1)
4. 로그인 실패(401 `INVALID_CREDENTIALS`) → 「이메일 또는 비밀번호가 올바르지 않습니다.」, URL `/login`, 토큰 없음
5. 로그인한 상태에서 새로고침 → 같은 화면 유지(`/v1/users/me` 재확인)
6. `/v1/users/me`가 401 `TOKEN_REVOKED` → `/login`, 토큰 삭제됨
7. 「계정」 → 메뉴 → 「로그아웃」 → 「취소」(그대로) → 「계정」 → 「로그아웃」 → 「로그아웃」(확인) → `/login`, 토큰 삭제, `/v1/auth/logout` 1회, 이후 `/owner/today` → `/login`(`from` 없이 복귀하지 않음). `mobile`·`desktop` 두 프로젝트 모두에서 시트가 `.app` 안에 보인다
8. CUSTOMER 계정으로 로그인 → `/`(「마감 직전」)
- `owner-shell.spec.ts`: 모든 테스트 앞에 `mockOwnerSession(page)`를 호출하는 `test.beforeEach`를 추가한다. `test` 본문 단언은 바꾸지 않는다.

### 테스트 수 합계

domain 52(redirect 28, authState 9, loginInput 5, loginMessage 5, user 5), application 29(login 5, logout 4, restoreSession 8, useAuthController 12), infrastructure 16, presentation 33(LoginPage 14, OwnerAccountMenu 11, OwnerLayout 가드 8), routes 신규 3. 신규 단위·컴포넌트 **약 133개**, E2E 신규 8개. 기존 테스트 수정 파일 4개(§7 (h)).

## 8. 남길 작업 주석 (`code-annotations`, F19)

**이번에 지운다**(구현 시 같은 커밋에서)

| 위치 | 주석 | 처리 |
| --- | --- | --- |
| `src/app/layouts/OwnerLayout.tsx:7` | FIXME 가드 항상 통과 | 가드 구현으로 삭제 |
| `src/app/container.ts:3` | TODO 영역 wiring 없음 | `...wireAuth()` 추가로 삭제 |
| `src/app/router/routes.tsx:18` | TODO 로그인 후 돌아가기 | `location.state.from`(D-1)으로 구현해 삭제 |
| `src/widgets/owner-nav/presentation/OwnerAccountButton.tsx:1` | TODO 계정 버튼 → O8 | 메뉴 연결로 삭제 |

**새로 남긴다**

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| N-1 | `pages/login/presentation/LoginPage.tsx` | TODO | `// TODO: 「회원가입」 버튼과 「비밀번호 재설정」·「입점 신청」 링크가 이동하지 않는다.`<br>`//   왜: 도착 화면 A2·A3가 아직 없다 (docs/design/frontend/auth.md §3.4, D-10)`<br>`//   언제: A2 구현 시, A3 구현 시, 늦어도 배포 전` |
| N-2 | 같은 파일 | TODO | `// TODO: 진입 경로별 안내 한 줄(예약을 이어가려면…)이 없다.`<br>`//   왜: 고객 흐름(C2·내 예약 탭)이 없어 진입 경로를 구분할 수 없다 (screens.md A1 동작 메모)`<br>`//   언제: C2 구현 시` |
| N-3 | `features/auth/domain/redirect.ts` `resolvePostLoginPath` | TODO | `// TODO: 상점주는 항상 O1로, 관리자는 홈으로 보낸다.`<br>`//   왜: 상점 유무로 O0·O1을 정하는 stores 영역과 관리자 셸(M1)이 아직 없다 (auth.md C-3, D-6)`<br>`//   언제: stores 구현 시, admin 구현 시` |
| N-4 | `widgets/owner-nav/presentation/OwnerAccountMenu.tsx` | TODO | `// TODO: 메뉴에 「내 정보」(C8)·「비밀번호 변경」(C9) 행이 없고, PC에서도 드롭다운 대신 시트를 쓴다.`<br>`//   왜: C8·C9 화면이 없고 드롭다운 컴포넌트가 디자인 시스템에 없다 (auth.md D-3)`<br>`//   언제: C8 구현 시, C9 구현 시, 결정 후 (사용자: PC 드롭다운)` |
| N-4b | 같은 파일 | open-issues | `// open-issues: O8 상점주 회원 탈퇴 메뉴 없음 (규칙이 정해질 때까지 메뉴에서 뺌)` |
| N-5 | `features/auth/application/useAuthController.ts` | FIXME | `// FIXME: 다른 영역 요청이 받은 401·TOKEN_REVOKED를 처리하지 않는다. 화면은 다시 불러오기 전까지 로그인 상태로 남는다.`<br>`//   왜: 서버 데이터를 읽는 공용 훅이 아직 없어 401을 세션 정리로 잇는 곳이 없다. 공용 훅이 받은 401에서 SessionStoreToken의 clear()를 부르면 이 컨트롤러가 구독으로 anonymous가 된다 (auth.md §3.2)`<br>`//   언제: products 구현 시(첫 보호 API 화면 O4), 늦어도 배포 전` |
| N-6 | `app/layouts/OwnerLayout.tsx` 가드 | FIXME | `// FIXME: 승인 대기·거부·정지 상점주도 가드를 통과한다. O0(승인 대기) 화면이 없다.`<br>`//   왜: stores 영역이 없어 상점 개설·승인 상태 화면을 만들 수 없다 (auth.md D-7, C-3)`<br>`//   언제: stores 구현 시, 늦어도 배포 전` |
| N-7 | `application/login.ts` 3단계, `restoreSession.ts` 403 분기 | TODO | `// TODO: /users/me가 403이면 로그인 실패로 처리한다. 정지 상점주는 로그인 응답이 200이어도 들어올 수 없다.`<br>`//   왜: 정지 계정은 내 정보를 조회할 수 없다 (auth.md C-2, D-4)`<br>`//   언제: 결정 후 (백엔드: 정지 상점주의 /users/me 허용 여부)` |
| N-8 | `presentation/LoginForm.tsx`·`OwnerLayout.tsx`의 임시 문구 | TODO | `// TODO: 임시 문구다(로그인 실패 기본 문구, 「다시 시도」, 「닫기」, 「계정 메뉴」). 정본 문구가 정해지면 바꾼다.`<br>`//   왜: screens.md·content.md에 해당 문구가 없다 (auth.md D-9)`<br>`//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)` |

`FIXME` 2건(N-5, N-6)은 `list --tag FIXME`에 남으므로 배포 전에 0건이어야 한다.

## 9. 결정 표

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 로그인 후 원래 화면으로 돌아가기(app-shell.md Q-2 해소) | **router `location.state = { from: pathname+search+hash }`**. `readFrom`이 안전한 내부 경로만 통과시킴 | **확정** | 권장 이유: ① 주소창에 노출되지 않고 조작할 수 없어 open redirect 위험이 작다 ② URL이 공유·북마크되지 않아 `/login`이 깨끗하다 ③ `BrowserRouter`의 `history.state`는 새로고침 후에도 유지된다. 사용자 확정 | 아니오(확정됨) |
| D-2 | 상점주 셸에 상점주가 아닌 사람이 들어왔을 때 | **`/`로 이동**(`replace`). 고객·관리자 모두. 새 화면·문구 없음 | **확정** | 「권한 없음」 화면의 정본 문구가 없다. 고객 홈(C1)은 비로그인도 열리므로 안전한 도착지. 관리자는 M1이 생기면 `resolvePostLoginPath`·가드를 바꾼다. 사용자 확정 | 아니오(확정됨) |
| D-3 | O8 메뉴 범위·형태 | 로그아웃 한 줄만. C8·C9 행은 이동할 곳이 없어 이번에는 그리지 않음. 모바일·PC 모두 `.dim > .sheet` 오버레이(PC 드롭다운은 후속). 라우트 없이 포털 오버레이 | 임시 | 죽은 행을 만들지 않음. `bundle.css`에 드롭다운 클래스가 없음(F12). 사용자 요청의 "자리만 둘지"에 대한 권장안 | 아니오 |
| D-4 | `/users/me` 403(정지 계정) | 로그인 흐름에서는 실패로 보고(세션 비움, 서버 문구를 A1에 표시), 세션 복원에서는 비로그인으로 처리. 정지 중 픽업 처리(`reference/auth.md` §2 D35·D39)는 이번에 불가 | **확정**(임시 처리로 확정, 백엔드 확인 필요) | C-2. 사용자 확정. 백엔드가 정지 상점주의 `/users/me`를 허용하면 N-7 주석에 따라 다시 연다 | 아니오 |
| D-5 | `entities/user` | 만들지 않음. `User`는 `features/auth/domain` | 임시 | 두 번째 영역이 필요할 때 내림(`fsd-structure` §4). `container.test.ts` 토큰 목록은 `SessionStoreToken`, `AuthGatewayToken` 2개 | 아니오 |
| D-6 | 로그인 후 역할별 도착지 | OWNER → O1(`ROUTES.ownerToday`), CUSTOMER → `from` 또는 `/`, ADMIN → `/` | 임시 | C-3. `screens.md` A1은 O0/O1을 stores 결과로 정함. stores 구현 때 바꿈 | 아니오 |
| D-7 | 승인 대기·거부·정지 상점주의 가드 | 통과시킴(역할만 본다) | 임시 | stores(O0)가 없음. N-6 | 아니오 |
| D-8 | A1 「✕」 | `ROUTES.home` 링크, 접근 이름 「닫기」 | 임시 | `screens.md` 연결 화면 C1. 이동 규칙이 명세에 없음 | 아니오 |
| D-9 | 임시 문구 | 로그인 실패 기본 문구 `로그인하지 못했어요. 잠시 후 다시 시도해 주세요.`, 가드 오류 버튼 「다시 시도」, A1 「닫기」, 메뉴 대화상자 이름 「계정 메뉴」 | 임시 | 해요체(`content.md` 5줄). 정본에 없음. 기존 `NETWORK_ERROR` 문구와 같은 방식 | 아니오 |
| D-10 | `shared/ui` | 만들지 않음. A1·시트는 `bundle.css` 클래스와 마크업을 직접 씀(placeholders와 같은 방식, app-shell.md D-3) | 임시 | Button·Input·AppBar 컴포넌트는 별도 설계가 필요. 첫 폼이라 이 이슈가 다음 화면(O6·O11)에서 반복되면 `shared/ui` 설계를 먼저 하는 것을 권장 | 아니오 |
| D-11 | 토큰 보관·401·`SessionStoreToken` 사용 | localStorage, client는 throw만, 처리는 인증 Context | **확정** | 사용자(요청서 "확정된 결정") | |
| D-12 | container 한 줄 추가, 경로 상수 `shared/lib/routes.ts` | `...wireAuth()`, `ROUTES` 재사용(추가 상수 없음) | **확정** | app-shell.md D-5, D-17 | |
| D-13 | A1 문구 | `screens.md` A1 그대로(정식 화면) | **확정** | 요청서 | |
| D-14 | Context 위치 | `features/auth`(공개 `AuthProvider`·`useAuth`), 마운트는 `App.tsx` | **확정** | C-1 해소(`api-client` §2.1·§3 수정 완료) | 아니오(확정됨) |

## 10. 정책·보안 메모 (구현 시 지킬 점)

- 토큰은 React 상태·Context 값·로그·URL에 넣지 않는다(F17). `AuthState`에는 `User`만 있다.
- 복귀 경로 검증(`isSafeInternalPath`)은 제어문자와 `\`가 들어 있는 경로도 거부한다.
- `readFrom`이 안전한 내부 경로만 통과시킨다. 사용자 입력으로 `href`·`navigate`를 만들지 않는다.
- 로그인 요청은 `auth:false`(이전 토큰이 남아 있어도 헤더를 붙이지 않음).
- 서버 `message`는 `loginErrorMessage`를 거쳐 JSX 텍스트로만 출력한다(`dangerouslySetInnerHTML` 금지).
- 로그인 오류 문구는 계정 존재 여부를 드러내지 않는 서버 문구(`INVALID_CREDENTIALS`)를 그대로 쓴다.

## 11. 차단 이슈와 질문 목록

구현을 막는 남은 항목은 없다. Q-1~Q-4는 해결됐고(번호 유지), 나머지는 임시값으로 구현할 수 있다.

| Q | 내용 | 권장안 / 해결 | 막는가 |
| --- | --- | --- | --- |
| Q-1 | 로그인 후 돌아가기 방식을 `location.state`로 할지 쿼리로 할지(D-1) | 해결: `location.state` 확정(D-1). app-shell.md Q-2 해소 | 아니오 |
| Q-2 | 상점주 셸에 고객·관리자가 들어오면 어디로 보낼지(D-2) | 해결: `/`로 replace 이동 확정(D-2) | 아니오 |
| Q-3 | 인증 Context를 `features/auth`에 두고 `api-client` §2.1·§3의 "app/providers" 표기를 고칠지(D-14, C-1) | 해결: `features/auth` 확정(D-14), 오케스트레이터가 `api-client` 수정 완료 | 아니오 |
| Q-4 | 정지 상점주 로그인 처리(C-2, D-4). 백엔드 `/users/me`가 정지 계정을 403으로 막는데 로그인은 허용하는 설계다. 정지 중 픽업 처리를 허용하려면 백엔드가 정지 허용 내 정보 API를 주거나 로그인 응답에 역할을 넣어야 한다 | 해결(임시 처리 확정): 세션을 지우고 로그인 실패로 처리, 정지 중 픽업 처리는 이번에 불가(D-4). 백엔드 확인은 N-7 `언제:`로 추적 | 아니오 |
| Q-5 | O8 메뉴에 이번에 C8·C9 행을 자리로 둘지(D-3). 권장안: 두지 않음 | 두지 않음 | 아니오 |
| Q-6 | 승인 대기·거부 상점주 처리(D-7, N-6). stores(O0) 구현 전까지는 통과시키는 것이 괜찮은지 | 통과(임시), 배포 전 FIXME로 추적 | 아니오 |
| Q-7 | C10 시트 부연 문구(「진행 중인 예약은 그대로 남아요…」)를 상점주·관리자에게도 보일지. `screens.md` C10에는 질문 문구가 없고 와이어프레임에만 있다 | 이번에는 뺌 | 아니오 |
| Q-8 | 임시 문구 4개(D-9)를 해요체 임시값으로 둘지 | 임시값 | 아니오 |
| Q-9 | PC 계정 메뉴를 드롭다운으로 할지(`screens.md` O8). 디자인 시스템에 드롭다운 컴포넌트가 없다 | 후속(N-4) | 아니오 |
| Q-10 | 첫 폼이므로 `shared/ui`(Button·Input·FieldError·AppBar) 설계를 별도로 먼저 할지(D-10, C-5) | O6 설계 전에 한다 | 아니오 |
