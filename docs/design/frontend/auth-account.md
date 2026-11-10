# auth 영역 설계 2차: 회원가입·비밀번호 재설정·프로필·비밀번호 변경

- 대상: `features/auth`(영역 확장), `pages/signup`·`pages/password-reset`·`pages/account-profile`·`pages/account-password`(신규), `pages/login`(링크 연결·안내), `widgets/owner-nav`(O8 행 추가), `app`(`layouts/AccountLayout.tsx` 신규, `router/routes.tsx`), `shared/lib/routes.ts`(경로 상수)
- 대응 화면: A2 회원가입(고객·상점주), A3 비밀번호 재설정, C8 프로필 변경, C9 비밀번호 변경, O8 계정 메뉴의 C8·C9 행, A1 로그인의 링크 연결·안내 한 줄·429 잠금 문구
- 범위 밖(추천, D-2): C6 마이, C7 회원 탈퇴 확인, C11 포인트 내역, 고객 셸·고객 가드, 관리자 셸(M1~). C8·C9 라우트는 역할 무관이라 이후 고객 셸(C6)·관리자 셸이 그대로 연결한다.
- 상태: 설계안 2차. 사용자가 결정을 위임해 Q-1~Q-16을 추천안대로, D-1~D-30을 확정했다(2026-11-10). 구현을 막는 항목은 없다.
- 이어받는 설계: `auth.md`(1차, 구현 완료). 이 문서는 그 위에 **더하는 것만** 적는다. `auth.md`의 D·C·N 번호는 `auth.md D-3`처럼 파일명과 함께 가리킨다. 확정되면 `auth.md D-3`(O8 로그아웃 한 줄), `auth.md` N-1·N-4 주석이 이 문서 D-23·§9로 대체된다.
- 정본: 화면 `../../design-system/screens.md` A1·A2·A3·C8·C9·O8, `layout.md`(화면 골격·연결 지도), `wireframe.html` 164~291줄, `content.md`, `open-issues.md`(A3·C8·O8), `components/{RolePicker,Input,Button,Box,CtaBar,AppBar,ListRow}/README.md`, `components/bundle.css`(`.pick`·`.pcard`·`.in.ro`·`.in.code`·`.box`·`.done`·`.cta`·`.dk`). API `../../reference/auth.md` §1·§2·§8·§9·§10·§11, `../../requirements/auth.md` REQ-3·5·6·7·13·22~32
- 백엔드 실재 확인(`frontend-orchestration.md` §6): `backend/src/auth/presentation/router.py:41~56` 가입(201), `:75~87` 재설정 요청(204), `:90~98` 재설정 확인(204), `:106~108` `PATCH /v1/users/me`(`UserResponse`), `:111~126` 비밀번호 변경(204, `keep_jti`로 현재 토큰 유지). 스키마 `schemas.py`(`SignupRequest` 이름·전화 `max_length=100`·이메일 255·비밀번호 128, `ProfileUpdateRequest`, `PasswordChangeRequest`, `PasswordResetConfirmRequest.code` `^\d{6}$`). 오류 처리 `error_handlers.py:33~35`(429 + `Retry-After`), `:53~66`(pydantic 오류 → `VALIDATION_ERROR` `"<필드>: <영문 msg>"`, 도메인 `ValueError` → 한국어 문구), 잠금 문구 `auth/domain/exceptions.py:19~29`(`ceil(초/60)`분), 비밀번호 규칙 `auth/domain/user.py:203~209`(공백만 → 8자 → 72바이트 순). URI·필드·상태 코드·`error_code`는 명세와 같다. 문구 차이는 C-3.
- 기존 코드 현황(fd8a643): `features/auth`(로그인·로그아웃·세션 복원·`AuthProvider`), `pages/login`(A1, 링크 3개는 이동 없음 + TODO N-1), `widgets/owner-nav`(`OwnerAccountMenu`는 로그아웃 한 줄 + TODO N-4), `app/layouts/OwnerLayout.tsx`(가드), `entities/session`. `AccountGateway`·가입·재설정·프로필 코드는 없다.

## 1. 계층 배치와 slice

| slice | 계층 | 이번 변경 | 이유 |
| --- | --- | --- | --- |
| `features/auth` | domain, application, infrastructure, presentation, `wiring.ts` | 확장 | 가입·재설정·프로필·비밀번호 변경은 모두 auth 엔드포인트(`fsd-structure` §1.1) |
| `pages/signup` | presentation | 신규 | A2 라우트 하나 |
| `pages/password-reset` | presentation | 신규 | A3 라우트 하나 |
| `pages/account-profile` | presentation | 신규 | C8 라우트 하나 |
| `pages/account-password` | presentation | 신규 | C9 라우트 하나 |
| `pages/login` | presentation | 수정 | A1 링크 연결, 안내 한 줄(D-7·D-10·D-25) |
| `widgets/owner-nav` | presentation | 수정 | O8 메뉴에 C8·C9 행(D-23) |
| `app` | `layouts/AccountLayout.tsx` 신규, `router/routes.tsx` 수정 | | 역할 무관 로그인 필요 가드(D-4) |
| `shared/lib/routes.ts` | (용도별 폴더) | 수정 | 경로 상수 추가(D-3) |

- entities는 새로 만들지 않는다(D-26). 새 포트 `AccountGateway`는 auth 영역만 쓰므로 `features/auth/application`에 둔다(`fsd-structure` §4 2번).
- 문서 배치(D-1): 같은 slice(`features/auth`)이지만 `auth.md`가 1차 구현 반영본이라, 2차 범위를 이 파일에 따로 둔다. 같은 내용을 두 곳에 쓰지 않고 `auth.md`를 가리킨다.

## 2. 파일 목록과 export

### 2.1 `shared/lib/routes.ts` (추가만)

`ROUTES`에 `signup: '/signup'`, `ownerSignup: '/signup?role=owner'`, `passwordReset: '/password-reset'`, `accountProfile: '/account/profile'`, `accountPassword: '/account/password'`, `account: '/account'`를 더한다. `ROUTE_PATTERNS`는 그대로.

### 2.2 `features/auth/domain` (순수 TypeScript, F6)

| 파일 | 상태 | export |
| --- | --- | --- |
| `domain/passwordRule.ts` | 신규 | `type PasswordCheck = 'ok' \| 'empty' \| 'blank' \| 'tooShort' \| 'tooLong'`, `PASSWORD_MIN_LENGTH = 8`, `PASSWORD_MAX_BYTES = 72`, `utf8ByteLength(text: string): number`, `checkPassword(password: string): PasswordCheck` |
| `domain/signupInput.ts` | 신규 | `type SignupRole = 'CUSTOMER' \| 'OWNER'`, `type SignupForm = { role: SignupRole; name: string; email: string; password: string; phone: string }`, `type SignupInput = SignupForm`(정리된 값), `PROFILE_TEXT_MAX_LENGTH = 100`, `EMAIL_MAX_LENGTH = 255`, `readSignupRole(search: string): SignupRole`, `canSubmitSignup(form: SignupForm): boolean`, `toSignupInput(form: SignupForm): SignupInput`, `nameLabel(role: SignupRole): string` |
| `domain/passwordReset.ts` | 신규 | `isResetCode(code: string): boolean`, `canRequestReset(email: string): boolean`, `canConfirmReset(input: { codeSent: boolean; code: string; newPassword: string }): boolean` |
| `domain/profileInput.ts` | 신규 | `type ProfileForm = { name: string; phone: string }`, `type ProfilePatch = { name?: string; phone?: string }`, `isNameLocked(user: User): boolean`, `profileFormOf(user: User): ProfileForm`, `profilePatch(user: User, form: ProfileForm): ProfilePatch`, `canSaveProfile(user: User, form: ProfileForm): boolean` |
| `domain/passwordChange.ts` | 신규 | `type PasswordChangeForm = { current: string; next: string; confirm: string }`, `isConfirmMismatch(next: string, confirm: string): boolean`, `canSubmitPasswordChange(form: PasswordChangeForm): boolean` |
| `domain/accountMessages.ts` | 신규 | 정본 문구 상수 5개와 임시 문구 상수(§3.1 표), `type FieldError<F extends string> = { field: F; message: string }`, `signupErrorView(e: ErrorLike): FieldError<'email' \| 'form'>`, `resetConfirmErrorMessage(e: ErrorLike): string`, `changePasswordErrorView(e: ErrorLike): FieldError<'current' \| 'form'>`, `accountErrorMessage(e: ErrorLike): string`, `passwordRuleMessage(check: PasswordCheck): string \| null` (`type ErrorLike = { errorCode: string; message: string }`) |
| `domain/redirect.ts` | 수정 | `LoginLocationState`를 `{ from?: string; notice?: LoginNotice }`로 넓힘, `type LoginNotice = 'passwordReset' \| 'signupLoginFailed'`, `readLoginNotice(state: unknown): LoginNotice \| null`, `isAccountPath(path: string): boolean`, `resolvePostLoginPath` 규칙 추가(§3.1) |
| `domain/authState.ts` | 수정 | `decideAccess(state: AuthState, required: Role \| 'ANY'): AccessDecision`(인자 타입만 넓힘. 기존 호출 그대로 동작) |

### 2.3 `features/auth/application`

| 파일 | 상태 | export |
| --- | --- | --- |
| `application/ports.ts` | 수정(추가) | `interface AccountGateway { signup(input: SignupInput, signal?: AbortSignal): Promise<void>; requestPasswordReset(email: string, signal?: AbortSignal): Promise<void>; confirmPasswordReset(input: { email: string; code: string; newPassword: string }, signal?: AbortSignal): Promise<void>; updateProfile(patch: ProfilePatch, signal?: AbortSignal): Promise<User>; changePassword(input: { currentPassword: string; newPassword: string }, signal?: AbortSignal): Promise<void> }`. 기존 `AuthGateway`는 바꾸지 않는다(D-8) |
| `application/tokens.ts` | 수정(추가) | `AccountGatewayToken = createToken<AccountGateway>('AccountGateway')` |
| `application/signup.ts` | 신규 | `type SignupOutcome = { kind: 'loggedIn'; user: User } \| { kind: 'loginFailed' }`, `signupAndLogin(deps: { account: AccountGateway; login(email: string, password: string): Promise<User> }, form: SignupForm): Promise<SignupOutcome>` |
| `application/passwordReset.ts` | 신규 | `requestPasswordReset(deps: { account: AccountGateway }, email: string): Promise<void>`, `confirmPasswordReset(deps: { account: AccountGateway; session: SessionStore }, input: { email: string; code: string; newPassword: string }): Promise<void>` |
| `application/updateProfile.ts` | 신규 | `updateProfile(deps: { account: AccountGateway; session: SessionStore }, patch: ProfilePatch): Promise<User>` |
| `application/changePassword.ts` | 신규 | `changePassword(deps: { account: AccountGateway; session: SessionStore }, form: PasswordChangeForm): Promise<void>` |
| `application/useSubmit.ts` | 신규, **내부 파일(공개 API 아님)** | `type SubmitState = { pending: boolean; error: ErrorInfo \| null; done: boolean }`, `useSubmit<A extends unknown[], R>(run: (...args: A) => Promise<R>): { state: SubmitState; submit(...args: A): Promise<R \| undefined>; reset(): void }` — 4개 폼 훅의 공통 전이(중복 제출 무시, 언마운트 뒤 상태 변경 금지) |
| `application/useSignup.ts` | 신규 | `useSignup(): { submit(form: SignupForm): Promise<SignupOutcome \| undefined>; pending: boolean; error: ErrorInfo \| null }` |
| `application/usePasswordReset.ts` | 신규 | `usePasswordReset(): { sentEmail: string \| null; request(email: string): Promise<void>; resend(): Promise<void>; confirm(code: string, newPassword: string): Promise<boolean>; invalidate(): void; requestPending: boolean; requestError: ErrorInfo \| null; confirmPending: boolean; confirmError: ErrorInfo \| null }` |
| `application/useUpdateProfile.ts` | 신규 | `useUpdateProfile(): { submit(patch: ProfilePatch): Promise<User \| undefined>; pending: boolean; error: ErrorInfo \| null; done: boolean; reset(): void }` |
| `application/useChangePassword.ts` | 신규 | `useChangePassword(): { submit(form: PasswordChangeForm): Promise<boolean>; pending: boolean; error: ErrorInfo \| null; done: boolean; reset(): void }` |
| `application/authContext.ts` | 수정 | `AuthContextValue`에 `replaceUser(user: User): void` 추가(D-13) |
| `application/useAuthController.ts` | 수정 | `replaceUser` 구현 |

`ErrorInfo`는 기존 내부 파일 `application/errorInfo.ts`의 타입이다(`auth.md` §2.2).

### 2.4 `features/auth/infrastructure`

| 파일 | 상태 | export |
| --- | --- | --- |
| `infrastructure/userDto.ts` | 신규, 내부 | `type MeDto`, `toUser(dto: MeDto): User` — `httpAuthGateway.ts` 안의 `MeDto`·`pick`·변환을 옮김(D-30). 공개하지 않음 |
| `infrastructure/httpAccountGateway.ts` | 신규 | `class HttpAccountGateway implements AccountGateway` |
| `infrastructure/httpAuthGateway.ts` | 수정 | `findMe`가 `toUser`를 씀. 동작 변경 없음(기존 테스트 그대로 통과) |

### 2.5 `features/auth/presentation`

| 파일 | 상태 | export |
| --- | --- | --- |
| `presentation/SignupRolePicker.tsx` | 신규, 내부 | `SignupRolePicker({ value, onChange }: { value: SignupRole; onChange(role: SignupRole): void })` |
| `presentation/SignupForm.tsx` | 신규 | `SignupForm({ initialRole, onLoginFailed }: { initialRole: SignupRole; onLoginFailed(): void })` — 폼 전체(본문 칸 + CtaBar·`.dk` 버튼) |
| `presentation/PasswordResetForm.tsx` | 신규 | `PasswordResetForm({ onDone }: { onDone(): void })` |
| `presentation/ProfileForm.tsx` | 신규 | `ProfileForm()` — `useAuth().state.user` 사용(가드 안에서만 렌더) |
| `presentation/PasswordChangeForm.tsx` | 신규 | `PasswordChangeForm()` |

이동(`Navigate`·`navigate`)은 page가 한다. 폼은 결과만 알린다(`onLoginFailed`, `onDone`)(`layer-architecture` §4 "라우터 호출은 컴포넌트", A1과 같은 방식).

### 2.6 `features/auth/wiring.ts`

`bind(AccountGatewayToken, new HttpAccountGateway())` 한 줄 추가. 등록 토큰: `AuthGatewayToken`, `SessionStoreToken`, `AccountGatewayToken`.

### 2.7 공개 API

`features/auth/index.ts`에 추가: `type AccountGateway`, `AccountGatewayToken`, `type SignupRole`, `readSignupRole`, `readLoginNotice`, `type LoginNotice`, `PASSWORD_RESET_DONE_NOTICE`, `SIGNUP_LOGIN_FAILED_NOTICE`, `SignupForm`, `PasswordResetForm`, `ProfileForm`, `PasswordChangeForm`. (구현체·DTO·유스케이스·`useSubmit`·`SignupRolePicker`는 내보내지 않음.)

pages 공개 API: `pages/signup/index.ts` → `SignupPage`, `pages/password-reset/index.ts` → `PasswordResetPage`, `pages/account-profile/index.ts` → `ProfilePage`, `pages/account-password/index.ts` → `PasswordChangePage`. `widgets/owner-nav/index.ts`는 그대로.

## 3. 동작 규칙

### 3.1 domain

**`checkPassword(pw)`** (백엔드 `user.py:203~209`과 같은 순서, REQ-5): `pw === ''` → `'empty'` / `pw.trim() === ''` → `'blank'` / 코드 포인트 수(`[...pw].length`, Python `len`과 같게. `pw.length`는 UTF-16 단위라 쓰지 않음) `< 8` → `'tooShort'` / `utf8ByteLength(pw) > 72` → `'tooLong'` / 그 외 `'ok'`. trim하지 않는다(앞뒤 공백도 비밀번호의 일부).

**`utf8ByteLength(text)`**: 코드 포인트별 1·2·3·4바이트 합(`TextEncoder`를 쓰지 않는 순수 계산).

**`readSignupRole(search)`**: `URLSearchParams(search).get('role') === 'owner'`이면 `'OWNER'`, 그 외(없음·`OWNER`·`admin`·`customer`) `'CUSTOMER'`. 대소문자를 구분한다(만드는 쪽이 `ROUTES.ownerSignup` 하나뿐).

**`canSubmitSignup(form)`**: `name.trim()`·`email.trim()`·`phone.trim()`이 비어 있지 않고 `checkPassword(password) === 'ok'`. 이메일 형식(REQ-3)은 화면에서 검사하지 않고 서버 문구(`이메일 형식이 올바르지 않습니다.`, 도메인 `ValueError`라 한국어)를 보인다(D-14).

**`toSignupInput(form)`**: `name`·`phone`·`email`은 `trim()`, `password`·`role`은 그대로(D-15).

**`nameLabel(role)`**: `CUSTOMER` → `이름 *`, `OWNER` → `상호(상점명으로 쓰임) *`(D-22).

**`isResetCode(code)`**: `/^[0-9]{6}$/`(전각 숫자·공백 거부. 서버 `^\d{6}$`가 pydantic 영문 오류를 내지 않게 화면에서 막음).
**`canRequestReset(email)`**: `email.trim() !== ''`. **`canConfirmReset`**: `codeSent && isResetCode(code) && checkPassword(newPassword) === 'ok'`.

**`isNameLocked(user)`**: `user.role === 'OWNER'`(`open-issues.md` C8 임시 동작).
**`profileFormOf(user)`**: `{ name: user.name ?? '', phone: user.phone ?? '' }`.
**`profilePatch(user, form)`**: 각 칸을 `trim()`해 `(user.<칸> ?? '')`와 다르면 넣는다. `isNameLocked(user)`면 `name`은 넣지 않는다.
**`canSaveProfile(user, form)`**: `profilePatch`가 비어 있지 않고, 넣은 값이 모두 공백이 아니며, `user.role !== 'ADMIN'`이면 변경 뒤 이름·전화번호(`patch.x ?? user.x ?? ''`)가 둘 다 공백이 아님(reference §8 "관리자 제외", REQ-23).

**`isConfirmMismatch(next, confirm)`**: `confirm !== '' && next !== confirm`. **`canSubmitPasswordChange(f)`**: `current !== '' && checkPassword(next) === 'ok' && next === confirm`. (현재 비밀번호는 형식 검사 없음.)

**문구 상수와 오류 매핑(`accountMessages.ts`)**

| 상수 | 값 | 정본 |
| --- | --- | --- |
| `EMAIL_DUPLICATED_MESSAGE` | `이미 가입된 이메일입니다.` | `screens.md` A2 |
| `INVALID_RESET_CODE_MESSAGE` | `코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.` | `screens.md` A3, `content.md` |
| `CURRENT_PASSWORD_MISMATCH_MESSAGE` | `현재 비밀번호가 일치하지 않습니다.` | `screens.md` C9 |
| `PASSWORD_RESET_DONE_NOTICE` | `새 비밀번호로 로그인하세요` | `screens.md` A3 동작 메모 |
| `PROFILE_SAVED_NOTICE` | `저장했어요` | `screens.md` C8 동작 메모 |
| `PASSWORD_CHANGED_NOTICE` | `비밀번호를 바꿨어요.` | **임시**(D-12) |
| `PASSWORD_BLANK_MESSAGE` | `비밀번호는 공백만으로 만들 수 없어요.` | **임시**(D-14) |
| `PASSWORD_TOO_LONG_MESSAGE` | `비밀번호가 너무 길어요. 72바이트 이하로 줄여 주세요.` | **임시**(D-14) |
| `PASSWORD_CONFIRM_MISMATCH_MESSAGE` | `새 비밀번호가 서로 달라요. 다시 확인해 주세요.` | **임시**(D-14) |
| `SIGNUP_LOGIN_FAILED_NOTICE` | `가입했어요. 로그인해 주세요.` | **임시**(D-25) |
| `ACCOUNT_FALLBACK_MESSAGE` | `처리하지 못했어요. 잠시 후 다시 시도해 주세요.` | **임시**(`auth.md` D-9와 같은 방식) |
| `BACK_LABEL` | `뒤로` | **임시**(D-20, ← 링크의 접근 이름) |

| 함수 | 규칙 (D-16) |
| --- | --- |
| `signupErrorView(e)` | `EMAIL_DUPLICATED` → `{ field: 'email', message: EMAIL_DUPLICATED_MESSAGE }`(서버 문구 무시) / 그 외 → `{ field: 'form', message: accountErrorMessage(e) }` |
| `resetConfirmErrorMessage(e)` | `INVALID_RESET_CODE` → `INVALID_RESET_CODE_MESSAGE`(서버 문구는 `재설정 코드가 올바르지 않거나 만료되었습니다.`로 다름, C-3) / 그 외 → `accountErrorMessage(e)` |
| `changePasswordErrorView(e)` | `CURRENT_PASSWORD_MISMATCH` → `{ field: 'current', message: CURRENT_PASSWORD_MISMATCH_MESSAGE }`(서버 문구 `…올바르지 않습니다.`와 다름, C-3) / 그 외 → `{ field: 'form', … }` |
| `accountErrorMessage(e)` | `message !== ''`이면 서버 `message`(`content.md`: 계정·보안 서버 오류는 합니다체 그대로. `VALIDATION_ERROR` 도메인 문구, 403 `정지된 계정입니다.`, `NETWORK_ERROR`), 비면 `ACCOUNT_FALLBACK_MESSAGE` |
| `passwordRuleMessage(check)` | `'blank'` → `PASSWORD_BLANK_MESSAGE`, `'tooLong'` → `PASSWORD_TOO_LONG_MESSAGE`, 그 외 `null`(`'tooShort'`는 라벨 「(8자 이상)」이 알려 주므로 문구 없이 버튼만 비활성) |

**`redirect.ts` 추가 규칙**
- `readLoginNotice(state)`: `{ notice: 'passwordReset' | 'signupLoginFailed' }`이면 그 값, 아니면 `null`.
- `isAccountPath(p)`: `p === '/account'` 또는 `p.startsWith('/account/')`(`/accountx` false).
- `resolvePostLoginPath(user, from)`: 안전한 `from`이 `isAccountPath`이면 **역할과 관계없이** `from`(D-29). 나머지는 `auth.md` §3.1 표 그대로.
- `readFrom`은 그대로 쓴다(`notice`가 같이 있어도 `from`만 읽음).

**`decideAccess(state, 'ANY')`**: `authenticated`면 역할과 관계없이 `'allow'`. 그 외 상태는 기존과 같다(`'home'`은 나오지 않음).

### 3.2 application

**`signupAndLogin(deps, form)`**
1. `input = toSignupInput(form)`, `await deps.account.signup(input)`. 실패하면 그대로 throw(로그인 호출 안 함).
2. `try { user = await deps.login(input.email, input.password) } catch { return { kind: 'loginFailed' } }` (가입 응답에 토큰이 없어 같은 이메일·비밀번호로 로그인, `screens.md` A2. `deps.login`은 훅이 넘기는 `useAuth().login`이라 성공하면 인증 상태가 바뀐다).
3. `{ kind: 'loggedIn', user }`.

**`requestPasswordReset(deps, email)`**: `deps.account.requestPasswordReset(email.trim())`. 오류는 그대로 throw.
**`confirmPasswordReset(deps, input)`**: `deps.account.confirmPasswordReset(input)` 성공 뒤 `deps.session.clear()`(재설정은 모든 토큰 무효, REQ-32, `api-client` §2.1. 비로그인 화면이라 보통 세션이 없지만 남은 토큰을 지운다, D-10). 실패하면 `clear()`를 부르지 않고 throw.
**`updateProfile(deps, patch)`**: `deps.account.updateProfile(patch)` → `User`. 오류의 `status === 401`이면 `deps.session.clear()` 후 같은 오류 throw(D-18). 그 외 오류는 그대로 throw.
**`changePassword(deps, form)`**: `deps.account.changePassword({ currentPassword: form.current, newPassword: form.next })`. **성공해도 `session.clear()`를 부르지 않는다**(현재 토큰 유지, D-9, C-1). 401이면 `clear()` 후 throw.

**`useSubmit(run)`** (공통 전이, F10)
- `submit(...args)`: `pending`이면 `undefined`를 돌려주고 무시(ref 플래그로 같은 틱 연타도 막음). `{pending:true, error:null, done:false}` → 성공 `{pending:false, done:true}` 후 결과 반환 / 실패 `{pending:false, error: readErrorInfo(e)}` 후 `undefined`.
- 언마운트되면 그 뒤 상태를 바꾸지 않는다(마운트 ref). `useSubmit`이 `AbortController`를 하나 두고 정리 때 `abort()`하며 `run(input, signal)`으로 넘긴다(D-32). abort로 생긴 오류는 상태로 만들지 않는다.
- `reset()`: `{pending:false, error:null, done:false}`.

**`useSignup()`**: `useDep(AccountGatewayToken)`, `useAuth().login`으로 `signupAndLogin` 호출. 결과를 그대로 돌려준다(이동은 page).
**`usePasswordReset()`**
- `request(email)`: 성공하면 `sentEmail = email.trim()`(2단계가 열림). 실패하면 `requestError`.
- `resend()`: `sentEmail`로 `request` 다시(「코드 다시 받기」). 60초 안이면 서버가 새 코드를 만들지 않지만 응답은 같다(REQ-28-1). 화면은 차이를 표시하지 않는다(D-24).
- `confirm(code, pw)`: `confirmPasswordReset({ email: sentEmail, code, newPassword: pw })`. 성공 `true`, 실패 `false` + `confirmError`.
- `invalidate()`: `sentEmail = null`, `confirmError = null`(이메일 칸을 고치면 호출, D-24).
**`useUpdateProfile()`**: 성공하면 `useAuth().replaceUser(user)` 후 `done = true`.
**`useChangePassword()`**: 성공 `true`·`done = true`.
**`replaceUser(user)`**: 상태가 `authenticated`일 때만 `{ authenticated, user }`로 바꾼다. 그 외 상태에서는 무시. `reload()`를 쓰지 않는 이유: `reload()`는 `loading`을 거쳐 가드가 화면을 내렸다 올리므로 C8 폼 상태(완료 표시)가 사라진다.

### 3.3 infrastructure (`HttpAccountGateway`, DTO는 파일 안에서만)

| 메서드 | 엔드포인트 | 요청 | 응답 |
| --- | --- | --- | --- |
| `signup` | `POST /v1/auth/signup` (`auth: false`) | `{ email, password, name, phone, role }` | 201 `UserResponse` → 쓰지 않음(`void`) |
| `requestPasswordReset` | `POST /v1/auth/password-reset/request` (`auth: false`) | `{ email }` | 204 |
| `confirmPasswordReset` | `POST /v1/auth/password-reset/confirm` (`auth: false`) | `{ email, code, new_password }` | 204 |
| `updateProfile` | `PATCH /v1/users/me` | 넣은 키만(`{ phone }`처럼. `undefined` 키를 만들지 않음) | 200 `MeDto` → `toUser` |
| `changePassword` | `POST /v1/users/me/password` | `{ current_password, new_password }` | 204 |

- 모두 `request<T>(path, { method, body, signal, auth })`를 쓴다(F8). `signal`을 그대로 넘긴다.
- 429 `Retry-After`는 읽지 않는다(D-17). `ApiError`는 바꾸지 않는다.

### 3.4 presentation·pages

공통(D-19·D-20)
- 골격: `<div className="app">` > `<form noValidate style={{ display: 'contents' }}>` > AppBar(`.bar`) + `.body` + `.cta`. `display: contents`로 `.app`의 flex 배치(`.cta`의 `margin-top: auto`)를 깨지 않고 CtaBar 버튼도 같은 폼의 submit이 된다.
- 주 버튼은 와이어프레임(`wireframe.html:757·762`)처럼 두 번 그린다: `.body` 끝의 `btn pri dk`(720px 이상)와 `.cta` 안의 `btn pri`(모바일). 둘은 같은 상태(문구·`aria-disabled`)다. 비활성은 `aria-disabled="true"`(`Button` README), 처리 중은 「처리 중…」.
- AppBar: `<Link to={뒤로} aria-label={BACK_LABEL}>←</Link>` + `<h1 className="t">제목</h1>` + `<span className="sp" />`(`AppBar` README "하위 화면: ← + 화면 제목").
- 입력: `label.lbl` + `input.in`(A1 `LoginForm`과 같은 방식, `auth.md` D-10). 오류는 칸 바로 아래 `div.err[role=alert]`(`Input` README).
- 서버 `message`는 JSX 텍스트로만 출력(F17 보안 메모).

**A2 `pages/signup/presentation/SignupPage.tsx`**
- `useAuth().state`: `authenticated` → `<Navigate replace to={resolvePostLoginPath(user, readFrom(location.state))} />`(A1과 같은 한 곳 이동, D-5) / `loading` → `<div className="app" aria-busy="true" />` / 그 외 화면.
- AppBar ← → `ROUTES.login`, `state = location.state`를 그대로 넘겨 `from`을 잃지 않는다. 제목 「회원가입」.
- `SignupForm initialRole={readSignupRole(location.search)} onLoginFailed={() => navigate(ROUTES.login, { replace: true, state: { from, notice: 'signupLoginFailed' } })}`.
- `SignupForm` 본문(와이어프레임 183~199줄 순서): 라벨 「어떻게 이용하시나요? *」 + `SignupRolePicker` / `.m` 「한 계정은 한 가지 유형이에요. 상점주는 관리자 승인 후 상점을 열 수 있어요.」(와이어프레임 문구) / `nameLabel(role)` 칸(`autoComplete="name"`(고객)·`"organization"`(상점주), `maxLength=100`) / 「이메일 *」(`type="email"`, `autoComplete="username"`, `maxLength=255`, 아래 이메일 오류) / 「비밀번호 * (8자 이상)」(`type="password"`, `autoComplete="new-password"`, 아래 `passwordRuleMessage`) / 「전화번호 *」(`type="tel"`, `autoComplete="tel"`, `maxLength=100`) / 폼 오류 `err` / `btn pri dk` 「가입하기」. `.cta`: `btn pri` 「가입하기」.
- `SignupRolePicker`(D-21): `<div className="pick" role="radiogroup" aria-labelledby=라벨id>` 안에 `<button type="button" role="radio" aria-checked className={on ? 'pcard on' : 'pcard'}>`(아이콘 `.ic` + 와이어프레임 SVG 경로, `<b>일반 고객</b><span className="m">할인을 예약하고 픽업</span>` / `<b>상점주</b><span className="m">할인을 올리고 픽업 관리</span>`). 방향키 이동은 하지 않는다(두 항목, Tab·클릭).
- 상태 표

| 상태 | 표시 |
| --- | --- |
| 처음 | 역할 = `initialRole`, 빈 칸, 「가입하기」 비활성 |
| 입력 중 | `canSubmitSignup`이면 활성. 비밀번호 `blank`·`tooLong`이면 비밀번호 칸 아래 임시 문구 |
| 제출 중 | 「처리 중…」 + `aria-disabled`, 연타 무시 |
| 409 `EMAIL_DUPLICATED` | 이메일 칸 아래 `이미 가입된 이메일입니다.`, 입력값 유지 |
| 400·403·네트워크 | 폼 오류 자리에 `accountErrorMessage` |
| 가입·로그인 성공 | 인증 상태가 바뀌어 page가 `Navigate`(고객 → `from` 또는 `/`, 상점주 → `/owner/today`, `auth.md` D-6·N-3) |
| 가입 성공·로그인 실패 | `onLoginFailed` → A1(`notice: 'signupLoginFailed'`) |
| 로딩·빈·권한 없음 | 세션 확인 중 빈 프레임 / 빈 상태 없음 / 로그인 상태면 이동 |

**A3 `pages/password-reset/presentation/PasswordResetPage.tsx`**
- 가드·로딩은 A2와 같다(D-5). AppBar ← → `ROUTES.login`(state 그대로), 제목 「비밀번호 재설정」.
- `PasswordResetForm onDone={() => navigate(ROUTES.login, { replace: true, state: { from: readFrom(location.state) ?? undefined, notice: 'passwordReset' } })}`.
- `PasswordResetForm` 본문(와이어프레임 205~218줄)
  - 라벨 「1단계 · 코드 받기」, `.box` 안: 「가입한 이메일」(`type="email"`, `autoComplete="username"`, `maxLength=255`), `btn` 「코드 보내기」(`type="button"`, `canRequestReset` 아니면 비활성, 처리 중 「처리 중…」), `.m` 「가입된 이메일이면 6자리 코드를 보내요.」(와이어프레임 문구), 요청 오류 `err`.
  - `sentEmail !== null`일 때만: 라벨 「2단계 · 새 비밀번호」, `.box` 안: 「6자리 코드」(`className="in code"`, `inputMode="numeric"`, `autoComplete="one-time-code"`, `maxLength=6`), 「새 비밀번호 (8자 이상)」(`type="password"`, `autoComplete="new-password"`, 아래 `passwordRuleMessage`), 확인 오류 `err`(`resetConfirmErrorMessage`), `<button type="button" className="link">코드 다시 받기</button>`.
  - 주 버튼 「비밀번호 바꾸기」(`.dk` + `.cta`, submit): `canConfirmReset` 아니면 비활성.
  - 이메일 칸을 바꾸면 `invalidate()`: 2단계가 닫히고 코드 칸을 비운다(D-24).
  - 확인 성공(`confirm` → `true`) → `onDone()`.

| 상태 | 표시 |
| --- | --- |
| 처음 | 1단계만, 「비밀번호 바꾸기」 비활성 |
| 코드 요청 중 | 「코드 보내기」 → 「처리 중…」 |
| 요청 204 | 2단계가 열림(가입 여부와 무관하게 같은 화면, REQ-27) |
| 요청 실패(네트워크·400) | 1단계 상자 안 `err`에 `accountErrorMessage` |
| 확인 400 `INVALID_RESET_CODE` | 2단계 `err`에 `코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.`, 입력값 유지 |
| 확인 400 `VALIDATION_ERROR` | 서버 문구(예: 도메인 비밀번호 규칙 문구). 코드는 유효한 채 남음(REQ-29) |
| 확인 204 | 세션 정리 후 A1로 이동, A1에 안내 |

**A1 `pages/login/presentation/LoginPage.tsx` 수정**(D-7·D-10·D-25)
- `from = readFrom(location.state)`, `linkState = from !== null ? { from } : undefined`.
- 「비밀번호 재설정」 → `<Link className="link" to={ROUTES.passwordReset} state={linkState}>`.
- 「회원가입」 → `<Link className="btn" to={ROUTES.signup} state={linkState}>`(링크 역할. 버튼 모양은 `btn` 클래스).
- 「사장님이신가요? 입점 신청」 → `<Link className="link" to={ROUTES.ownerSignup} state={linkState}>`.
- 안내 한 줄: `readLoginNotice(location.state)`가 `'passwordReset'`이면 `<div className="box done" role="status">새 비밀번호로 로그인하세요</div>`, `'signupLoginFailed'`이면 같은 자리에 `SIGNUP_LOGIN_FAILED_NOTICE`. 위치는 `<h1>로그인</h1>` 바로 아래(와이어프레임의 진입 안내 한 줄 자리). `Box` README "성공 확인은 `box done`".
- 429 `ACCOUNT_LOCKED`: 기존대로 `loginErrorMessage`가 서버 문구를 보인다(`로그인 시도가 너무 많아 계정이 잠겼습니다. N분 뒤에 다시 시도해 주세요.`). 서버가 `Retry-After`로 남은 분을 계산해 문구에 넣으므로 화면은 헤더를 읽지 않는다(D-17). 코드 변경 없음, 테스트만 보강(§7).

**C8 `pages/account-profile/presentation/ProfilePage.tsx`**
- `AccountLayout` 안(로그인 보장). `user = useAuth().state.user`.
- AppBar ← → `resolvePostLoginPath(user, readFrom(location.state))`(상점주는 들어온 상점주 화면 또는 `/owner/today`, 고객은 `/`, D-4). 제목 「프로필 변경」.
- `ProfileForm` 본문(와이어프레임 224~233줄): 「이메일 (변경 불가)」 `<input readOnly className="in ro" value={user.email}>` / 고객·관리자: 「이름」 `input.in`(`maxLength=100`, `autoComplete="name"`) / 상점주: 「상호 (변경 불가)」 `<input readOnly className="in ro" value={user.name ?? ''}>`(D-22, `// open-issues:` 주석) / 「전화번호」 `input.in`(`type="tel"`, `maxLength=100`) / 완료 `<div className="box done" role="status">저장했어요</div>`(D-11) / 오류 `err` / `btn pri dk` 「저장」. `.cta`: 「저장」.
- 폼 초기값 `profileFormOf(user)`. `canSaveProfile(user, form)`가 아니면 「저장」 비활성(`Input` README "바꾼 값이 없으면 저장 버튼 비활성"). 제출 → `submit(profilePatch(user, form))`.
- 저장 성공 → `replaceUser`로 `user`가 바뀌어 같은 값이 기준이 되므로 버튼이 다시 비활성. 완료 표시는 다음 입력에서 `reset()`으로 지운다. 이동하지 않는다(D-11, C-4).

| 상태 | 표시 |
| --- | --- |
| 가드 로딩·비로그인 | `AccountLayout`이 처리(§4) |
| 처음 | 현재 값, 「저장」 비활성 |
| 제출 중 | 「처리 중…」 + `aria-disabled` |
| 200 | `저장했어요`(role status), 버튼 비활성 |
| 400·403·네트워크 | `accountErrorMessage` |
| 401 | `session.clear()` → 가드가 `/login`(`from: /account/profile`)으로 보냄 |

**C9 `pages/account-password/presentation/PasswordChangePage.tsx`**
- `AccountLayout` 안. AppBar ←는 C8과 같은 규칙. 제목 「비밀번호 변경」.
- `PasswordChangeForm` 본문(와이어프레임 239~249줄): 「현재 비밀번호」(`type="password"`, `autoComplete="current-password"`, 아래 `current` 오류) / 「새 비밀번호 (8자 이상)」(`autoComplete="new-password"`, 아래 `passwordRuleMessage`) / 「새 비밀번호 확인」(`autoComplete="new-password"`, `isConfirmMismatch`면 아래 임시 문구) / `.m` 「바꿔도 이 기기는 로그인이 유지되고, 다른 기기에서는 로그아웃돼요.」(와이어프레임 문구) / 완료 `box done` `PASSWORD_CHANGED_NOTICE` / 폼 오류 / `btn pri dk` 「비밀번호 바꾸기」. `.cta`: 「비밀번호 바꾸기」.
- 성공 → 세 칸을 비우고 완료 표시. 세션·인증 상태는 그대로(D-9). 이동하지 않는다(D-12).

| 상태 | 표시 |
| --- | --- |
| 처음 | 빈 칸, 버튼 비활성 |
| 제출 중 | 「처리 중…」 + `aria-disabled` |
| 204 | 칸 비움, 완료 문구 |
| 400 `CURRENT_PASSWORD_MISMATCH` | 현재 비밀번호 칸 아래 `현재 비밀번호가 일치하지 않습니다.`, 입력값 유지 |
| 400 `VALIDATION_ERROR`·403·네트워크 | 폼 오류 자리에 `accountErrorMessage` |
| 401 | `session.clear()` → `/login`(`from: /account/password`) |

**O8 `widgets/owner-nav/presentation/OwnerAccountMenu.tsx` 수정**(D-23, 와이어프레임 276~291줄)
- `.list` 행 순서: `<Link className="li" to={ROUTES.accountProfile} state={{ from }}>`「내 정보 (전화번호)」 + `<span className="m">›</span>`, 같은 모양의 「비밀번호 변경」(`ROUTES.accountPassword`), 기존 `button.li` 「로그아웃」. `from = location.pathname + location.search + location.hash`(`useLocation`).
- 상점주일 때만 목록 아래 `.m` 「상점 정보·폐점은 매장 탭(O4)에 있어요.」(와이어프레임 문구, 관리자는 "상점 줄 없음"). C-11.
- 첫 포커스는 첫 행(「내 정보 (전화번호)」 링크). 링크를 누르면 라우트가 `/account/*`로 바뀌어 `OwnerLayout`과 함께 시트가 사라진다(별도 닫기 처리 없음).
- PC 드롭다운은 여전히 시트(`auth.md` D-3의 PC 부분은 유지, Q-9).

## 4. 라우트와 가드

| 화면 | 경로 | 레이아웃 | 접근 | 비고 |
| --- | --- | --- | --- | --- |
| A1 | `/login` (기존) | 없음 | 비로그인 전용(page 안 `Navigate`) | |
| A2 | `/signup`, `/signup?role=owner` | 없음 | 비로그인 전용(page 안 `Navigate`, D-5) | `role=owner`는 상점주 미리 선택(D-6) |
| A3 | `/password-reset` | 없음 | 비로그인 전용(D-5) | |
| C8 | `/account/profile` | `AccountLayout` | 로그인 필요, 역할 무관 | 상점주·고객·관리자 공용 |
| C9 | `/account/password` | `AccountLayout` | 로그인 필요, 역할 무관 | |
| `/account` | 리다이렉트 → `/account/profile` | | | `<Navigate replace>` |

**`app/layouts/AccountLayout.tsx`** (D-4): `decideAccess(useAuth().state, 'ANY')`.

| decision | 렌더 |
| --- | --- |
| `loading` | `<div className="app" aria-busy="true" />` |
| `allow` | `<Outlet />` (page가 `.app` 프레임을 그림. TabBar 없음: 하위 화면) |
| `login` | `<Navigate to={ROUTES.login} replace state={loginRedirectState('other', pathname+search+hash)} />` |
| `login-without-from` | `<Navigate to={ROUTES.login} replace />` |
| `error` | `OwnerLayout`과 같은 `err` + 「다시 시도」(`auth.md` D-9 임시 문구 재사용) |

- `OwnerLayout`과 달리 `allow`일 때 `.app`을 레이아웃이 아니라 page가 그린다: C8·C9는 고객 셸(420px 가운데)·상점주 셸 어느 쪽에서 와도 같은 하위 화면이다. 고객 셸이 생기면 그 셸의 프레임 규칙에 맞춰 이 레이아웃을 다시 본다(N 주석 M-6).
- `routes.tsx`: `{ path: ROUTES.signup, element: <SignupPage /> }`, `{ path: ROUTES.passwordReset, element: <PasswordResetPage /> }`, `{ path: ROUTES.account, element: <Navigate to={ROUTES.accountProfile} replace /> }`, `{ element: <AccountLayout />, children: [{ path: ROUTES.accountProfile, element: <ProfilePage /> }, { path: ROUTES.accountPassword, element: <PasswordChangePage /> }] }`. `*`보다 앞.
- 상점주·고객 모두 C8·C9 진입: 상점주는 O8 행, 고객은 이후 C6 행(`ROUTES.accountProfile`·`accountPassword`에 `state.from`)으로 같은 경로를 쓴다. 관리자는 관리자 셸의 O8에서 같은 경로.

## 5. 정합 이슈

| C | 내용 | 근거 | 처리 |
| --- | --- | --- | --- |
| C-1 | `api-client` §2.1 표 "비밀번호 변경·재설정 성공 → `session.clear()` 후 다시 로그인"과 화면·API 명세 "변경은 현재 토큰 유지(다시 로그인 안 함), 재설정만 모든 토큰 무효"가 다르다 | `frontend/.claude/skills/api-client/SKILL.md` §2.1 표 "비밀번호 변경·재설정 성공" 행 / `screens.md` C9 동작 메모, `reference/auth.md` §9, `router.py:117~125`(`keep_jti`) | **해소**: 화면·API 명세를 따른다(D-9 확정). 오케스트레이터가 `api-client` §2.1 표를 고쳤다(Q-4) |
| C-2 | `screens.md` A3·`open-issues.md` A3 "코드는 서버 로그로만, 메일 미발송(reset_notifier.py) → 확인 필요"는 낡았다. 명세는 SMTP 설정 시 메일 발송, 백엔드에 `SmtpPasswordResetNotifier`가 있다 | `screens.md` A3, `open-issues.md` A3 / `reference/auth.md` §10 "전달 방식", `backend/src/auth/infrastructure/reset_notifier.py:46` | 화면 동작은 같다(가입 여부와 무관한 같은 안내). 디자인 문서 갱신을 사용자에게 보고. 코드에는 `open-issues:` 주석을 남기되 문구는 open-issues 원문 기준(M-3) |
| C-3 | 서버 `message`와 화면 문구가 다르다: `CURRENT_PASSWORD_MISMATCH` 서버 `현재 비밀번호가 올바르지 않습니다.` ↔ 화면 `현재 비밀번호가 일치하지 않습니다.` / `INVALID_RESET_CODE` 서버 `재설정 코드가 올바르지 않거나 만료되었습니다.` ↔ 화면 `코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.` | `reference/auth.md` §9·§11, `auth/domain/exceptions.py:150~159` / `screens.md` C9·A3 | `errorCode`로 분기해 화면 문구를 쓴다(F11·F13, D-16). `EMAIL_DUPLICATED`는 같은 문구 |
| C-4 | C8 "저장 후 '저장했어요' 알림 + 이전 화면"인데 디자인 시스템에 알림(토스트) 컴포넌트·클래스가 없다. 이전 화면(상점주 자리 page 등)이 알림을 받아 그릴 방법도 없다 | `screens.md` C8 동작 메모 / `components/` 19종 목록, `bundle.css`(토스트 클래스 없음) | 같은 화면에 `box done`으로 표시하고 이동하지 않음(D-11). Q-5 |
| C-5 | `screens.md` C8 입력 라벨 「상점주로 열었을 때」는 와이어프레임의 설명 상자 제목이지 실제 라벨이 아니다. 상점주 상호 칸의 실제 라벨이 정본에 없다 | `screens.md` C8 입력 라벨 / `wireframe.html:230` | 「상호 (변경 불가)」(`Input` README "(변경 불가)" 규칙) 임시(D-22). Q-6 |
| C-6 | 와이어프레임 C8 안내 「상호 변경은 고객센터에 문의해 주세요.」는 `content.md` "할 수 없는 약속은 쓰지 않음"과 부딪칠 수 있다(고객센터 존재가 어느 정본에도 없음) | `wireframe.html:230` / `content.md` 오류·안내 4번째 줄 | 이번에는 넣지 않음(D-22). Q-6 |
| C-7 | O8 메뉴 행 이름: 와이어프레임 O8 「내 정보 (전화번호)」 ↔ `ListRow` README·C6 「프로필 변경」 | `wireframe.html:283` / `components/ListRow/README.md`, `wireframe.html:484` | O8에는 O8 와이어프레임 문구, C6(이후)에는 C6 문구(D-23) |
| C-8 | `api-client` §3 "429 `ACCOUNT_LOCKED`는 `Retry-After` 헤더를 필요한 화면에서 읽는다"인데 `ApiError`에는 헤더가 없고, 백엔드에 CORS 설정(`expose_headers`)이 없어 다른 출처 배포에서는 헤더를 읽을 수 없다. 서버 문구에 남은 분이 이미 들어 있다 | `api-client/SKILL.md` §3 마지막 줄, `src/shared/api/error.ts` / `error_handlers.py:33~35`, `exceptions.py:24~29`, `backend/src`에 `CORSMiddleware` 없음 | 서버 문구 사용(D-17). Q-9 |
| C-9 | 이름·전화번호가 빈 기존 회원은 변경 때 둘 다 채워야 하는데(REQ-23), 상점주는 상호 칸이 잠겨(`open-issues` C8) 이름이 빈 상점주는 C8에서 저장할 수 없다 | `requirements/auth.md` REQ-2·REQ-23, `reference/auth.md` §8 / `open-issues.md` C8 | `canSaveProfile`이 비활성으로 막는다. 안내 문구·해결책은 정본이 없어 Q-11 |
| C-10 | A2 연결 화면은 O0뿐(상점주 가입 → 승인 대기)이나 stores 영역이 없어 O0가 없다 | `screens.md` A2 / `auth.md` C-3·D-6 | 상점주는 `/owner/today`로(기존 `resolvePostLoginPath`, `auth.md` N-3 주석이 추적) |
| C-11 | 요청 범위를 넘은 추가: O8 상점주 전용 안내 한 줄(와이어프레임에 있음), `HttpAuthGateway`의 DTO 변환을 `userDto.ts`로 옮기는 리팩터(동작 불변), `AuthContextValue.replaceUser` 추가 | 요청서 범위 / `wireframe.html:286`, §2.4, D-13 | 사용자 확인(Q-15). 빼도 나머지 설계는 그대로 성립 |
| C-12 | `auth.md` D-3(O8 로그아웃 한 줄)·N-1·N-4가 이번 설계로 바뀐다 | `auth.md` §3.4·§8·§9 | 확정되면 이 문서 D-23·§9가 대체. `auth.md`에는 후속 문서 위치만 적는다 |

## 6. 골격 (`tdd-workflow` §3)

**그대로 만들 것**(타입·상수·포트·토큰·공개 API·wiring·경로 상수·라우트 배열)

| 파일 | 내용 |
| --- | --- |
| `shared/lib/routes.ts` | §2.1 상수 추가 |
| `features/auth/domain/passwordRule.ts` | 타입·상수 실제, `utf8ByteLength`·`checkPassword` 비움 |
| `features/auth/domain/signupInput.ts` | 타입·상수 실제, 함수 4개 비움 |
| `features/auth/domain/passwordReset.ts`, `profileInput.ts`, `passwordChange.ts` | 타입 실제, 함수 비움 |
| `features/auth/domain/accountMessages.ts` | 상수 12개 실제 값(§3.1 표), 함수 5개 비움 |
| `features/auth/domain/redirect.ts` | 타입 확장 실제, `readLoginNotice`·`isAccountPath` 비움. `resolvePostLoginPath` 기존 본문 유지(Green에서 규칙 추가) |
| `features/auth/domain/authState.ts` | `decideAccess` 인자 타입만 `Role \| 'ANY'`로. 본문 그대로(Green에서 `'ANY'` 분기) |
| `features/auth/application/ports.ts`, `tokens.ts` | `AccountGateway`, `AccountGatewayToken` 실제 |
| `features/auth/application/authContext.ts` | `replaceUser` 타입 추가 |
| `features/auth/wiring.ts`, `index.ts` | §2.6·§2.7 그대로 |
| `pages/*/index.ts` 4개 | 공개 API |
| `app/router/routes.tsx` | §4 라우트 추가(요소 연결 포함) |

**본문을 비울 것**(`void <인자>; throw new Error('not implemented: <이름>')` 또는 `return null`)

| 파일 | export |
| --- | --- |
| `application/signup.ts`, `passwordReset.ts`, `updateProfile.ts`, `changePassword.ts` | 유스케이스 |
| `application/useSubmit.ts`, `useSignup.ts`, `usePasswordReset.ts`, `useUpdateProfile.ts`, `useChangePassword.ts` | 훅 |
| `application/useAuthController.ts` | `replaceUser`만 `void user; throw new Error('not implemented: replaceUser')`인 콜백으로 추가(기존 동작 유지) |
| `infrastructure/httpAccountGateway.ts` | 클래스(메서드 본문 비움) |
| `infrastructure/userDto.ts` | `toUser`는 기존 `httpAuthGateway.ts` 코드를 그대로 옮긴 실제 구현(동작 불변 이동, 기존 테스트로 보호) |
| `presentation/SignupRolePicker.tsx`, `SignupForm.tsx`, `PasswordResetForm.tsx`, `ProfileForm.tsx`, `PasswordChangeForm.tsx` | `return null` |
| `pages/signup/presentation/SignupPage.tsx`, `pages/password-reset/…/PasswordResetPage.tsx`, `pages/account-profile/…/ProfilePage.tsx`, `pages/account-password/…/PasswordChangePage.tsx` | `return null` |
| `app/layouts/AccountLayout.tsx` | `return null` |

**골격 단계에서 건드리지 않는 기존 파일**(기존 테스트 유지): `pages/login/presentation/LoginPage.tsx`, `widgets/owner-nav/presentation/OwnerAccountMenu.tsx`, `features/auth/domain/loginMessage.ts`. Green에서 바꾼다.

신규 약 27개(domain 5, application 9, infrastructure 2, presentation 5, pages 8(page 4 + index 4), app 1) + 수정 약 9개(`routes.ts`, `redirect.ts`, `authState.ts`, `ports.ts`, `tokens.ts`, `authContext.ts`, `useAuthController.ts`, `httpAuthGateway.ts`, `wiring.ts`, `index.ts`, `routes.tsx`).

## 7. 테스트 목록 (`tdd-workflow` §2, 위치 `tests/` 아래)

공통 준비(`fe-qa` Red 단계에서 만듦)
- `tests/features/auth/fakes/fakeAccountGateway.fake.ts`: `signup`·`requestPasswordReset`·`confirmPasswordReset`·`updateProfile`·`changePassword`가 `vi.fn`(기본 resolve, `updateProfile`은 인자를 반영한 `User`).
- `tests/support/authFakes.ts`: `AuthFakes`에 `account: FakeAccountGateway` 추가, `createAuthContainer`가 `AccountGatewayToken`도 등록(기존 호출은 그대로 동작).
- 사용자 고정값은 기존 `tests/features/auth/fakes/users.ts`(`ownerUser`, `customerUser`, `adminUser`) + 필요 시 `legacyCustomerUser`(`name: null`).
- 오류는 `new ApiError(status, errorCode, message)`.

### (a) domain

**`tests/features/auth/domain/passwordRule.test.ts` — 18**

| 입력 | 기대 |
| --- | --- |
| `checkPassword('')` | `'empty'` |
| `'   '`(3칸) | `'blank'`(공백 검사가 길이보다 먼저) |
| `'        '`(8칸) | `'blank'` |
| `'1234567'` | `'tooShort'` |
| `'12345678'` | `'ok'` |
| `' abcdefg'`(공백 포함 8자) | `'ok'`(trim하지 않음) |
| `'a'.repeat(72)` | `'ok'` |
| `'a'.repeat(73)` | `'tooLong'` |
| `'가'.repeat(24)`(72바이트) | `'ok'` |
| `'가'.repeat(25)`(75바이트) | `'tooLong'` |
| `'😀'.repeat(7)`(코드 포인트 7, UTF-16 14) | `'tooShort'` |
| `'😀'.repeat(18)`(72바이트) | `'ok'` |
| `'😀'.repeat(19)`(76바이트) | `'tooLong'` |
| `utf8ByteLength`: `''`·`'a'`·`'é'`·`'가'`·`'😀'` | 0·1·2·3·4 (5케이스) |

**`tests/features/auth/domain/signupInput.test.ts` — 20**
- `readSignupRole`: `'?role=owner'` → OWNER / `''` → CUSTOMER / `'?role=OWNER'` → CUSTOMER / `'?role=admin'` → CUSTOMER / `'?role=customer'` → CUSTOMER / `'?x=1&role=owner'` → OWNER (6)
- `canSubmitSignup`(기준: 모두 유효한 고객 폼): 기준 true / OWNER 기준 true / 이름 `''` false / 이름 `'  '` false / 이메일 `' '` false / 전화 `''` false / 비밀번호 7자 false / 비밀번호 공백 8칸 false / 비밀번호 73바이트 false (9)
- `toSignupInput`: `' 홍길동 '`·`' a@b.c '`·`' 010 '` → 앞뒤 공백 제거 / 비밀번호 `' pw123456 '` 그대로 / `role` 그대로 (3)
- `nameLabel`: CUSTOMER `이름 *` / OWNER `상호(상점명으로 쓰임) *` (2)

**`tests/features/auth/domain/passwordReset.test.ts` — 12**
- `isResetCode`: `'123456'` true / `'000000'` true / `'12345'` false / `'1234567'` false / `'12a456'` false / `''` false / `' 123456'` false / `'１２３４５６'`(전각) false (8)
- `canRequestReset`: `'a@b.c'` true / `'  '` false (2)
- `canConfirmReset`: 코드 보냄·6자리·`'ok'` 비밀번호 true / `codeSent: false`면 false (2)

**`tests/features/auth/domain/profileInput.test.ts` — 15**
- `isNameLocked`: OWNER true / CUSTOMER false / ADMIN false (3)
- `profileFormOf`: `name: null` → `''` (1)
- `profilePatch`(고객 `{name:'김고객', phone:'010-1'}`): 그대로 → `{}` / 전화 변경 → `{ phone }`만 / 이름 변경 → `{ name }`만 / 둘 다 → 둘 다 / `' 010-1 '` → `{}`(trim 뒤 같음) / 상점주 이름 변경 → `{}`(잠김) / 상점주 전화 변경 → `{ phone }`만 (7)
- `canSaveProfile`: `{}` false / 전화를 `'  '`로 → false / 전화 변경 → true / 이름이 `null`인 고객이 전화만 변경 → false(REQ-23) / 같은 경우 ADMIN → true (5)

(이름 101자는 입력 칸 `maxLength`로 막으므로 domain 경계값에서 뺀다.)

**`tests/features/auth/domain/passwordChange.test.ts` — 8**
- `isConfirmMismatch`: `('abcdefgh','')` false / `('abcdefgh','abcdefgx')` true / `('abcdefgh','abcdefgh')` false (3)
- `canSubmitPasswordChange`: 유효 true / 현재 `''` false / 새 비밀번호 7자 false / 확인 다름 false / 확인 `''` false (5)

**`tests/features/auth/domain/accountMessages.test.ts` — 15**
- `signupErrorView`: `EMAIL_DUPLICATED`+임의 서버 문구 → `{email, '이미 가입된 이메일입니다.'}` / `VALIDATION_ERROR`+`'이메일 형식이 올바르지 않습니다.'` → `{form, 그 문구}` / `NETWORK_ERROR` → `{form, 그 문구}` / `message: ''` → `{form, ACCOUNT_FALLBACK_MESSAGE}` (4)
- `resetConfirmErrorMessage`: `INVALID_RESET_CODE`+서버 문구 `'재설정 코드가 올바르지 않거나 만료되었습니다.'` → 정확히 `코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.` / `VALIDATION_ERROR` → 서버 문구 / `''` → 기본 문구 (3)
- `changePasswordErrorView`: `CURRENT_PASSWORD_MISMATCH`+`'현재 비밀번호가 올바르지 않습니다.'` → `{current, '현재 비밀번호가 일치하지 않습니다.'}` / `VALIDATION_ERROR` → `{form, 서버 문구}` / 403 `FORBIDDEN` `'정지된 계정입니다.'` → `{form, 그 문구}` (3)
- `passwordRuleMessage`: `'blank'` → 임시 문구 / `'tooLong'` → 임시 문구 / `'tooShort'`·`'empty'`·`'ok'` → `null` (5)

**`tests/features/auth/domain/redirect.test.ts` 추가 — 12**
- `readLoginNotice`: `{notice:'passwordReset'}` → `'passwordReset'` / `{notice:'signupLoginFailed'}` → 그 값 / `{notice:'x'}` → `null` / `null` → `null` / `{from:'/'}` → `null` (5)
- `isAccountPath`: `/account/profile` true / `/account` true / `/accountx` false (3)
- `resolvePostLoginPath`: OWNER + `/account/password` → 그대로 / CUSTOMER + `/account/profile` → 그대로 / ADMIN + `/account/profile` → 그대로 (3)
- `readFrom({ from: '/owner/offers', notice: 'passwordReset' })` → `'/owner/offers'` (1)

**`tests/features/auth/domain/authState.test.ts` 추가 — 7**: `decideAccess(state, 'ANY')`: loading → `'loading'` / anonymous other → `'login'` / anonymous loggedOut → `'login-without-from'` / error → `'error'` / OWNER·CUSTOMER·ADMIN authenticated → 모두 `'allow'`(3).

### (b) application (가짜 포트, React 없음)

**`signup.test.ts` — 5**: 성공 → `account.signup`이 정리된 입력(`trim`, 역할 포함)으로 호출되고 그 뒤 `login(정리된 email, password)` 호출(순서), `{kind:'loggedIn', user}` / `signup` 409 → 같은 `ApiError`로 reject, `login` 미호출 / `signup` 성공 + `login` reject(네트워크) → `{kind:'loginFailed'}`로 resolve / `signup` 400 → reject / OWNER 폼 → `role: 'OWNER'` 전달.

**`passwordReset.test.ts` — 6**: `requestPasswordReset(' a@b.c ')` → `account.requestPasswordReset('a@b.c')` / 요청 실패 전파 / `confirmPasswordReset` 성공 → `account.confirmPasswordReset({email, code, newPassword})` 뒤 `session.clear()`(순서) / `INVALID_RESET_CODE` reject → `clear` 미호출, 같은 오류 reject / `VALIDATION_ERROR` → `clear` 미호출 / 호출은 각 1회.

**`updateProfile.test.ts` — 4**: 성공 → `account.updateProfile({phone:'010-2'})`, 반환 `User` / 401 `TOKEN_REVOKED` → `session.clear` 후 reject / 403 → reject, `clear` 미호출 / 400 → reject, `clear` 미호출.

**`changePassword.test.ts` — 4**: 성공 → `account.changePassword({currentPassword, newPassword})`, **`session.clear` 미호출** / 401 → `clear` 후 reject / `CURRENT_PASSWORD_MISMATCH` → reject, `clear` 미호출 / 403 → reject, `clear` 미호출.

**훅 (`renderHook` + `DepsProvider` 가짜 컨테이너 + `AuthProvider`)**
- `useSubmit.test.tsx` — 6: 처음 `{pending:false,error:null,done:false}` / `submit` 중 `pending:true` → 성공 `done:true`·결과 반환 / 실패 → `error`가 `ErrorInfo`(`status`·`errorCode`·`message`), 반환 `undefined` / `pending` 동안 두 번째 `submit`은 `run` 미호출 / 언마운트 뒤 resolve돼도 상태 갱신 경고 없음, 넘긴 `signal.aborted === true` / `reset()` → 처음 상태.
- `useSignup.test.tsx` — 4: 성공 → `fakes.auth.login` 호출, 인증 상태 `authenticated`, 반환 `{kind:'loggedIn'}` / 409 → `error.errorCode === 'EMAIL_DUPLICATED'`, 상태 anonymous / 로그인 실패 → 반환 `{kind:'loginFailed'}`, `error` 없음 / 제출 중 `pending`.
- `usePasswordReset.test.tsx` — 7: 처음 `sentEmail === null` / `request(' a@b.c ')` 성공 → `sentEmail === 'a@b.c'` / 요청 실패 → `requestError`, `sentEmail` 그대로 `null` / `resend()` → 같은 이메일로 다시 호출 / `confirm('123456','pw123456')` 성공 → `true`, `session.clear` 호출 / `INVALID_RESET_CODE` → `false`, `confirmError` / `invalidate()` → `sentEmail === null`, `confirmError === null`.
- `useUpdateProfile.test.tsx` — 4: 성공 → `useAuth().state.user`가 응답 `User`로 바뀜(`replaceUser`), `done:true`, 인증 상태가 `loading`을 거치지 않음 / 401 → 상태 `anonymous`(구독으로) / 400 → `error` / 제출 중 `pending`.
- `useChangePassword.test.tsx` — 4: 성공 → `true`, `done:true`, 인증 상태·`session.clear` 그대로 / `CURRENT_PASSWORD_MISMATCH` → `false`, `error` / 401 → `anonymous` / `pending`.
- `useAuthController.test.tsx` 추가 — 2: 인증 상태에서 `replaceUser(u2)` → `{authenticated, user: u2}` / anonymous에서 `replaceUser` → 상태 그대로.

### (c) infrastructure

**`tests/features/auth/infrastructure/httpAccountGateway.test.ts` — 11** (`vi.mock('@/shared/api/client')`)
- `signup`: `/v1/auth/signup`에 `{email,password,name,phone,role}` POST, `auth:false`, 반환 `undefined` / 409 `ApiError` 전파
- `requestPasswordReset`: `/v1/auth/password-reset/request`에 `{email}` POST, `auth:false`
- `confirmPasswordReset`: `/v1/auth/password-reset/confirm`에 `{email, code, new_password}` POST, `auth:false`(필드명 snake_case)
- `updateProfile`: `PATCH /v1/users/me` 본문이 정확히 `{phone:'010-2'}`(키 `name` 없음) / `{name, phone}` 둘 다 / 응답 DTO → `User`(`point`=`users_point`, `createdAt` `Date`) / `role:'WEIRD'` → reject
- `changePassword`: `/v1/users/me/password`에 `{current_password, new_password}` POST, `auth` 옵션 없음(토큰 붙음)
- `signal` 전달(5메서드 묶음 1)
- 기존 `httpAuthGateway.test.ts` 9개는 그대로 통과해야 한다(`userDto.ts` 이동 회귀).

### (d) presentation·pages

**`tests/pages/signup/SignupPage.test.tsx` — 17** (`renderRoutesWithAuth`, 라우트: `/signup`, `/login`, `/owner/today`, `/`, `/offers/1` 자리)
1. 제목 heading 「회원가입」, ← 링크(이름 「뒤로」) `href="/login"`
2. 라벨 「어떻게 이용하시나요? *」「이름 *」「이메일 *」「비밀번호 * (8자 이상)」「전화번호 *」, 역할 radio 「일반 고객」 `aria-checked="true"`, 「상점주」 false
3. 안내 「한 계정은 한 가지 유형이에요. 상점주는 관리자 승인 후 상점을 열 수 있어요.」
4. `/signup?role=owner` → 「상점주」 checked, 라벨 「상호(상점명으로 쓰임) *」
5. 「상점주」를 누르면 라벨이 바뀌고 다시 「일반 고객」을 누르면 「이름 *」
6. 「가입하기」 버튼이 2개(`.cta` 안, `.dk`)이고 처음 둘 다 `aria-disabled="true"`
7. 모두 입력하면 둘 다 활성 / 비밀번호 7자면 비활성
8. 비밀번호 공백 8칸 → 비밀번호 칸 아래 `PASSWORD_BLANK_MESSAGE`, 비활성
9. `maxLength`: 이름·전화 100, 이메일 255
10. 제출 → `account.signup`이 `{email:'a@b.c', password:'pw123456', name:'홍길동', phone:'010-1', role:'CUSTOMER'}`(앞뒤 공백 제거)로 1회, 이어서 `auth.login('a@b.c','pw123456')`
11. OWNER 가입(`role=owner`) + 로그인 결과 OWNER → URL `/owner/today`, `signup` 인자 `role:'OWNER'`
12. `location.state = {from:'/offers/1'}`로 진입, CUSTOMER 가입 → `/offers/1`
13. 409 → 이메일 칸 아래(이메일 input과 같은 묶음) `이미 가입된 이메일입니다.` alert, 입력값 유지, URL `/signup`
14. 400 `VALIDATION_ERROR` `'이메일 형식이 올바르지 않습니다.'` → 폼 오류 자리에 그 문구
15. 가입 성공 + 로그인 실패(`NETWORK_ERROR`) → URL `/login`, A1에 `SIGNUP_LOGIN_FAILED_NOTICE`(role status), `from` 유지
16. 제출 중 「처리 중…」 + `aria-disabled`, 연타해도 `signup` 1회
17. 이미 로그인한 OWNER가 `/signup` → `/owner/today` / 세션 확인 중 → `aria-busy` 프레임만

**`tests/pages/password-reset/PasswordResetPage.test.tsx` — 15**
1. 제목 「비밀번호 재설정」, ← `href="/login"`
2. 처음: 「1단계 · 코드 받기」「가입한 이메일」, 「코드 보내기」, 안내 「가입된 이메일이면 6자리 코드를 보내요.」, 「2단계 · 새 비밀번호」 없음, 「비밀번호 바꾸기」(2개) 비활성
3. 이메일이 비면 「코드 보내기」 비활성
4. 「코드 보내기」 → `account.requestPasswordReset('a@b.c')`, 2단계(「6자리 코드」「새 비밀번호 (8자 이상)」, 「코드 다시 받기」)가 나타남
5. 코드 칸: 클래스 `in code`, `inputMode="numeric"`, `maxLength=6`, `autoComplete="one-time-code"`
6. 코드 6자리 + 비밀번호 8자 → 「비밀번호 바꾸기」 활성 / 코드 5자리면 비활성
7. 제출 → `account.confirmPasswordReset({email:'a@b.c', code:'123456', newPassword:'pw123456'})`, `session.clear` 1회, URL `/login`, A1에 `새 비밀번호로 로그인하세요`(role status)
8. `location.state = {from:'/owner/offers'}`로 진입해 완료 → A1의 `location.state.from === '/owner/offers'`
9. `INVALID_RESET_CODE` → `코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.` alert, 코드·비밀번호 값 유지, URL 그대로
10. `VALIDATION_ERROR` 서버 문구 표시
11. 「코드 다시 받기」 → `requestPasswordReset`이 같은 이메일로 2번째 호출
12. 코드를 보낸 뒤 이메일 칸을 고치면 2단계가 사라지고, 다시 보내면 코드 칸이 비어 있음
13. 코드 요청 `NETWORK_ERROR` → 1단계 상자 안에 그 문구, 2단계 없음
14. 요청 중 「코드 보내기」 → 「처리 중…」, 확인 중 「비밀번호 바꾸기」 → 「처리 중…」, 연타해도 각 1회
15. 이미 로그인한 CUSTOMER가 `/password-reset` → `/`

**`tests/pages/account-profile/ProfilePage.test.tsx` — 14** (`renderRoutesWithAuth` + 전체 `routes`, `signedInFakes`)
1. CUSTOMER: 제목 「프로필 변경」, 「이메일 (변경 불가)」 칸이 `readOnly`이고 클래스 `in ro`, 값 이메일
2. 「이름」「전화번호」에 현재 값, 「저장」(2개) 비활성
3. 전화 변경 → 활성 → 제출 → `account.updateProfile({phone:'010-2'})` 정확히 1회(키 `name` 없음)
4. 성공 → `저장했어요`(role status), 「저장」 다시 비활성, URL 그대로 `/account/profile`
5. 성공 뒤 같은 트리 안의 `useAuth` 소비자(테스트용 프로브)가 새 `phone`을 본다
6. OWNER: 「상호 (변경 불가)」 칸 `readOnly`·`in ro`, 「이름」 입력 칸 없음, 전화 변경 제출 시 인자에 `name` 없음
7. ← 링크: OWNER가 `state.from='/owner/offers'`로 진입 → `href="/owner/offers"` / `from` 없으면 `/owner/today` / CUSTOMER `from` 없으면 `/`
8. 전화를 공백으로 지우면 비활성
9. 이름이 `null`인 CUSTOMER가 전화만 바꾸면 비활성(REQ-23)
10. ADMIN: 「이름」 편집 가능(잠금 없음)
11. 400 → 서버 문구 표시
12. 401 `TOKEN_REVOKED` → `session.clear` 호출, URL `/login`, `location.state.from === '/account/profile'`
13. 403 `정지된 계정입니다.` → 그 문구
14. 제출 중 「처리 중…」·연타 1회. 완료 표시는 다시 입력하면 사라짐

**`tests/pages/account-password/PasswordChangePage.test.tsx` — 13**
1. 제목 「비밀번호 변경」, 라벨 3개, 안내 「바꿔도 이 기기는 로그인이 유지되고, 다른 기기에서는 로그아웃돼요.」
2. 처음 「비밀번호 바꾸기」(2개) 비활성
3. 확인이 다르면 확인 칸 아래 `PASSWORD_CONFIRM_MISMATCH_MESSAGE`, 비활성
4. 새 비밀번호 73바이트 → `PASSWORD_TOO_LONG_MESSAGE`
5. 유효 → 활성 → 제출 → `account.changePassword({currentPassword:'old12345', newPassword:'new12345'})`
6. 성공 → 세 칸이 빈 값, `PASSWORD_CHANGED_NOTICE`(role status), `session.clear` 미호출, 인증 상태 유지, URL 그대로
7. `CURRENT_PASSWORD_MISMATCH` → 현재 비밀번호 칸 아래 `현재 비밀번호가 일치하지 않습니다.`, 입력값 유지
8. `VALIDATION_ERROR` → 서버 문구
9. 401 → `session.clear`, `/login` + `from: '/account/password'`
10. 제출 중 「처리 중…」·연타 1회
11. 비밀번호 칸 `autoComplete`: `current-password`, `new-password`, `new-password`
12. ← 링크 규칙(C8과 같음, OWNER `from` 없음 → `/owner/today`)
13. 403 → 서버 문구

**`tests/app/layouts/AccountLayout.test.tsx` — 8**: 세션 확인 중 → `aria-busy`, Outlet 없음 / anonymous → `/login`, `state.from === '/account/profile'` / 쿼리 포함 경로 → `from`에 쿼리 포함 / loggedOut → `/login`, state `null` / OWNER·CUSTOMER·ADMIN → Outlet 본문 보임(각 역할 1케이스, 3) / error → `err` + 「다시 시도」 → 재시도 성공 후 본문.

**`tests/widgets/owner-nav/presentation/OwnerAccountMenu.test.tsx` 추가 — 6** (`renderRoutesWithAuth`로 라우터 안에 렌더)
1. 메뉴 행 순서: 「내 정보 (전화번호)」, 「비밀번호 변경」, 「로그아웃」
2. 「내 정보 (전화번호)」 링크 `href="/account/profile"`, 「비밀번호 변경」 `href="/account/password"`
3. `/owner/offers?x=1`에서 「내 정보 (전화번호)」를 누르면 URL `/account/profile`, `location.state.from === '/owner/offers?x=1'`, 시트 없음
4. OWNER면 「상점 정보·폐점은 매장 탭(O4)에 있어요.」가 있다 / ADMIN이면 없다(2케이스 묶음 1)
5. 열면 포커스가 「내 정보 (전화번호)」 링크
6. 시트 안 Tab 순환이 링크 2개 + 로그아웃 버튼 사이에서 돈다

**`tests/pages/login/LoginPage.test.tsx` 변경·추가 — 기존 1개 교체 + 6 추가**
- 교체: 「회원가입·비밀번호 재설정·입점 신청 자리가 있고 눌러도 URL이 바뀌지 않는다」 → 「회원가입」 링크 `href="/signup"`, 「비밀번호 재설정」 `href="/password-reset"`, 「사장님이신가요? 입점 신청」 `href="/signup?role=owner"`, 「계정이 없나요?」 문구 유지(설계 변경에 따른 교체이므로 `tdd-workflow` §5의 테스트 변경이 아니라 Red 단계 범위)
- 추가: `state.from='/owner/offers'`로 진입 → 「회원가입」 클릭 → A2의 `location.state.from === '/owner/offers'` / 같은 조건으로 「비밀번호 재설정」 클릭 → A3 state 유지 / `notice:'passwordReset'` → `새 비밀번호로 로그인하세요`(role status) / `notice:'signupLoginFailed'` → `SIGNUP_LOGIN_FAILED_NOTICE` / notice 없음 → role status 없음 / 429 `ACCOUNT_LOCKED` 서버 문구 `'로그인 시도가 너무 많아 계정이 잠겼습니다. 9분 뒤에 다시 시도해 주세요.'`가 글자 그대로 보이고 「로그인」 다시 활성(입력 유지)

**`tests/app/router/routes.test.tsx` 추가 — 7**: `/signup` anonymous → heading 「회원가입」 / `/password-reset` → 「비밀번호 재설정」 / `/account/profile` anonymous → `/login` / `/account/profile` OWNER → 「프로필 변경」 / `/account/password` CUSTOMER → 「비밀번호 변경」 / `/account` → `/account/profile` / `/signup` OWNER 인증 → `/owner/today`.

**`tests/app/container.test.ts`**: 토큰 목록에 `AccountGatewayToken` 추가(같은 커밋, `layer-architecture` §6.7).

### (e) E2E — `e2e/account.spec.ts` 신규 9 (백엔드 응답은 `page.route`)

`e2e/support/auth.ts`의 `mockOwnerSession`은 `**/v1/users/me`를 메서드 구분 없이 받으므로, C8 테스트는 `route.request().method()`로 GET·PATCH를 나누는 별도 헬퍼(`mockOwnerSessionWithProfile`)를 support에 추가한다.
1. A1 「회원가입」 → A2(고객) 입력 → `POST /v1/auth/signup` 201 + 로그인 200 + `/v1/users/me` CUSTOMER → `/`(「마감 직전」). 가입 요청 본문 `role: 'CUSTOMER'`
2. A1 「사장님이신가요? 입점 신청」 → A2 「상점주」 선택됨·라벨 「상호(상점명으로 쓰임) *」 → 가입(본문 `role: 'OWNER'`) → `/owner/today`
3. A2 409 → 「이미 가입된 이메일입니다.」, URL `/signup`
4. A1 「비밀번호 재설정」 → 코드 보내기(204) → 코드·새 비밀번호 → 확인 204 → `/login` + 「새 비밀번호로 로그인하세요」, `localStorage` 토큰 없음
5. A3 확인 400 `INVALID_RESET_CODE` → 화면 문구
6. 상점주 O1 → 「계정」 → 「내 정보 (전화번호)」 → C8: 상호 잠김, 전화 변경 → PATCH 본문 `{phone}`만 → 「저장했어요」 → ← → `/owner/today`
7. O8 → 「비밀번호 변경」 → C9 → 204 → 완료 문구, `localStorage` 토큰 그대로, URL `/account/password`
8. A1 429 `ACCOUNT_LOCKED`(+ `Retry-After: 540`) → 서버 문구 그대로
9. `mobile`·`desktop` 두 프로젝트에서 C8의 「저장」이 각각 `.cta` 안 / `.dk` 버튼으로 하나씩만 보인다(720px 전환)

### 테스트 수 합계

domain 107(passwordRule 18, signupInput 20, passwordReset 12, profileInput 15, passwordChange 8, accountMessages 15, redirect 추가 12, authState 추가 7), application 46(유스케이스 19, 훅 27), infrastructure 11, presentation 87(SignupPage 17, PasswordResetPage 15, ProfilePage 14, PasswordChangePage 13, AccountLayout 8, OwnerAccountMenu 추가 6, LoginPage 교체 1 + 추가 6, routes 추가 7). 신규·추가 단위·컴포넌트 **약 251개**, E2E 신규 9개. 기존 테스트 변경: `LoginPage.test.tsx` 1개 교체, `tests/support/authFakes.ts`·`container.test.ts` 확장.

## 8. 남길 작업 주석 (`code-annotations`, F19)

**이번에 지운다·고친다**(구현 커밋에서)

| 위치 | 주석 | 처리 |
| --- | --- | --- |
| `src/pages/login/presentation/LoginPage.tsx:5~7` | TODO 「회원가입」·「비밀번호 재설정」·「입점 신청」이 이동하지 않음(`auth.md` N-1) | 링크 연결로 삭제 |
| `src/widgets/owner-nav/presentation/OwnerAccountMenu.tsx:4~6` | TODO C8·C9 행 없음 + PC 드롭다운(`auth.md` N-4) | C8·C9 부분을 지우고 PC 드롭다운만 남게 고침(M-5) |
| `src/features/auth/application/useAuthController.ts` | FIXME 다른 영역 401 미처리(`auth.md` N-5) | **그대로 둔다.** C8·C9는 유스케이스가 직접 `clear()`하지만 다른 영역 훅은 여전히 없다. `왜:`에 "auth-account.md D-18: C8·C9는 처리함"을 덧붙인다 |

**새로 남긴다**

| ID | 위치 | 태그 | 원문 초안 |
| --- | --- | --- | --- |
| M-1 | `features/auth/domain/accountMessages.ts` 임시 상수 위 | TODO | `// TODO: 임시 문구다(비밀번호 변경 완료, 비밀번호 공백·길이 초과, 확인 불일치, 가입 뒤 로그인 실패, 계정 처리 기본 문구, 「뒤로」). 정본 문구가 정해지면 바꾼다.`<br>`//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/auth-account.md D-12, D-14, D-20, D-25)`<br>`//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)` |
| M-2 | `features/auth/presentation/ProfileForm.tsx` 상호 칸 | open-issues | `// open-issues: C8 상점주 상호 칸 잠금, 전화번호만 수정` |
| M-3 | `features/auth/presentation/PasswordResetForm.tsx` | open-issues | `// open-issues: A3 메일 발송 확인 필요 (화면은 가입 여부와 무관하게 같은 안내만 보임)` |
| M-4 | `features/auth/presentation/ProfileForm.tsx` 완료 표시 | TODO | `// TODO: 저장 뒤 「저장했어요」를 같은 화면에 표시하고 이전 화면으로 돌아가지 않는다.`<br>`//   왜: 디자인 시스템에 알림(토스트) 컴포넌트가 없어 이전 화면에 알림을 띄울 수 없다 (auth-account.md C-4, D-11)`<br>`//   언제: 결정 후 (디자인 시스템: 알림 컴포넌트)` |
| M-5 | `widgets/owner-nav/presentation/OwnerAccountMenu.tsx`(기존 TODO 고침) | TODO | `// TODO: PC에서도 드롭다운 대신 시트를 쓴다.`<br>`//   왜: 드롭다운 컴포넌트가 디자인 시스템에 없다 (docs/design/frontend/auth.md D-3)`<br>`//   언제: 결정 후 (사용자: PC 드롭다운)` |
| M-6 | `app/layouts/AccountLayout.tsx` | TODO | `// TODO: C8·C9 프레임을 고객 셸(PC 420px 가운데) 규칙과 맞춘다.`<br>`//   왜: 고객 셸이 아직 없어 역할 무관 하위 화면으로만 둔다 (auth-account.md D-4)`<br>`//   언제: 고객 셸 구현 시` |
| M-7 | `pages/signup/presentation/SignupPage.tsx` | TODO | `// TODO: C2에서 가입하러 왔을 때 같은 수량으로 예약을 이어가지 않는다(원래 화면으로만 돌아간다).`<br>`//   왜: 고객 흐름(C2)이 없다 (screens.md A2 동작 메모)`<br>`//   언제: C2 구현 시` |
| M-8 | `features/auth/presentation/PasswordResetForm.tsx` 「코드 다시 받기」 | TODO | `// TODO: 60초 안에 다시 받으면 서버가 새 코드를 만들지 않는데 화면은 알려 주지 않는다.`<br>`//   왜: 재요청 간격 안내 문구가 정본에 없다 (reference/auth.md §10, auth-account.md D-24)`<br>`//   언제: 결정 후 (사용자: 재요청 간격 안내)` |

`FIXME`는 새로 만들지 않는다. 기존 FIXME(`auth.md` N-5·N-6)는 그대로 배포 전 0건 대상이다.

## 9. 결정 표

D-1~D-30은 사용자 위임으로 추천안대로 확정됐다(2026-11-10). 구현을 막는 항목은 없다. 문구 값 중 "임시"로 표시한 것(§3.1)은 확정된 임시값이며 content.md가 정해지면 바꾼다(M-1).

| D | 항목 | 값 | 상태 | 근거 | 구현을 막는가 |
| --- | --- | --- | --- | --- | --- |
| D-1 | 문서 배치 | 새 파일 `auth-account.md`(같은 slice `features/auth`), `auth.md`는 가리키기만 | 확정(위임, 2026-11-10) | `auth.md`가 1차 구현 반영본(436줄). 정본 하나 원칙: 겹치는 내용 없이 추가분만 | 아니오 |
| D-2 | 이번 범위 | A2(고객·상점주), A3, C8, C9, O8 C8·C9 행, A1 링크·안내·429. 제외: C6, C7, C11, 고객 셸, 관리자 셸 | 확정(위임, 2026-11-10) | C6·C7·C11은 고객 셸·고객 가드가 먼저 필요. C7은 C6에서만 들어감(`screens.md` C6·C7), O8 상점주 탈퇴는 `open-issues` O8로 없음 | 아니오(확정, Q-1) |
| D-3 | 경로 | `/signup`, `/signup?role=owner`, `/password-reset`, `/account/profile`, `/account/password`, `/account` → `/account/profile` | 확정(위임, 2026-11-10) | 뜻으로 짓기, 역할 무관 공용 화면 | 아니오(확정, Q-3) |
| D-4 | C8·C9 가드 | 역할 무관 `app/layouts/AccountLayout`(`decideAccess(state,'ANY')`), TabBar 없음, ← 는 `resolvePostLoginPath(user, from)` | 확정(위임, 2026-11-10) | 화면 명세상 고객·상점주·관리자 공용(`screens.md` C8·C9). 셸마다 같은 page를 두 번 등록하지 않음 | 아니오(확정, Q-3) |
| D-5 | 비로그인 전용(A2·A3) | A1과 같이 page 안에서 `authenticated` → `Navigate(resolvePostLoginPath)`, `loading` → 빈 프레임 | 확정(위임, 2026-11-10) | 기존 A1 방식과 일관. 새 레이아웃 없이 가입 직후 로그인 이동도 같은 한 곳에서 처리 | 아니오 |
| D-6 | 상점주 가입 진입 | 쿼리 `?role=owner`로 미리 선택. 화면에서 다시 바꿀 수 있음 | 확정(위임, 2026-11-10) | 이후 C1 「입점 신청」(`wireframe.html:323`)도 같은 주소. 새로고침·공유해도 유지 | 아니오(Q-7) |
| D-7 | A1 ↔ A2·A3 `from` 전달 | 링크 `state={{from}}`로 넘기고 A2·A3 ←·완료 이동도 `from`을 유지 | 확정(위임, 2026-11-10) | `screens.md` A2 "가입 후 이동은 A1과 같음"(원래 화면으로), `auth.md` D-1(`location.state`) | 아니오 |
| D-8 | 포트 | 새 `AccountGateway`(application 포트) + `AccountGatewayToken` + `HttpAccountGateway`, `wireAuth` 한 줄 추가. `AuthGateway`는 그대로 | 확정(위임, 2026-11-10) | 기존 가짜(`FakeAuthGateway`)·테스트를 건드리지 않음. 인증 상태(로그인·세션)와 계정 관리 책임 분리 | 아니오 |
| D-9 | C9 성공 후 세션 | 유지(`session.clear()` 안 함, 다시 로그인 안 함) | 확정(위임, 2026-11-10) | `screens.md` C9, `reference/auth.md` §9, `router.py:117~125`. `api-client` §2.1 표와 다름(C-1) | 아니오(확정, Q-4) |
| D-10 | A3 성공 후 | `session.clear()` 후 `/login`으로 `replace` 이동, `state = { from, notice: 'passwordReset' }`, A1에 `box done` 「새 비밀번호로 로그인하세요」 | 확정(위임, 2026-11-10) | `screens.md` A3 동작 메모, REQ-32, `api-client` §2.1 | 아니오 |
| D-11 | C8 성공 표시 | 같은 화면에 `box done` 「저장했어요」(role status), 이동 안 함 | 확정(위임, 2026-11-10) | 알림 컴포넌트 없음(C-4) | 아니오(확정, Q-5) |
| D-12 | C9 성공 표시 | 같은 화면에 `box done` 「비밀번호를 바꿨어요.」(임시 문구), 세 칸 비움, 이동 안 함 | 확정(위임, 2026-11-10) | `screens.md` C9에 성공 문구·이동 없음. D-11과 같은 방식 | 아니오(Q-8) |
| D-13 | 인증 상태의 사용자 갱신 | `AuthContextValue.replaceUser(user)` 추가 | 확정(위임, 2026-11-10) | `reload()`는 `loading`을 거쳐 화면이 내려감(§3.2). O8 헤더 이름 등이 저장 값을 바로 반영 | 아니오 |
| D-14 | 화면 검증 | 비밀번호 규칙은 domain(`checkPassword`, 코드 포인트·UTF-8 바이트), 필수·최소 길이는 버튼 비활성, 공백만·72바이트 초과·확인 불일치만 임시 문구, 이메일 형식은 서버 문구, 입력 칸 `maxLength`(이름·전화 100, 이메일 255, 코드 6) | 확정(위임, 2026-11-10) | A1 방식(`auth.md` §3.1). pydantic 영문 오류(`error_handlers.py:53~62`)에 닿지 않게 막음 | 아니오(Q-8) |
| D-15 | 보내기 전 정리 | 이름·전화·이메일 `trim()`, 비밀번호는 그대로 | 확정(위임, 2026-11-10) | 서버는 이름·전화를 trim하지 않고 저장(`user.py:67~70`). 비밀번호 공백은 값(REQ-5) | 아니오 |
| D-16 | 오류 매핑 | `EMAIL_DUPLICATED`·`INVALID_RESET_CODE`·`CURRENT_PASSWORD_MISMATCH`는 화면 정본 문구(칸 아래), 그 밖은 서버 `message`(폼 아래), 빈 문구는 임시 기본 문구 | 확정(위임, 2026-11-10) | F11·F13, `content.md` "계정·보안 서버 오류는 합니다체 그대로", C-3 | 아니오 |
| D-17 | 429 `ACCOUNT_LOCKED` | 서버 문구 그대로(남은 분 포함). `Retry-After`를 읽지 않고 `ApiError`도 바꾸지 않음 | 확정(위임, 2026-11-10) | 서버가 `ceil(Retry-After/60)`분을 문구에 넣음(`exceptions.py:24~29`). 헤더 읽기는 CORS 노출 설정이 없어 배포에서 불안정(C-8) | 아니오(Q-9) |
| D-18 | C8·C9의 401 | 유스케이스가 `session.clear()` 후 throw → 인증 상태 `anonymous` → `AccountLayout`이 `/login`(+`from`) | 확정(위임, 2026-11-10) | `api-client` §2.1·§3, `auth.md` N-5가 제안한 방식을 이 화면들에 먼저 적용 | 아니오 |
| D-19 | CtaBar 배치 | `<form style={{display:'contents'}}>`가 `.body`와 `.cta`를 감쌈. 주 버튼은 `.cta`와 `.dk` 두 벌 | 확정(위임, 2026-11-10) | `wireframe.html:757·762`(`.dk` + `.cta`), `layout.md` 반응형. 새 클래스 없음(F12) | 아니오 |
| D-20 | 하위 화면 AppBar | ← 링크(접근 이름 「뒤로」, 임시) + `h1.t` 제목 | 확정(위임, 2026-11-10) | `AppBar` README. 「닫기」(`auth.md` D-9)와 같은 방식 | 아니오 |
| D-21 | RolePicker 위치·접근성 | `features/auth/presentation/SignupRolePicker`(공개 안 함), `radiogroup` + `role="radio"` 버튼, 문구·아이콘은 와이어프레임 | 확정(위임, 2026-11-10) | 업무(역할)를 아는 부품이라 `shared/ui`가 아님(`design-system-usage` §3), A2 전용 | 아니오 |
| D-22 | 상호 라벨 | A2 상점주 「상호(상점명으로 쓰임) *」, C8 상점주 「상호 (변경 불가)」 읽기 전용, 와이어프레임의 「상호 변경은 고객센터에 문의해 주세요.」는 넣지 않음 | 확정(위임, 2026-11-10) | `screens.md` A2, `Input` README 필수·변경 불가 규칙, C-5·C-6 | 아니오(Q-6, Q-12) |
| D-23 | O8 메뉴 | 「내 정보 (전화번호)」(→ C8), 「비밀번호 변경」(→ C9), 「로그아웃」 순서. 행은 `Link` + `state.from`. 상점주만 안내 한 줄. PC는 계속 시트 | 확정(위임, 2026-11-10) | `wireframe.html:283~286`, `layout.md`(O8 → C8·C9·C10). `auth.md` D-3 대체 | 아니오 |
| D-24 | A3 단계·이메일 | 첫 요청 성공 뒤 2단계 표시, 이메일을 고치면 2단계를 닫고 코드를 비움, 확인·다시 받기는 보낸 이메일로, 60초 안내 없음 | 확정(위임, 2026-11-10) | `screens.md` A3 "1단계를 보내면 2단계가 열림". 다른 이메일의 코드로 확인하는 실수 방지 | 아니오(Q-10) |
| D-25 | 가입 성공·로그인 실패 | `/login`으로 `replace`, `state = { from, notice: 'signupLoginFailed' }`, A1에 임시 문구 「가입했어요. 로그인해 주세요.」 | 확정(위임, 2026-11-10) | 계정은 생겼으므로 A2에 머물면 다시 가입하다 409가 남 | 아니오(Q-8) |
| D-26 | entities | 새로 만들지 않음. `User`·`AccountGateway`는 `features/auth`. C3(결제 포인트)·C11 설계 때 `entities/user`(잔액·포인트 내역 포트) 내림을 검토 | 확정(위임, 2026-11-10) | `fsd-structure` §4 "미리 entities를 만들지 않습니다", `auth.md` D-5 | 아니오(Q-14) |
| D-27 | C8 진입 시 재조회 | 하지 않음(`useAuth`의 사용자 사용) | 확정(위임, 2026-11-10) | 가드가 앱 시작·재로그인 때 `/users/me`로 확인함. 저장 응답이 최신 값을 줌 | 아니오 |
| D-28 | 회원 탈퇴 | C7은 범위 밖(고객 C6 설계 때 후보). O8 상점주 탈퇴는 `open-issues` O8대로 넣지 않음 | 확정(위임, 2026-11-10) | `screens.md` C6·C7·O8 | 아니오(Q-13) |
| D-29 | 로그인 후 `/account/*` 복귀 | 안전한 `from`이 `/account/*`면 역할과 관계없이 복귀 | 확정(위임, 2026-11-10) | C8·C9에서 세션이 끊겨 다시 로그인한 상점주가 `/owner/today`로 튕기지 않게 | 아니오 |
| D-30 | DTO 변환 공유 | `infrastructure/userDto.ts`(`MeDto`, `toUser`)로 옮겨 `HttpAuthGateway`·`HttpAccountGateway`가 함께 씀 | 확정(위임, 2026-11-10) | `PATCH /users/me` 응답이 `GET /users/me`와 같음(reference §8). 같은 변환을 두 번 쓰지 않음 | 아니오 |
| D-31 | 이어받는 확정값 | 토큰 `localStorage`(`auth.md` D-11), 경로 상수 `shared/lib/routes.ts`(`app-shell.md` D-17), `location.state` 복귀(`auth.md` D-1), Context 위치(`auth.md` D-14), 역할별 도착지(`auth.md` D-6 임시) | 확정(이전 결정) | 다시 묻지 않음(`frontend-orchestration.md` §6) | |
| D-32 | AbortSignal 전달 경로 | `useSubmit<I, R>(run: (input: I, signal: AbortSignal) => Promise<R>)`. `useSubmit`이 `AbortController`를 하나 두고 언마운트 정리 때 `abort()`하며, `run`에 그 `signal`을 넘긴다(각 훅은 컨트롤러를 따로 두지 않고 받은 `signal`을 유스케이스에 넘김). 유스케이스 4개는 마지막 인자 `signal?: AbortSignal`을 받아 `AccountGateway`에 넘긴다. abort로 생긴 오류는 상태로 만들지 않는다(§3.2 `useSubmit`) | 확정(오케스트레이터, 2026-11-10) | F10, `react-implementation` §2 "`signal`은 포트 → infrastructure → `shared/api`까지". 발주서에서 D-31로 지정했으나 D-31이 이미 있어 D-32로 둠 | 아니오 |

## 10. 정책·보안 메모

- 비밀번호·재설정 코드는 입력 칸 값 외에 상태·로그·URL·`location.state`에 두지 않는다. `location.state`에는 `from`과 `notice` 문자열만 넣는다.
- 재설정 요청 결과는 가입 여부와 관계없이 같은 화면이다(REQ-27). 화면에서 "가입되지 않은 이메일" 같은 분기를 만들지 않는다.
- `readSignupRole`은 `OWNER`·`CUSTOMER`만 낸다. `ADMIN`은 화면 어디에서도 보낼 수 없다(REQ-1).
- 가입·재설정 요청은 `auth: false`(남은 토큰을 붙이지 않음). 프로필·비밀번호 변경은 토큰을 붙인다.
- 서버 문구는 JSX 텍스트로만 출력한다. `from`은 `readFrom`(내부 경로 검사)을 거친 값만 링크·이동에 쓴다.

## 11. C11·고객 셸을 위한 메모 (이번에 만들지 않음)

다음 설계(고객 C6·C7·C11)가 이어받을 것만 적는다. 코드·테스트는 이번 범위에 없다.
- C11·C6 포인트: `AccountGateway`에 `findPoints(query: { type?: PointType; page: number; size: number }, signal?): Promise<PointPage>`를 더하는 방식이 자연스럽다(엔드포인트 `GET /v1/users/me/points`, `page` 0부터·`total_elements`, `balance_after` nullable — `reference/auth.md` §5 "확인 필요"). `PointType` → 한국어는 `states.md` "포인트 내역 종류" 표를 domain 상수로.
- C7: `AccountGateway.withdraw(password)` + 성공 뒤 `session.clear()`, 오류 `CURRENT_PASSWORD_MISMATCH`(화면 문구 `비밀번호가 일치하지 않습니다.`로 C9와 다름), `STORE_HAS_RESERVED_RESERVATIONS` 등(`reference/auth.md` §12).
- C3 결제가 포인트 잔액을 쓰면 두 번째 영역(payments)이 생기므로 그때 `entities/user`(또는 잔액 포트) 내림을 결정한다(D-26). 결제 뒤 잔액 갱신은 `replaceUser`(D-13) 또는 `reload` 중에서 그때 정한다.
- 고객 셸 가드는 `decideAccess(…, 'CUSTOMER')`, C6 → C8·C9 행은 이 문서의 `ROUTES.accountProfile`·`accountPassword` + `state.from`을 쓴다.

## 12. 질문 목록 (추천안 포함)

| Q | 질문 | 추천안 | 상태 |
| --- | --- | --- | --- |
| Q-1 | 이번 범위(D-2): A2(고객·상점주)·A3·C8·C9·O8 행·A1 연결로 하고 C6·C7·C11·고객 셸은 다음 고객 화면 설계로 미룰지 | 그렇게 한다 | 확정: 추천안 |
| Q-2 | 설계안을 새 파일 `auth-account.md`로 둘지, `auth.md`에 합칠지(D-1) | 새 파일 | 확정: 추천안 |
| Q-3 | C8·C9를 역할 무관 `/account/profile`·`/account/password` + `AccountLayout`으로 둘지, 셸마다(`/owner/account/*`, 이후 `/me/*`) 따로 둘지(D-3·D-4) | 역할 무관 공용 경로 | 확정: 추천안 |
| Q-4 | C9 성공 뒤 이 기기 로그인을 유지할지(화면·API 명세) — 유지한다면 `api-client` §2.1 표의 "비밀번호 변경 → `session.clear()`"를 "재설정만 `clear()`"로 고칠지(C-1, D-9) | 유지, 스킬 표 수정(오케스트레이터) | 확정: 추천안 |
| Q-5 | C8 저장 뒤 표시(C-4, D-11): (a) 같은 화면 「저장했어요」(`box done`) 후 머묾 (b) 알림 없이 이전 화면으로 이동 (c) 디자인 시스템에 알림 컴포넌트를 먼저 추가 | (a) | 확정: 추천안 |
| Q-6 | C8 상점주 상호 칸 라벨과 안내(C-5·C-6, D-22): 라벨 「상호 (변경 불가)」로 할지, 와이어프레임의 「상호 변경은 고객센터에 문의해 주세요.」를 넣을지(고객센터가 있는지) | 라벨 「상호 (변경 불가)」, 안내는 고객센터 확인 전까지 뺌 | 확정: 추천안 |
| Q-7 | 상점주 가입 미리 선택을 쿼리(`/signup?role=owner`)로 할지 `location.state`로 할지(D-6) | 쿼리 | 확정: 추천안 |
| Q-8 | 임시 문구 7개(§3.1 표의 **임시**, D-12·D-14·D-20·D-25)를 해요체 임시값으로 구현할지 | 임시값으로 구현, content.md 확정 시 교체(M-1) | 확정: 추천안 |
| Q-9 | 429 잠금 문구를 서버 문구 그대로 쓸지, `Retry-After`로 화면이 직접 계산할지(C-8, D-17). 직접 계산하려면 `ApiError` 확장과 배포 시 CORS 노출 헤더(백엔드) 필요 | 서버 문구 | 확정: 추천안 |
| Q-10 | A3 「코드 다시 받기」에 60초 재요청 간격을 화면에 표시(카운트다운·안내)할지(D-24) | 이번에는 안 함(M-8) | 확정: 추천안 |
| Q-11 | 이름이 빈 기존 상점주는 상호 칸이 잠겨 C8에서 전화번호를 저장할 수 없다(C-9). 화면 안내를 둘지, 백엔드·디자인 규칙을 바꿀지 | 이번에는 버튼 비활성만, 규칙은 Auth 담당에게 확인 | 확정: 추천안 |
| Q-12 | A2 상점주 이름 라벨에 필수 표시를 붙일지: 「상호(상점명으로 쓰임) *」(D-22) | 붙인다(`Input` README 필수 규칙) | 확정: 추천안 |
| Q-13 | C7 회원 탈퇴를 이번 범위에 넣을지(D-28). 진입점이 C6뿐이고 고객 셸이 없다 | 다음 고객 화면 설계에 넣음 | 확정: 추천안 |
| Q-14 | C11·포인트를 위한 entities·API 확장을 미리 만들지(D-26, §11) | 만들지 않음, 메모만 | 확정: 추천안 |
| Q-15 | 범위 밖 추가(C-11): O8 상점주 안내 한 줄, `userDto.ts` 리팩터, `replaceUser`를 넣을지 | 넣는다(셋 다 작고 이번 화면에 필요하거나 와이어프레임에 있음) | 확정: 추천안 |
| Q-16 | C-2(A3 메일 발송 "확인 필요"가 낡음)를 디자인 문서(`screens.md`·`open-issues.md`)에 반영할지 | 디자인 시스템 담당에게 갱신 요청(프론트는 문서를 고치지 않음) | 확정: 추천안 |
