---
name: layer-architecture
description: 마감 직전 프론트엔드에서 FSD slice(pages, widgets, features, entities) 안을 나누는 4계층(presentation, application, domain, infrastructure)의 책임과 의존 방향, 그리고 의존성 역전·주입 구조를 정합니다. domain 포트(저장소 등)와 application 포트(유스케이스 전용 기능)로 추상화하고, 소유 영역(features/<영역>)의 infrastructure에서 구현하며, 영역별 features/<영역>/wiring.ts와 app/container.ts에서 토큰 기반 Context로 조립합니다. slice 안에 코드를 어디에 둘지 정할 때, 포트·구현체·wiring을 만들 때, 계층 간 import가 허용되는지 판단할 때, 테스트에서 가짜 구현체를 넣을 때 사용합니다. slice를 어느 FSD 계층·영역에 둘지는 fsd-structure, 코드 패턴은 react-implementation, 자동 검사는 layer-check를 씁니다.
---

# slice 안 4계층과 의존성 주입

이 스킬은 **slice 안에서 무엇을 어디에 두고, 계층끼리 어떻게 약하게 연결하는가**를 정합니다. 규칙 ID(F4~F10, F18)는 `frontend-invariants`가 정본입니다. features는 업무 영역 7개(auth, stores, products, offers, reservations, payments, admin)이며, 영역 목록과 배치 기준은 `fsd-structure` §1.1이 정본입니다.

**의존성 주입(§6)은 이 스킬이 정본입니다.** 다른 스킬의 코드 예시가 이 절과 다르면 이 절을 따르고 그 예시를 고칩니다.

## 1. 계층 책임

| 계층 | 책임 | 파일 예시 | 두지 않는 것 |
| --- | --- | --- | --- |
| presentation | 그리기, 사용자 입력 받기, 로딩·에러·빈 상태 표시 | `OfferCard.tsx`, `ReserveButton.tsx` | fetch, 비즈니스 계산, DTO, 구현체 |
| application | 유스케이스 흐름(순수 함수), React 훅, **application 포트**(유스케이스만 필요로 하는 기능의 추상)와 주입 토큰 | `reserveOffer.ts`, `useReserveOffer.ts`, `ports.ts`, `tokens.ts` | JSX, 금액·시간 계산 규칙, 구현체 |
| domain | 타입, 업무 규칙, 계산, 표기 변환, **domain 포트**(도메인 데이터 접근의 추상) | `offer.ts`, `offerRepository.ts` | React, fetch, 브라우저 API, env, 토큰 |
| infrastructure | 포트의 구현체. 서버 API 호출, DTO 타입, DTO → domain 변환, 브라우저 API 사용. **features 영역에만 둠** | `httpOfferRepository.ts`, `localSessionStore.ts` | React, 상태, 화면 문구 |
| `wiring.ts` (features 영역 루트) | 이 영역의 구현체를 만들어 토큰에 연결 | `features/offers/wiring.ts` | 업무 로직 |
| `index.ts` (slice 루트) | 공개 API. 타입·포트·토큰·훅·컴포넌트만 내보냄 | `index.ts` | 구현체, wiring |

- FSD 세그먼트 이름(`ui`, `model`, `api`, `lib`)은 slice 안에서 쓰지 않습니다(F4). 쓰지 않는 계층 폴더는 만들지 않습니다.
- **entities에는 infrastructure와 wiring을 두지 않습니다.** entities는 영역끼리 공유하는 타입·규칙·포트·토큰·표시 부품만 갖고, 그 포트의 구현체는 개체를 소유한 영역에 둡니다(`fsd-structure` §1.1).

## 2. 의존 방향 (F5)

```text
                 presentation
                      │
                      ▼
 infrastructure ┈┈▶ application        ┈┈▶ : 포트 타입만 (import type)
      │                │
      └──────▶ domain ◀┘

 features/<영역>/wiring.ts ──▶ 자기 영역의 모든 계층 · entities 공개 API(토큰)
                                                      (구현체를 고르는 영역 단위의 유일한 곳)
 app/container.ts ──▶ 7개 영역의 wiring.ts            (영역별 wiring을 모으는 앱의 유일한 곳)
```

| 계층 | import할 수 있는 slice 안 계층 | 그 외 |
| --- | --- | --- |
| presentation | application, domain | 아래 FSD 계층의 공개 API, `shared/ui`, `shared/lib` |
| application | domain | 아래 FSD 계층의 공개 API, `shared/lib`, `react` |
| infrastructure | domain, application(**`import type`만**) | entities 공개 API(포트 타입), `shared/api`, `shared/config`, `shared/lib` |
| domain | 없음 | 아래 FSD 계층 공개 API의 **타입과 순수 함수**, `shared/lib`의 순수 함수 |
| `wiring.ts` (features만) | 모든 계층 | `shared/lib/di`, entities 공개 API(토큰) |

- **application은 infrastructure를 import하지 않습니다.** 필요한 기능은 포트(추상)로 선언하고, 토큰으로 주입받습니다.
- **infrastructure는 application의 포트 타입만** 가져옵니다(`import type`). 실행 코드를 가져오면 application이 바뀔 때 구현체도 함께 바뀌는 강한 결합이 됩니다.
- presentation은 infrastructure를 import하지 않습니다. 서버 호출은 반드시 application 훅을 거칩니다.
- **영역끼리는 import하지 않습니다(F1).** 다른 영역의 데이터는 entities의 포트·토큰으로 받습니다(`fsd-structure` §2).
- 이렇게 하면 **어느 계층도, 어느 영역도 다른 쪽의 구현을 모릅니다.** 서버 형식이 바뀌면 그 영역의 infrastructure 하나, 저장 방식(localStorage → 쿠키)이 바뀌면 구현체와 그 영역 wiring 한 줄만 고칩니다.

## 3. domain 순수성 (F6, F7)

- domain 파일은 Node에서 React·브라우저 없이 import하고 테스트할 수 있어야 합니다.
- 현재 시각이 필요한 규칙은 `now: Date`를 인자로 받습니다. 함수 안에서 `new Date()`를 부르지 않습니다(테스트 고정이 어려움).
- 화면에 보일 계산값(할인율, "판매 마감 N분 전", 상태 문구)은 `../docs/design-system/states.md`의 "화면에서 계산하는 값"을 domain 함수로 만듭니다.
- domain 포트는 순수 TypeScript `interface`입니다. 토큰(DI 도구)은 domain에 두지 않고 application에 둡니다.

```ts
// entities/offer/domain/offer.ts
export type Offer = { id: string; price: number; discountPrice: number; closesAt: Date; stock: number }

export function discountRate(o: Offer): number {
  return Math.round((1 - o.discountPrice / o.price) * 100)
}

export function minutesUntilClose(o: Offer, now: Date): number {
  return Math.max(0, Math.floor((o.closesAt.getTime() - now.getTime()) / 60000))
}

export function canReserve(o: Offer, now: Date): boolean {
  return o.stock > 0 && minutesUntilClose(o, now) > 0
}
```

## 4. 계층 판단 예시

| 코드 | 위치 | 이유 |
| --- | --- | --- |
| `Offer` 타입, `canReserve` | `entities/offer/domain` | offers·reservations 두 영역이 씀 |
| `OfferRepository` 인터페이스(`findNearby`, `findById`) | `entities/offer/domain` (domain 포트) | 도메인 데이터 접근의 추상. reservations도 씀 |
| `GET /v1/offers` 호출과 응답 → `Offer[]` 변환 (`HttpOfferRepository`) | `features/offers/infrastructure` | offer를 소유한 영역. 서버 형식을 아는 유일한 곳 |
| `StockAdjustment` 포트(재고 조정, O10) | `features/offers/domain` | offers 영역만 씀. 공유하지 않으면 entities로 내리지 않음 |
| `SessionStore` 인터페이스(`save`, `clear`, `hasSession`) | `entities/session/application` (application 포트) | 도메인 규칙과 무관한 기술 기능. auth·app 인증 Context 등이 씀 |
| `localStorage` 사용 (`LocalSessionStore`) | `features/auth/infrastructure` | session을 소유한 영역. 브라우저 기술 |
| `reserveOffer(deps, input)` 유스케이스 | `features/reservations/application` | 흐름. 포트만 받음 |
| `useNearbyOffers()`가 로딩·에러·데이터를 돌려줌 | `features/offers/application` | 비동기 흐름. 포트는 `useDep(토큰)`으로 받음 |
| 비활성 버튼을 `btn` 클래스로 그림 | presentation | 그리기 |
| 예약 성공 후 결제 화면(C3)으로 이동 | application(결과 반환) + presentation(`navigate`) | 흐름은 훅, 라우터 호출은 컴포넌트 |
| `RESERVATION_CLOSED` 에러를 화면 문구로 바꿈 | domain(코드 → 문구 표) 또는 presentation(`content.md` 문구) | 화면 명세에 따라 |
| `new HttpOfferRepository()` | `features/offers/wiring.ts` | 구현체 생성은 소유 영역의 조립 지점에서만 |

## 5. 설계안에 적을 것

`fe-architect`는 `../docs/design/frontend/<slice>.md`(영역이면 `<영역>.md`, 예: `offers.md`)에 slice마다 아래를 적습니다.
1. FSD 계층과 slice 이름, 대응 화면 ID
2. 계층별 파일 목록과 각 파일의 export
3. domain 타입·규칙 함수와 입력·출력, 경계값
4. 포트 목록: 이름, 위치(이 영역 / entities, domain / application), 메서드 시그니처, 토큰 이름, 구현체 이름과 소유 영역
5. infrastructure: 엔드포인트, DTO 필드 ↔ domain 필드 대응
6. application 유스케이스·훅이 받는 포트와 돌려주는 값(데이터·로딩·에러), 성공·실패 후 동작
7. presentation: 화면 상태(로딩·빈·에러·권한 없음)별 표시와 사용하는 디자인 시스템 컴포넌트
8. 공개 API(`index.ts`) 목록. 영역이면 `wiring.ts`가 등록하는 토큰과 구현체 목록
9. 결정 표: `D-번호 | 항목 | 값 | 임시/확정 | 근거`. 설계자가 정한 값은 "임시", 사용자가 정한 값만 "확정"
10. 정합 이슈: `C-번호 | 내용 | 양쪽 근거(파일:절)`. 명세 ↔ 백엔드 코드, 화면 명세 ↔ API 명세, 다른 slice 설계안과의 불일치, 요청 범위를 넘은 추가
11. 차단 이슈와 질문 목록: 명세·디자인 문서의 "확인 필요", 백엔드에 없는 엔드포인트, `open-issues.md` 항목

D-번호·C-번호는 설계안 파일 안에서 1부터 매기고, 한 번 매긴 번호는 바꾸거나 다시 쓰지 않습니다. 다른 파일에서 가리킬 때는 `<slice>.md D-3`처럼 파일명과 함께 씁니다.

## 6. 추상화와 의존성 주입 (F18)

백엔드의 `domain/repository.py`(추상) → `infrastructure/`(구현) → `src/container.py`(조립)와 같은 구조입니다. React에는 FastAPI `Depends`가 없으므로 **토큰 + Context**로 주입합니다.

| 백엔드 | 프론트 |
| --- | --- |
| 모듈 (`src/<모듈>/`) | 영역 (`features/<영역>/`) |
| `domain/repository.py` (ABC) | `domain/<이름>Repository.ts` (`interface`). 영역끼리 공유하면 `entities/<개체>/domain/` |
| `domain/service.py` (ABC) | `application/ports.ts` (`interface`, 유스케이스 전용) |
| `infrastructure/repositories.py` | `features/<영역>/infrastructure/http<이름>Repository.ts` |
| `presentation/dependencies.py`의 `provide_*` 자리표시자 | `application/tokens.ts`의 토큰 |
| `src/container.py`의 모듈 구역 | `features/<영역>/wiring.ts` |
| `wire_dependencies()` | `app/container.ts`의 `createContainer()` |
| `Depends(provide_*)` | `useDep(토큰)` |

### 6.1 DI 도구 — `shared/lib/di.ts` + `shared/lib/DepsProvider.tsx` (업무를 모름, 한 벌만 둠)

컴포넌트(`DepsProvider`)는 따로 `DepsProvider.tsx`에 둡니다. 한 파일이 컴포넌트와 함수를 함께 내보내면 Fast Refresh가 깨지고 ESLint `react-refresh/only-export-components`에 걸립니다. 규칙을 끄지 않고 파일을 나눕니다.

```ts
// shared/lib/di.ts
import { createContext, useContext } from 'react'

export type Token<T> = { readonly key: symbol; readonly name: string; readonly _type?: T }
export function createToken<T>(name: string): Token<T> {
  return { key: Symbol(name), name }
}

export type Binding = { readonly token: Token<unknown>; readonly value: unknown }
export function bind<T>(token: Token<T>, value: T): Binding {
  return { token, value }
}

export class Container {
  private readonly map = new Map<symbol, unknown>()
  constructor(bindings: readonly Binding[]) {
    for (const b of bindings) {
      if (this.map.has(b.token.key)) throw new Error(`의존성 중복 등록: ${b.token.name} (토큰은 소유 영역 한 곳에서만 등록)`)
      this.map.set(b.token.key, b.value)
    }
  }
  get<T>(token: Token<T>): T {
    if (!this.map.has(token.key)) throw new Error(`의존성 미등록: ${token.name} (소유 영역의 wiring.ts와 app/container.ts 확인)`)
    return this.map.get(token.key) as T
  }
}

export const DepsContext = createContext<Container | null>(null)

export function useDep<T>(token: Token<T>): T {
  const container = useContext(DepsContext)
  if (!container) throw new Error('DepsProvider 밖에서 useDep를 호출했습니다.')
  return container.get(token)
}
```

```tsx
// shared/lib/DepsProvider.tsx
import type { ReactNode } from 'react'
import { DepsContext, type Container } from './di'

export function DepsProvider({ container, children }: { container: Container; children: ReactNode }) {
  return <DepsContext.Provider value={container}>{children}</DepsContext.Provider>
}
```
- 가져오는 곳: 토큰·`bind`·`Container`·`useDep`은 `@/shared/lib/di`, `DepsProvider`는 `@/shared/lib/DepsProvider`.
- `shared`는 업무를 모르므로 어떤 포트·토큰도 import하지 않습니다. slice별 타입은 토큰의 제네릭(`Token<OfferRepository>`)이 들고 다닙니다.
- **토큰 하나는 정확히 한 영역이 등록합니다.** 두 번 등록하면 앱 시작 때 "의존성 중복 등록" 오류가 납니다.
- 컨테이너는 앱 시작 때 한 번 만들고 바꾸지 않습니다. 렌더 중에 만들지 않습니다.

### 6.2 domain 포트 — 도메인 데이터 접근

```ts
// entities/offer/domain/offerRepository.ts  (offers·reservations가 함께 쓰므로 entities)
import type { Offer } from './offer'

export type NearbyQuery = { lat: number; lng: number; radiusKm: number }

export interface OfferRepository {
  findNearby(q: NearbyQuery, signal?: AbortSignal): Promise<Offer[]>
  findById(id: string, signal?: AbortSignal): Promise<Offer>
}
```
- 도메인 객체만 주고받습니다. DTO, `Response`, URL을 노출하지 않습니다.
- 이름은 `<개체>Repository`, 메서드는 `find*`·`save`·`create`·`cancel`처럼 업무 동사로 짓습니다.
- 한 영역만 쓰는 포트는 그 영역의 `domain/`에 둡니다. 두 번째 영역이 필요로 할 때 entities로 내립니다(`fsd-structure` §6).

### 6.3 application 포트와 토큰

```ts
// entities/session/application/ports.ts  (auth 영역과 app 인증 Context 등이 함께 씀)
export interface SessionStore {
  save(accessToken: string): void
  clear(): void
  hasSession(): boolean
}

// entities/session/application/tokens.ts
import { createToken } from '@/shared/lib/di'
import type { SessionStore } from './ports'
export const SessionStoreToken = createToken<SessionStore>('SessionStore')

// entities/offer/application/tokens.ts
import { createToken } from '@/shared/lib/di'
import type { OfferRepository } from '../domain/offerRepository'
export const OfferRepositoryToken = createToken<OfferRepository>('OfferRepository')
```
- **포트 위치 기준:** 도메인 데이터를 읽고 쓰는 추상은 domain, 도메인 규칙과 무관하게 유스케이스만 필요로 하는 기술 기능(세션 저장, 현재 위치, 클립보드)은 application에 둡니다.
- **토큰은 포트와 같은 slice의 `application/tokens.ts`에 둡니다.** domain 포트의 토큰도 application에 둡니다(domain을 DI 도구로부터 지키기 위해).
- 포트 하나에 토큰 하나. 토큰 이름은 `<포트이름>Token`, `createToken`의 문자열은 포트 이름과 같게 짓습니다(오류 메시지에 쓰임).

### 6.4 유스케이스와 훅 — 포트만 받는다

```ts
// features/auth/application/login.ts  (순수 함수: React 없이 테스트)
import type { SessionStore } from '@/entities/session'
import type { AuthGateway, LoginResult } from './ports'

export async function login(
  deps: { auth: AuthGateway; session: SessionStore },
  input: { email: string; password: string },
): Promise<LoginResult> {
  const result = await deps.auth.login(input.email, input.password)
  deps.session.save(result.accessToken)
  return result
}

// features/auth/application/useLogin.ts  (React 연결)
import { useDep } from '@/shared/lib/di'
import { SessionStoreToken } from '@/entities/session'
import { AuthGatewayToken } from './tokens'
import { login } from './login'

export function useLogin() {
  const auth = useDep(AuthGatewayToken)
  const session = useDep(SessionStoreToken)
  // pending·error 상태 처리는 react-implementation §4
  return (email: string, password: string) => login({ auth, session }, { email, password })
}
```
- 유스케이스 함수는 첫 인자로 필요한 포트 묶음(`deps`)만 받습니다. 구현체를 만들거나 기본값을 두지 않습니다(백엔드 스킬 `../backend/.claude/skills/layer-architecture/SKILL.md` §5.4와 같음).
- 훅은 `useDep`로 포트를 꺼내 유스케이스에 넘기는 얇은 연결만 합니다.
- 다른 영역의 데이터가 필요하면 entities의 포트·토큰을 씁니다. 예: `features/reservations`의 훅이 `useDep(OfferRepositoryToken)`으로 할인 정보를 읽음(구현체는 offers 영역이 등록).

### 6.5 구현체 — 소유 영역의 infrastructure

```ts
// features/offers/infrastructure/httpOfferRepository.ts
import { apiGet } from '@/shared/api/client'
import type { NearbyQuery, Offer, OfferRepository } from '@/entities/offer'

type OfferDto = { id: string; price: number; discount_price: number; closes_at: string; stock: number }
const toOffer = (d: OfferDto): Offer => ({
  id: d.id, price: d.price, discountPrice: d.discount_price, closesAt: new Date(d.closes_at), stock: d.stock,
})

export class HttpOfferRepository implements OfferRepository {
  async findNearby(q: NearbyQuery, signal?: AbortSignal) {
    const qs = new URLSearchParams({ lat: String(q.lat), lng: String(q.lng), radius_km: String(q.radiusKm) })
    return (await apiGet<OfferDto[]>(`/v1/offers?${qs}`, signal)).map(toOffer)
  }
  async findById(id: string, signal?: AbortSignal) {
    return toOffer(await apiGet<OfferDto>(`/v1/offers/${encodeURIComponent(id)}`, signal))
  }
}

// features/auth/infrastructure/localSessionStore.ts
import { clearToken, readToken, saveToken } from '@/shared/api/tokenStorage'
import type { SessionStore } from '@/entities/session'

export class LocalSessionStore implements SessionStore {
  save(accessToken: string) { saveToken(accessToken) }
  clear() { clearToken() }
  hasSession() { return readToken() !== null }
}
```
- 구현체는 그 개체를 소유한 영역(`fsd-structure` §1.1 "구현을 맡는 entities")의 infrastructure에만 둡니다.
- 이름은 `<기술><포트이름>`(`HttpOfferRepository`, `LocalSessionStore`, `BrowserLocationProvider`).
- `implements`를 반드시 씁니다. 포트가 바뀌면 타입 검사가 구현체를 잡아냅니다.
- 같은 영역의 application 포트를 구현할 때는 `import type`으로만 가져옵니다(F5).
- 필드는 예시입니다. 실제 필드는 `api-client` §5로 명세를 확인합니다.

### 6.6 조립 — 영역별 `features/<영역>/wiring.ts`

```ts
// features/auth/wiring.ts
import { bind, type Binding } from '@/shared/lib/di'
import { SessionStoreToken } from '@/entities/session'
import { AuthGatewayToken } from './application/tokens'
import { HttpAuthGateway } from './infrastructure/httpAuthGateway'
import { LocalSessionStore } from './infrastructure/localSessionStore'

export function wireAuth(): Binding[] {
  return [
    bind(AuthGatewayToken, new HttpAuthGateway()),       // 이 영역의 포트
    bind(SessionStoreToken, new LocalSessionStore()),    // 이 영역이 소유한 entities 포트
  ]
}

// features/offers/wiring.ts
export function wireOffers(): Binding[] {
  return [bind(OfferRepositoryToken, new HttpOfferRepository())]
}
```
- 영역의 wiring은 **이 영역의 포트**와 **이 영역이 소유한 entities 포트**(`fsd-structure` §1.1)를 등록합니다. 다른 영역이 소유한 토큰은 등록하지 않습니다.
- wiring이 가져오는 구현체는 자기 영역의 infrastructure뿐입니다. 다른 slice에서는 토큰(공개 API)만 가져옵니다.
- 함수 이름은 `wire<영역>`(`wireAuth`, `wireOffers`), 반환 타입은 `Binding[]`입니다. `bind`가 토큰 타입과 구현체 타입을 컴파일 때 맞춰 봅니다.
- 상태 없는 구현체는 여기서 한 번 만들어 앱 전체가 같이 씁니다(백엔드의 싱글턴 유틸과 같음).
- `wiring.ts`는 `index.ts`로 다시 내보내지 않습니다. 가져올 수 있는 곳은 `app/container.ts`뿐입니다(F18, `[wiring위치]`).

### 6.7 앱 조립 — `app/container.ts`

```ts
// app/container.ts
import { Container } from '@/shared/lib/di'
import { wireAdmin } from '@/features/admin/wiring'
import { wireAuth } from '@/features/auth/wiring'
import { wireOffers } from '@/features/offers/wiring'
import { wirePayments } from '@/features/payments/wiring'
import { wireProducts } from '@/features/products/wiring'
import { wireReservations } from '@/features/reservations/wiring'
import { wireStores } from '@/features/stores/wiring'

export function createContainer(): Container {
  return new Container([
    ...wireAuth(),
    ...wireStores(),
    ...wireProducts(),
    ...wireOffers(),
    ...wireReservations(),
    ...wirePayments(),
    ...wireAdmin(),
  ])
}

// main.tsx  (DepsProvider는 '@/shared/lib/DepsProvider'에서 import)
const container = createContainer()
createRoot(document.getElementById('root')!).render(
  <DepsProvider container={container}><App /></DepsProvider>,
)
```
- 영역은 7개로 고정이므로 이 파일은 영역이 생길 때만 바뀝니다. 순서는 상관없습니다.
- 등록을 빠뜨리면 그 포트를 쓰는 화면이 처음 렌더될 때 "의존성 미등록: <이름>" 오류가 납니다. `tests/app/container.test.ts`(§6.8)와 E2E로 잡습니다.

### 6.8 테스트 — 가짜 구현체를 넣는다

```ts
// 유스케이스: 포트에 가짜 객체를 넘긴다 (React·네트워크 없음)
const session = { save: vi.fn(), clear: vi.fn(), hasSession: () => false }
await login({ auth: fakeAuth, session }, { email: 'a@b.c', password: 'pw' })
expect(session.save).toHaveBeenCalledWith('token-1')

// 훅·컴포넌트: 가짜 구현체로 만든 컨테이너로 감싼다
const wrapper = ({ children }: { children: ReactNode }) => (
  <DepsProvider container={new Container([bind(OfferRepositoryToken, fakeOfferRepository)])}>{children}</DepsProvider>
)
renderHook(() => useNearbyOffers(query), { wrapper })

// 조립: 앱 컨테이너가 중복 없이 만들어지고, entities 토큰이 모두 풀리는지
const c = createContainer()
for (const token of [SessionStoreToken, OfferRepositoryToken /* entities 토큰 전부 */]) {
  expect(() => c.get(token)).not.toThrow()
}
```
- application·presentation 테스트에서 `vi.mock`으로 모듈을 바꾸지 않습니다. 포트에 가짜 구현체를 넣습니다.
- `vi.mock`은 infrastructure 테스트에서 `shared/api`를 바꿀 때만 씁니다.
- 가짜 구현체는 테스트 파일 안이나 `tests/<계층>/<slice>/fakes/*.fake.ts`에 둡니다(`react-implementation` §7). 운영 코드에서 import하지 않습니다.

### 6.9 새 포트 체크리스트
1. 위치를 정한다: 도메인 데이터 접근이면 domain, 유스케이스 전용 기술 기능이면 application (§6.3)
2. 쓰는 영역을 정한다: 한 영역만 쓰면 그 영역 안, 두 영역 이상이면 `entities/<개체>` (`fsd-structure` §4)
3. `interface`를 만들고, 같은 slice의 `application/tokens.ts`에 토큰을 만든다
4. 소유 영역의 infrastructure에 `implements` 구현체를 만든다
5. 소유 영역의 `wiring.ts`에서 `bind`한다 (토큰당 한 곳)
6. entities 포트면 `fsd-structure` §1.1 "구현을 맡는 entities"에 적고 `tests/app/container.test.ts`의 토큰 목록에 추가한다
7. 다른 slice가 쓸 포트면 `index.ts`에서 포트 타입과 토큰을 내보낸다 (구현체·wiring은 내보내지 않음)
8. `node .claude/skills/layer-check/check_layers.mjs`가 0건인지 확인한다
