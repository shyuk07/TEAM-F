---
name: fsd-structure
description: 마감 직전 프론트엔드의 Feature-Sliced Design(FSD) 바깥 구조를 관리합니다. 계층(app, pages, widgets, features, entities, shared)별 책임, features를 업무 영역 7개(auth, stores, products, offers, reservations, payments, admin)로 나누는 기준과 영역별 백엔드·명세·화면 대응, 영역끼리 공유하는 것을 entities로 내리는 기준, slice 이름 규칙, 공개 API(index.ts)와 wiring.ts, 계층 간 import 규칙, slice 생성·이동·분리·삭제 절차와 화면(C1, O2 등)↔slice 대응표를 다룹니다. 새 화면이나 기능을 어느 영역·계층에 둘지 정할 때, slice를 만들거나 옮기거나 나눌 때, "이건 feature야 entity야" 같은 배치 판단이 필요할 때 사용합니다. slice 안의 4계층과 의존성 주입은 layer-architecture, 자동 검사는 layer-check를 씁니다.
---

# FSD 구조 관리

이 스킬은 **slice를 어느 계층에 어떤 이름으로 두는가**를 정합니다. slice 안을 어떻게 나누고 연결하는지는 `layer-architecture`가 정본입니다. 규칙 ID(F1~F3, F18)는 `frontend-invariants`가 정본입니다.

## 1. 계층과 책임

| 계층 | 책임 | slice | 예시 |
| --- | --- | --- | --- |
| `app` | 앱 시작, 라우터, 전역 Provider, 전역 스타일, 역할별 셸, **의존성 조립(영역별 `wiring.ts`를 모음)** | 없음 | `app/router/`, `app/providers/`, `app/styles/`, `app/container.ts` |
| `pages` | 화면 하나(라우트 하나). 여러 영역의 features·widgets·entities를 조립 | 있음 | `pages/offer-detail/` (C2) |
| `widgets` | 여러 화면에서 쓰는 큰 화면 블록. 여러 영역을 함께 쓸 수 있음 | 있음 | `widgets/customer-tab-bar/`, `widgets/today-pickups/` |
| `features` | **업무 영역 하나**(§1.1의 7개). 그 영역의 포트·구현체·유스케이스·훅·화면 부품과 **의존성 연결(`wiring.ts`)** | 있음 | `features/auth/`, `features/offers/`, `features/reservations/` |
| `entities` | **두 영역 이상이 함께 쓰는** 업무 개체의 타입·순수 규칙·포트(`interface`)·토큰·표시 부품. 구현체와 wiring은 두지 않음 | 있음 | `entities/offer/`, `entities/session/` |
| `shared` | 업무를 모르는 공용 코드 | 없음 | `shared/api/`, `shared/ui/`, `shared/lib/`, `shared/config/` |

`app`과 `shared`는 slice 대신 용도별 폴더로 나눕니다(F3). 이 두 계층 안에는 4계층 폴더를 만들지 않습니다.

### 1.1 업무 영역 (features)

features slice는 아래 7개로 고정합니다. 이름과 범위는 백엔드 모듈과 API 명세를 따르되, 백엔드 catalog는 상품(products)과 할인(offers)으로 나눕니다.

| features slice | 백엔드 | API 명세 | 엔드포인트 | 주요 화면 | 구현을 맡는 entities |
| --- | --- | --- | --- | --- | --- |
| `auth` | auth | `../docs/reference/auth.md` | `/v1/auth/*`, `/v1/users/me*` | A1~A3, C6~C11, O8 | `session`, `user` |
| `stores` | stores | `../docs/reference/stores.md` | `/v1/stores`, `/v1/stores/me`, `/v1/stores/{id}/close` | O0, O7 | `store` |
| `products` | catalog | `../docs/reference/catalog.md` | `/v1/products*`, `/v1/stores/{id}/products`, 상품 이미지 | O4, O6, O11, O12 | `product` |
| `offers` | catalog | `../docs/reference/catalog.md` | `/v1/offers*`, `/v1/stores/{id}/offers`, `/v1/products/{id}/offers` | C1, C1a, C2, O2, O3, O5, O9, O10 | `offer` |
| `reservations` | reservations | `../docs/reference/reservations.md` | `/v1/reservations*`, `/v1/users/me/reservations`, `/v1/stores/{id}/reservations` | C2(예약 생성), C3a, C5, C5a, C5b, O1 | `reservation` |
| `payments` | payments | `../docs/reference/payments.md` | `/v1/payments*`, `/v1/refunds/*` | C3, C4 | `payment` |
| `admin` | admin (+ auth의 `/v1/admin/users/{id}`) | `../docs/reference/admin.md` | `/v1/admin/*` | M1~M5 | 없음 |

- 영역을 새로 만들거나 이름을 바꾸려면 사용자 승인을 받고, 이 표와 `check_layers.mjs`의 `FEATURE_DOMAINS`를 함께 고칩니다.
- 엔드포인트가 어느 영역인지 애매하면 URI가 아니라 **백엔드에서 그 엔드포인트를 가진 모듈**과 **다루는 개체**로 정합니다(`../backend/src/<모듈>/presentation/router.py`). 예: `/v1/stores/{id}/products`는 경로가 stores로 시작하지만 상품을 다루므로 `products`입니다.
- 화면 ↔ 엔드포인트는 `../docs/design-system/api-map.md`가 정본입니다. 이 표와 다르면 `api-map.md`를 따르고 이 표를 고칩니다.
- "구현을 맡는 entities"는 그 entity 포트의 구현체를 이 영역의 infrastructure에 두고 이 영역의 `wiring.ts`가 등록한다는 뜻입니다(`layer-architecture` §6.6). entities는 필요해질 때 만듭니다.

## 2. import 규칙 (F1)

```text
app ─▶ pages ─▶ widgets ─▶ features ─▶ entities ─▶ shared
```
- 화살표 방향(위 → 아래)으로만 import합니다. 건너뛰는 것은 됩니다(pages → entities).
- **영역(features)끼리는 import하지 않습니다.** `features/reservations`가 `features/offers`를 가져오면 안 됩니다.
- 영역끼리 필요한 것이 생기면 둘 중 하나로 풉니다.
  - **데이터·규칙이 필요할 때:** 공유할 타입·순수 규칙·포트·토큰을 `entities/<개체>`로 내립니다. 구현체는 그 개체를 소유한 영역(§1.1)이 만들고 등록합니다. 쓰는 영역은 `useDep(토큰)`으로 받습니다.
    - 예: 예약 화면이 할인 정보를 보여 준다 → `entities/offer`에 `Offer` 타입·`OfferRepository` 포트·`OfferRepositoryToken`, `features/offers`가 `HttpOfferRepository`를 구현·등록, `features/reservations`는 토큰으로 받음
  - **화면 조합만 필요할 때:** 두 영역의 부품을 `widgets`나 `pages`에서 함께 배치합니다.
- 경로는 `@/` 별칭(`src/`)을 씁니다. slice 안에서는 상대 경로를 씁니다.

## 3. 공개 API (F2, F18)

slice 루트에는 파일 두 개만 둡니다(F4, F18).

| 파일 | 역할 | 가져올 수 있는 곳 |
| --- | --- | --- |
| `index.ts` | 공개 API. 타입·순수 함수·포트 타입·토큰·훅·컴포넌트 | 위 FSD 계층 어디서나 |
| `wiring.ts` (**features만**) | 이 영역의 구현체를 토큰에 연결하는 `wire<영역>()` | `app/container.ts`만 |

```ts
// src/entities/offer/index.ts  (영역끼리 공유: 타입·규칙·포트·토큰·표시 부품)
export type { Offer, OfferStatus } from './domain/offer'
export { discountRate, minutesUntilClose, canReserve } from './domain/offer'
export type { OfferRepository, NearbyQuery } from './domain/offerRepository'
export { OfferRepositoryToken } from './application/tokens'
export { OfferCard } from './presentation/OfferCard'

// src/features/offers/index.ts  (영역: 화면에서 쓸 훅·부품)
export { useNearbyOffers, useOfferDetail } from './application/useOffers'
export { OfferList } from './presentation/OfferList'
export { StockAdjustSheet } from './presentation/StockAdjustSheet'
```
- 밖에서는 `import { OfferCard } from '@/entities/offer'`처럼 slice 루트만 씁니다.
- infrastructure(구현체, DTO)와 `wiring.ts`는 `index.ts`로 내보내지 않습니다. 다른 slice는 포트와 토큰만 알고 구현체를 모릅니다(`layer-architecture` §6).
- 공개 API를 바꾸면 쓰는 쪽을 함께 고칩니다(`git grep -n "@/entities/offer'" -- src`).

## 4. 어느 계층에 둘까

순서대로 묻고, 처음 "예"인 곳에 둡니다.
1. 업무를 전혀 모르는가(버튼, 날짜 함수, fetch 래퍼, DI 도구) → `shared`
2. 한 영역의 데이터·동작(조회든 변경이든)이나 그 영역의 포트·구현체·훅·화면 부품인가 → `features/<영역>` (§1.1 표로 영역 결정)
3. 그중 **다른 영역도 필요로 하는** 타입·순수 규칙·포트·토큰·표시 부품인가 → 그 부분만 `entities/<개체>`로 내림. 구현체는 영역에 남김
4. 여러 화면에 같은 모양으로 반복되는 큰 블록인가(하단 탭, 오늘 픽업 목록) → `widgets/<명사>`
5. 라우트 하나인가 → `pages/<화면>`

**처음에는 영역(features) 안에 두고, 두 번째 영역이 필요로 할 때 entities로 내립니다.** 미리 entities를 만들지 않습니다.

## 5. 이름 규칙

- 폴더는 kebab-case.
- features는 §1.1의 영역 이름만 씁니다(복수형 명사: `offers`, `reservations`. 단 `auth`, `admin`은 그대로).
- entities는 단수 명사(`offer`, `reservation`, `session`), widgets는 명사(`today-pickups`), pages는 화면의 뜻(`offer-detail`).
- 용어는 `../docs/design-system/screens.md`, `../docs/reference/`, 백엔드 모듈·테이블 이름과 같은 말을 씁니다. 같은 실체에 두 이름을 만들지 않습니다(offer / discount 혼용 금지).
- pages slice 이름은 화면 ID가 아니라 뜻으로 짓고, 대응은 §7 표에 적습니다.

## 6. 절차

### 영역(features)에 기능 추가
1. §1.1 표로 영역을 정합니다. 해당 영역이 없으면 만들지 말고 사용자에게 묻습니다.
2. 그 영역 slice 안의 맞는 4계층 폴더에 둡니다(F4, `layer-architecture` §1).
3. 포트·구현체가 생기면 그 영역의 `wiring.ts`에 등록합니다(`layer-architecture` §6.9). 영역을 처음 만들면 `app/container.ts`에 `wire<영역>()` 한 줄을 추가합니다.
4. §7 대응표를 갱신하고 `node .claude/skills/layer-check/check_layers.mjs`가 0건인지 확인합니다.

### entities로 내리기 (두 번째 영역이 필요로 할 때)
1. 공유할 것만 고릅니다: 타입, 순수 규칙, 포트(`interface`), 토큰, 표시 부품. 구현체·DTO·훅은 영역에 남깁니다.
2. `entities/<개체>/`로 옮기고 `index.ts`로 내보냅니다.
3. 원래 영역은 entities 공개 API를 import하도록 바꿉니다. 구현체는 그대로 원래 영역의 infrastructure에 두고 `implements`가 entities 포트를 가리키게 합니다.
4. §1.1 표의 "구현을 맡는 entities" 열과 설계안을 갱신합니다.

### 옮기기·나누기
1. 옮기기 전에 쓰는 곳을 찾습니다: `git grep -n "@/<계층>/<slice>" -- src` (Windows·macOS·Linux 공통. 아직 커밋하지 않은 새 파일도 찾으려면 `--untracked`를 붙입니다)
2. 공개 API 이름은 유지하고 import 경로만 바꿉니다.
3. 영역은 나누지 않습니다(7개 고정). 영역 안이 커지면 계층 폴더 안에서 하위 폴더로 정리합니다(예: `features/offers/presentation/owner/`).
4. §7 표와 설계안(`../docs/design/frontend/<slice>.md`)을 함께 고칩니다.

### 지우기
쓰는 곳이 0건인지 `git grep`으로 확인하고, §7 표와 설계안에서 지웠다고 표시합니다.

## 7. 화면 ↔ slice 대응표

slice를 만들 때마다 `fe-architect`가 이 표를 채웁니다. 화면 ID는 `../docs/design-system/screens.md`를 따릅니다.

| 화면 | pages slice | 쓰는 features(영역) / widgets / entities | 설계안 |
| --- | --- | --- | --- |
| (예) C2 할인 상세 | `pages/offer-detail` | `features/offers`, `features/reservations`, `entities/offer` | `../docs/design/frontend/offers.md`, `reservations.md` |
| A1 로그인 | `pages/login` | `features/auth`, `entities/session` | `../docs/design/frontend/auth.md` |
| O8 계정 메뉴, C10 로그아웃 확인 (상점주 셸) | 없음(라우트 없는 오버레이. `widgets/owner-nav`의 `OwnerAccountButton` 안) | `widgets/owner-nav`, `features/auth`(`LogoutConfirmSheet`), `entities/session` | `../docs/design/frontend/auth.md` |
| 상점주 셸 가드 | 없음(`app/layouts/OwnerLayout`) | `features/auth`(`useAuth`, `decideAccess`) | `../docs/design/frontend/auth.md` |
| A2 회원가입 | `pages/signup` | `features/auth`(`SignupForm`) | `../docs/design/frontend/auth-account.md` |
| A3 비밀번호 재설정 | `pages/password-reset` | `features/auth`(`PasswordResetForm`), `entities/session` | `../docs/design/frontend/auth-account.md` |
| C8 프로필 변경 | `pages/account-profile` | `features/auth`(`ProfileForm`, `useAuth`) | `../docs/design/frontend/auth-account.md` |
| C9 비밀번호 변경 | `pages/account-password` | `features/auth`(`PasswordChangeForm`) | `../docs/design/frontend/auth-account.md` |
| C8·C9 로그인 필요 가드 | 없음(`app/layouts/AccountLayout`) | `features/auth`(`useAuth`, `decideAccess(…, 'ANY')`) | `../docs/design/frontend/auth-account.md` |
| O8 계정 메뉴의 C8·C9 행 | 없음(`widgets/owner-nav`의 `OwnerAccountMenu`) | `widgets/owner-nav`, `features/auth` | `../docs/design/frontend/auth-account.md` |
| 고객 셸(하단 탭 홈·내 예약·마이)·고객 가드 | 없음(`app/layouts/CustomerLayout`·`CustomerFrame`) | `widgets/customer-nav`, `features/auth`(`useAuth`, `decideAccess(…, 'CUSTOMER')`, `loginRedirectState`) | `../docs/design/frontend/customer-home.md` |
| C1 홈·주변 할인, C1a 위치·반경(C1 위 시트) | `pages/home` | `features/offers`, `features/auth`(`useAuth`), `widgets/customer-nav`(레이아웃) | `../docs/design/frontend/customer-home.md` |
| C6 마이, C10 로그아웃 확인(고객, C6 위 시트) | `pages/my` | `features/auth`(`usePointHistory`, `PointLogList`, `LogoutConfirmSheet`) | `../docs/design/frontend/customer-home.md` |
| C11 포인트 내역 전체 | `pages/point-history` | `features/auth`(`usePointHistory`, `PointLogList`) | `../docs/design/frontend/customer-home.md` |
| C7 회원 탈퇴 확인 | `pages/withdraw` | `features/auth`(`WithdrawForm`, `useWithdraw`, `usePointHistory`) | `../docs/design/frontend/customer-home.md` |
| C2 할인 상세·C5 내 예약 (자리 page, 담당 팀원이 교체) | 없음(`app/router/placeholders.tsx`의 `OfferDetailPlaceholder`·`ReservationsPlaceholder`) | 없음 | `../docs/design/frontend/customer-home.md` §5 |
| A1 진입 경로별 안내 한 줄 | `pages/login` | `features/auth`(`readLoginEntry`, `loginEntryMessage`) | `../docs/design/frontend/customer-home.md` |
