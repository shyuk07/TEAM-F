# 관리자(admin) 프론트엔드 설계안

- 화면: M1(승인), M2(제재 확인 시트), M3(회원 탭·회원 상세), M4(포인트 지급), M5(상점 탭·할인 탭), 관리자 셸
- 정본: `../../design-system/screens.md` M1~M5, `layout.md`, `states.md`, `../../reference/admin.md`, `../../../backend/src/admin/presentation/router.py`·`schemas.py`
- 함께 바꾸는 것: `features/auth/domain/redirect.ts` 관리자 도착지(`auth.md` D-6, C-3 중 관리자 부분)

## 1. slice 배치

| FSD      | slice                         | 화면         | 내용                                                                        |
| -------- | ----------------------------- | ------------ | --------------------------------------------------------------------------- |
| shared   | `shared/lib/useAsync.ts`      | 공통         | 서버 데이터 읽기 공용 훅 (`react-implementation` §2)                        |
| shared   | `shared/lib/routes.ts`        | 공통         | 관리자 경로 상수 추가                                                       |
| shared   | `shared/ui/Overlay.tsx`       | M2, M4       | 앱 프레임(`.app`)에 시트를 띄우는 오버레이(딤·Esc·포커스 트랩). 업무를 모름 |
| features | `features/admin`              | M1~M5        | 포트·구현체·유스케이스·훅·화면 부품                                         |
| widgets  | `widgets/admin-nav`           | 관리자 셸    | 탭 4개(승인·회원·상점·할인), 상단 nav, 하단 탭 바                           |
| pages    | `pages/admin-approvals`       | M1           | 승인 탭                                                                     |
| pages    | `pages/admin-users`           | M3 (+M2, M4) | 회원 탭. `/admin/users/:userId`면 상세 선택                                 |
| pages    | `pages/admin-moderation`      | M5 (+M2)     | 상점 탭·할인 탭 (`AdminStoresPage`, `AdminOffersPage`)                      |
| app      | `app/layouts/AdminLayout.tsx` | 셸 가드      | `decideAccess(state, 'ADMIN')`, 하단 탭 바                                  |

## 2. 경로

| 경로                   | 화면                                           | 하단 탭         |
| ---------------------- | ---------------------------------------------- | --------------- |
| `/admin`               | `/admin/approvals`로 이동                      | —               |
| `/admin/approvals`     | M1                                             | 있음            |
| `/admin/users`         | M3 목록                                        | 있음            |
| `/admin/users/:userId` | M3 목록 + 상세 (PC 우측 패널, 모바일은 상세만) | 없음(하위 화면) |
| `/admin/stores`        | M5 상점                                        | 있음            |
| `/admin/offers`        | M5 할인                                        | 있음            |

## 3. features/admin

### domain

- `adminUser.ts`: `AdminRole`, `AdminAccountStatus`, `AdminUserSummary{id,email,name,role,status,createdAt}`, `AdminUserDetail{+phone,point}`, `UserPage{items,page,size,total}`, `PointEntry{id,amount,type,reason,balanceAfter,createdAt}`, `PointHistory{userId,balance,entries,page,size,total}`
- `labels.ts`: `accountStatusView(status)` → `{text, tone}` (`states.md` 상점·회원 표), `pointTypeLabel(type)` (`states.md` 포인트 표), `storeStatusView(status)`, `formatPoint`, `formatSignedPoint`(− 는 U+2212), `formatShortDate`(MM/DD), `displayName`, `maskPhone`
- `userQuery.ts`: `MemberFilter`(all·customer·owner·suspended·withdrawn) → `{role?, status?}`, `APPROVAL_QUERY`(OWNER·PENDING), `pageSummary(page,size,total)` → 「1–20 / 134명」·이전/다음 가능
- `sanction.ts`: `SanctionKind`(rejectOwner·suspendUser·withdrawUser·suspendStore·closeStore·suspendOffer), `sanctionCopy(kind)`(제목·사유 라벨·버튼), `validateSanction(kind, input, now)`, `suspensionEnd(date)`(선택한 날 23:59:59.999 현지 시각)
- `pointGrant.ts`: `parseAmount`, `validateGrant`, `grantButtonLabel`, `balanceAfterGrant`
- `actionError.ts`: `actionErrorMessage(info)` → 서버 `message`가 있으면 그대로, 없으면 임시 문구 (D-7)
- `uuid.ts`: `isUuid`
- `adminRepository.ts` (domain 포트 `AdminRepository`)

```ts
interface AdminRepository {
  listUsers(q: UserListQuery, signal?: AbortSignal): Promise<UserPage>;
  findUser(id: string, signal?: AbortSignal): Promise<AdminUserDetail>;
  findUserPoints(
    id: string,
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<PointHistory>;
  approveOwner(id: string): Promise<void>;
  rejectOwner(id: string, reason: string): Promise<void>;
  suspendUser(id: string, reason: string, until: Date | null): Promise<void>;
  withdrawUser(
    id: string,
    reason: string,
  ): Promise<{ cancelledReservationCount: number }>;
  suspendStore(id: string, reason: string): Promise<ModeratedStore>;
  closeStore(id: string, reason: string): Promise<ModeratedStore>;
  suspendOffer(id: string, reason: string): Promise<ModeratedOffer>;
  grantPoints(
    id: string,
    amount: number,
    reason: string,
  ): Promise<{ balanceAfter: number | null }>;
}
```

### application

- `tokens.ts`: `AdminRepositoryToken`
- `errorInfo.ts`: `readErrorInfo` (auth와 같은 방식, F5)
- `runSanction.ts`: `runSanction(deps, kind, targetId, input)` → 결과 (`SanctionResult`)
- `useAdminQueries.ts`: `useUserList(q)`, `useUserDetail(id)`, `useUserPoints(id)` — `useAsync`
- `useAdminMutation.ts`: 중복 제출 방지 + pending·error 상태 (`react-implementation` §4)

### infrastructure — `HttpAdminRepository`

| 메서드                    | 엔드포인트                                                     |
| ------------------------- | -------------------------------------------------------------- |
| listUsers                 | `GET /v1/admin/users?role&status&email&page&size`              |
| findUser                  | `GET /v1/admin/users/{id}` (auth 모듈)                         |
| findUserPoints            | `GET /v1/admin/users/{id}/points?page&size`                    |
| approveOwner              | `PATCH /v1/admin/owners/{id}/approve`                          |
| rejectOwner               | `PATCH /v1/admin/owners/{id}/reject {reason}`                  |
| suspendUser               | `PATCH /v1/admin/users/{id}/suspend {reason, suspended_until}` |
| withdrawUser              | `DELETE /v1/admin/users/{id} {reason}`                         |
| suspendStore / closeStore | `PATCH /v1/admin/stores/{id}/suspend` · `/close {reason}`      |
| suspendOffer              | `PATCH /v1/admin/offers/{id}/suspend {reason}`                 |
| grantPoints               | `POST /v1/admin/users/{id}/points {amount, reason}`            |

DTO 필드: snake_case → camelCase, `created_at` → `Date`, 포인트 `type`(EARN 등) 그대로.

### presentation

- `AccountStatusTag`: 「승인 대기 PENDING」처럼 문구 + `code-tag`
- `UserTable`: 표(TableRow). 모바일은 이메일·가입일을 이름 아래 `m mob`로 접음
- `ApprovalsPanel` (M1), `MembersPanel` (M3 목록), `UserDetailPanel` (M3 상세)
- `SanctionSheet` (M2), `PointGrantSheet` (M4) — `shared/ui/Overlay` 안에 그림
- `ModerationPanel` (M5): ID 입력 → 찾기 → 대상 행 + 버튼

상태: 로딩 = `sk` 뼈대, 오류 = `warn` + 「다시 시도」, 빈 상태 = `empty`.

## 4. 결정 표

| D    | 항목                                  | 값                                                                                                                                                                 | 임시/확정 | 근거                                                                                                | 사용자 결정 필요                  |
| ---- | ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------- | --------------------------------------------------------------------------------------------------- | --------------------------------- |
| D-1  | 계정 버튼                             | `widgets/owner-nav`의 `OwnerAccountButton`을 관리자 page에서 그대로 씀(O8은 상점주·관리자 공용)                                                                    | 임시      | `layout.md` 72줄. widget끼리 import 불가라 page가 조립                                              | 이름을 `AccountButton`으로 옮길지 |
| D-2  | M2·M4 표시 방식                       | 모든 크기에서 시트(Overlay). 와이어프레임의 PC 2단 배치·← 화면은 쓰지 않음                                                                                         | 임시      | 「행의 버튼마다 각자 M2 시트를 엶」(screens.md M1)                                                  | 예                                |
| D-3  | M1 왼쪽 상자                          | 이메일 검색 + 「승인 대기」「정지 회원」 건수. 「상점주/고객」 칩과 「정지 상점」은 뺌                                                                             | 임시      | 승인 대상은 상점주뿐. 정지 상점 수 API 없음(C-3)                                                    | 예                                |
| D-4  | 정지 종료 시각                        | 날짜 입력, 그날 23:59:59.999(현지)                                                                                                                                 | 임시      | 「정지 종료 (비우면 무기한)」에 시각 없음                                                           | 예                                |
| D-5  | M2 제목·라벨·버튼 문구 (회원 정지 외) | 상점주 거부/거부 사유 */거부하기, 강제 탈퇴/탈퇴 사유 */탈퇴시키기, 상점 정지/정지 사유 */정지하기, 강제 폐점/폐점 사유 */폐점하기, 할인 정지/정지 사유 */정지하기 | 임시      | screens.md에는 회원 정지 문구만 있음                                                                | 예 (content.md 확정)              |
| D-6  | M3 상세 포인트 내역                   | 최근 5건 (`size=5`)                                                                                                                                                | 임시      | 「최근 포인트 내역」 건수 미정                                                                      | 아니오                            |
| D-7  | 처리 오류 문구                        | 서버 `message`(명세 표의 한국어 문구)를 그대로, 없으면 「처리하지 못했어요. 잠시 후 다시 시도해 주세요.」                                                          | 임시      | admin 명세 메시지가 사용자용 한국어                                                                 | 예                                |
| D-8  | M5 「찾기」                           | ID 형식(UUID)만 확인해 대상 행을 만들고, 이름·상태는 조치 응답으로 채움                                                                                            | 임시      | 상점·할인 단건 조회 관리자 API 없음(C-1)                                                            | 예                                |
| D-9  | 역할·상태 타입                        | admin domain에 따로 둠(auth의 `Role`과 같은 값)                                                                                                                    | 임시      | 영역끼리 import 불가. `entities/user`는 두 번째 사용처가 생긴 지금 내릴 수 있음                     | 아니오 (리팩터 후보)              |
| D-10 | 관리자 도착지                         | 로그인 뒤 `from`이 `/admin` 아래면 그곳, 아니면 M1                                                                                                                 | 임시      | `layout.md` 70줄                                                                                    | 아니오                            |
| D-11 | 상세에서 버튼 숨김                    | 탈퇴 회원: 모든 버튼 없음. 관리자 계정: 정지·강제 탈퇴 없음. 정지 회원: 정지 없음                                                                                  | 임시      | 서버가 막는 동작(`USER_WITHDRAWN`, `ADMIN_ACCOUNT_PROTECTED`, `USER_ALREADY_SUSPENDED`)은 미리 숨김 | 아니오                            |
| D-12 | 관리자 상단 바 위치                   | `AdminLayout`이 그림(로고 「관리자」 + 상단 nav + 계정). 모든 관리자 화면의 바가 같다                                                                              | 임시      | 상점주는 page가 그림(`app-shell.md` D-3). 관리자 화면은 제목이 바뀌지 않음                          | 아니오                            |
| D-13 | `useAsync` 구현                       | 결과를 요청 키와 함께 저장하고, 키가 다르면 로딩으로 계산(effect 안에서 곧바로 setState하지 않음)                                                                  | 임시      | `react-implementation` §2 예시는 ESLint `react-hooks/set-state-in-effect` 오류. 스킬 예시를 맞출지  | 예 (스킬 예시 갱신)               |
| D-14 | 버튼 문구의 화면 ID                   | 「포인트 지급 (M4)」「정지 (M2)」의 괄호는 와이어프레임 연결 표기로 보고 빼서 「포인트 지급」「정지」                                                              | 임시      | `screens.md` M3                                                                                     | 아니오                            |

## 5. 정합·차단 이슈

| C   | 내용                                                                                                                                                                                                                                                                                                                                           | 근거                                                                                                             |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| C-1 | 상점·할인 목록 API와 관리자용 단건 조회가 없음. M5는 ID로만 조치                                                                                                                                                                                                                                                                               | `open-issues.md` M1, `backend/src/admin/presentation/router.py`                                                  |
| C-2 | M2 「진행 중 예약 N건」, M5 「강제 폐점은 예약 취소·환불 건수를 먼저 보여 줌」의 데이터를 주는 API가 없음 → 표시하지 않음. 강제 탈퇴는 응답의 `cancelled_reservation_count`를 결과로 보여 줌                                                                                                                                                   | `screens.md` M2·M5, `schemas.py`                                                                                 |
| C-3 | 정지 상점 수를 세는 API 없음                                                                                                                                                                                                                                                                                                                   | `screens.md` M1                                                                                                  |
| C-5 | 회원 상세(`GET /v1/admin/users/{id}`, auth `get_user`)는 저장된 `status` 그대로라 기간이 지난 정지도 `SUSPENDED`. 목록은 실효 상태(`effective_status`)라 `APPROVED`. 상세에서 「정지」 버튼이 숨고 상태가 목록과 다르게 보임. `UserResponse`에 `suspended_until`이 없어 프론트에서 계산할 수 없음 → 백엔드가 실효 상태를 주도록 할지 결정 필요 | `backend/src/auth/presentation/router.py` 157줄, `backend/src/auth/application/service.py` 82줄, `screens.md` M3 |
| C-4 | 회원 정지 `USER_NOT_SUSPENDABLE`은 명세 본문에 없고 표에만 있음(D36)                                                                                                                                                                                                                                                                           | `reference/admin.md` §3                                                                                          |

## 6. 테스트 목록 (`tests/` 아래 같은 경로)

- `features/admin/domain/labels.test.ts`: 상태별 문구·톤, 포인트 종류 문구, 부호 포인트(+/−), 전화번호 가림, 이름 없을 때 이메일
- `features/admin/domain/userQuery.test.ts`: 필터 → 쿼리, 페이지 요약(0건, 마지막 페이지)
- `features/admin/domain/sanction.test.ts`: 사유 공백 거부, 정지 종료 과거·오늘·미래, 종료는 회원 정지에만
- `features/admin/domain/pointGrant.test.ts`: 쉼표 숫자, 0·음수·소수 거부, 버튼 문구
- `features/admin/infrastructure/httpAdminRepository.test.ts`: 엔드포인트·메서드·본문, DTO 변환
- `features/admin/application/runSanction.test.ts`: 종류별 포트 호출
- `features/admin/presentation/ApprovalsPanel.test.tsx`: 로딩·빈·오류·성공, 승인 후 다시 불러옴, 거부 시트
- `features/admin/presentation/SanctionSheet.test.tsx`: 사유 없으면 제출 안 함, 서버 오류 표시, 성공 콜백
- `features/admin/presentation/PointGrantSheet.test.tsx`: 버튼 문구에 금액, 지급 후 잔액
- `features/admin/presentation/MembersPanel.test.tsx`: 칩 → 쿼리, 페이지 이동, 행 선택
- `widgets/admin-nav/domain/adminTabs.test.ts`: 경로 → 현재 탭
- `app/layouts/AdminLayout.test.tsx`: 관리자 통과, 상점주·고객은 `/`, 비로그인은 로그인
- `features/auth/domain/redirect.test.ts`: ADMIN 도착지 갱신

## 7. 남길 작업 주석

- `TODO` M5 ID 조회 (C-1, 언제: 상점·할인 목록 API 추가 후)
- `TODO` M2 진행 중 예약·강제 폐점 건수 (C-2, 언제: 백엔드 API 추가 후)
- `TODO` 임시 문구 D-5, D-7 (언제: 결정 후)
