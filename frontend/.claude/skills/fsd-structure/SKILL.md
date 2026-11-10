---
name: fsd-structure
description: 마감 직전 프론트엔드의 Feature-Sliced Design(FSD) 바깥 구조를 관리합니다. 계층(app, pages, widgets, features, entities, shared)별 책임, 새 slice를 어느 계층에 둘지 판단하는 기준, slice 이름 규칙, 공개 API(index.ts), 계층 간 import 규칙, slice 생성·이동·분리·삭제 절차와 화면(C1, O2 등)↔slice 대응표를 다룹니다. 새 화면이나 기능을 어디에 둘지 정할 때, slice를 만들거나 옮기거나 나눌 때, "이건 feature야 entity야" 같은 배치 판단이 필요할 때 사용합니다. slice 안의 4계층은 layer-architecture, 자동 검사는 layer-check를 씁니다.
---

# FSD 구조 관리

이 스킬은 **slice를 어느 계층에 어떤 이름으로 두는가**를 정합니다. slice 안을 어떻게 나누는지는 `layer-architecture`가 정본입니다. 규칙 ID(F1~F3)는 `frontend-invariants`가 정본입니다.

## 1. 계층과 책임

| 계층 | 책임 | slice | 예시 |
| --- | --- | --- | --- |
| `app` | 앱 시작, 라우터, 전역 Provider, 전역 스타일, 역할별 셸 | 없음 | `app/router/`, `app/providers/`, `app/styles/` |
| `pages` | 화면 하나(라우트 하나). widgets·features·entities를 조립 | 있음 | `pages/offer-detail/` (C2) |
| `widgets` | 여러 화면에서 쓰는 큰 화면 블록 | 있음 | `widgets/customer-tab-bar/`, `widgets/offer-list/` |
| `features` | 사용자 행동 하나(동사). 서버 상태를 바꾸는 상호작용 | 있음 | `features/reserve-offer/`, `features/cancel-reservation/` |
| `entities` | 업무 개체(명사)와 그 표시·조회 | 있음 | `entities/offer/`, `entities/reservation/`, `entities/user/` |
| `shared` | 업무를 모르는 공용 코드 | 없음 | `shared/api/`, `shared/ui/`, `shared/lib/`, `shared/config/` |

`app`과 `shared`는 slice 대신 용도별 폴더로 나눕니다(F3). 이 두 계층 안에는 4계층 폴더를 만들지 않습니다.

## 2. import 규칙 (F1)

```text
app ─▶ pages ─▶ widgets ─▶ features ─▶ entities ─▶ shared
```
- 화살표 방향(위 → 아래)으로만 import합니다. 건너뛰는 것은 됩니다(pages → entities).
- 같은 계층의 다른 slice는 import하지 않습니다. `features/reserve-offer`가 `features/cancel-reservation`을 쓰면 안 됩니다.
  - 두 feature가 같은 것을 필요로 하면 아래 계층(entities·shared)으로 내리거나, 위 계층(widgets·pages)에서 조립합니다.
- 경로는 `@/` 별칭(`src/`)을 씁니다. slice 안에서는 상대 경로를 씁니다.

## 3. 공개 API (F2)

slice마다 루트에 `index.ts`를 두고, 밖에서 쓸 것만 다시 내보냅니다.

```ts
// src/entities/offer/index.ts
export type { Offer, OfferStatus } from './domain/offer'
export { formatDiscountRate, minutesUntilClose } from './domain/offer'
export { useOffer, useOffers } from './application/useOffers'
export { OfferCard } from './presentation/OfferCard'
```
- 밖에서는 `import { OfferCard } from '@/entities/offer'`만 씁니다.
- infrastructure(API 함수, DTO)는 공개 API에 넣지 않습니다. 다른 slice가 서버를 직접 부르지 못하게 합니다.
- 공개 API를 바꾸면 쓰는 쪽을 함께 고칩니다(`git grep -n "@/entities/offer'" -- src`).

## 4. 어느 계층에 둘까

순서대로 묻고, 처음 "예"인 곳에 둡니다.
1. 업무를 전혀 모르는가(버튼, 날짜 함수, fetch 래퍼) → `shared`
2. 업무 개체 하나를 보여 주거나 조회만 하는가(상품 카드, 예약 상태 태그) → `entities/<명사>`
3. 사용자가 무언가를 **바꾸는** 행동인가(예약, 취소, 재고 조정, 로그인) → `features/<동사-명사>`
4. 여러 화면에 같은 모양으로 반복되는 큰 블록인가(하단 탭, 상품 목록 + 필터) → `widgets/<명사>`
5. 라우트 하나인가 → `pages/<화면>`

확신이 없으면 낮은 계층(entities)에 두지 말고 page 안에 두었다가, 두 번째 사용처가 생길 때 내립니다.

## 5. 이름 규칙

- 폴더는 kebab-case. features는 `동사-명사`(`reserve-offer`), entities·widgets는 명사(`offer`, `offer-list`).
- 용어는 `../docs/design-system/screens.md`, `../docs/reference/`, 백엔드 모듈명(auth, stores, catalog, reservations, payments)과 같은 말을 씁니다. 같은 실체에 두 이름을 만들지 않습니다(offer / discount 혼용 금지).
- pages slice 이름은 화면 ID가 아니라 뜻으로 짓고, 대응은 §7 표에 적습니다.

## 6. 절차

### 만들기
1. §4로 계층을 정하고 §5로 이름을 짓습니다.
2. 필요한 계층 폴더만 만들고(F4), `index.ts`를 둡니다.
3. §7 대응표에 행을 추가합니다.
4. `node .claude/skills/layer-check/check_layers.mjs`가 0건인지 확인합니다.

### 옮기기·나누기
1. 옮기기 전에 쓰는 곳을 찾습니다: `git grep -n "@/<계층>/<slice>" -- src` (Windows·macOS·Linux 공통. 아직 커밋하지 않은 새 파일도 찾으려면 `--untracked`를 붙입니다)
2. 공개 API 이름은 유지하고 import 경로만 바꿉니다.
3. 나눌 때는 행동(feature)과 개체(entity)를 기준으로 나눕니다. 파일 수로 나누지 않습니다.
4. §7 표와 설계안(`../docs/design/frontend/<slice>.md`)을 함께 고칩니다.

### 지우기
쓰는 곳이 0건인지 `git grep`으로 확인하고, §7 표와 설계안에서 지웠다고 표시합니다.

## 7. 화면 ↔ slice 대응표

slice를 만들 때마다 `fe-architect`가 이 표를 채웁니다. 화면 ID는 `../docs/design-system/screens.md`를 따릅니다.

| 화면 | pages slice | 쓰는 widgets / features / entities | 설계안 |
| --- | --- | --- | --- |
| (예) C2 할인 상세 | `pages/offer-detail` | `features/reserve-offer`, `entities/offer` | `../docs/design/frontend/offer-detail.md` |
