---
name: react-implementation
description: 마감 직전 프론트엔드(React + TypeScript + Vite)에서 컴포넌트, application 훅, domain 함수, React Router 라우팅, 폼, 테스트를 작성할 때 따르는 코드 패턴입니다. fetch + React 내장 상태(useState, useEffect, useReducer, Context)만으로 서버 데이터를 읽는 표준 훅(useAsync 패턴), 데이터를 바꾸는 요청 훅, AbortController 정리, 로딩·빈·에러 상태 분기, 역할별 라우트·셸, 폼 검증, Vitest + Testing Library 테스트 작성법을 다룹니다. React 코드를 새로 쓰거나 고칠 때 사용합니다.
---

# React 구현 패턴

배치 규칙은 `fsd-structure`·`layer-architecture`, 규칙 ID는 `frontend-invariants`가 정본입니다. 서버 데이터 라이브러리(TanStack Query 등)와 전역 상태 라이브러리는 쓰지 않습니다. fetch + React 내장 상태만 씁니다.

## 1. 공통
- TypeScript `strict`. `any`, `@ts-ignore`, 타입 단언(`as`)으로 오류를 덮지 않습니다(F16). 외부 입력은 infrastructure에서 좁힙니다.
- 컴포넌트는 함수 컴포넌트와 named export. 파일 하나에 공개 컴포넌트 하나, 파일명은 PascalCase(`OfferCard.tsx`).
- 훅은 `use`로 시작하고 camelCase 파일(`useOffers.ts`, 안에 `useNearbyOffers`·`useOfferDetail`). domain·infrastructure 파일도 camelCase.
- 스타일은 `bundle.css` 클래스와 토큰 변수만 씁니다(F12, `design-system-usage`). 인라인 `style`은 토큰 변수를 쓰는 레이아웃 값에만 씁니다.

## 2. 서버 데이터 읽기: 공용 훅

`shared/lib/useAsync.ts` 하나를 두고, slice의 application 훅은 이것을 감쌉니다. 같은 패턴을 화면마다 다시 쓰지 않습니다.

```ts
// shared/lib/useAsync.ts
import { useCallback, useEffect, useRef, useState } from 'react'

export type AsyncState<T> =
  | { status: 'loading'; data?: undefined; error?: undefined }
  | { status: 'error'; data?: undefined; error: unknown }
  | { status: 'success'; data: T; error?: undefined }

// key가 바뀌거나 reload()를 부르면 다시 불러온다.
export function useAsync<T>(load: (signal: AbortSignal) => Promise<T>, key: string) {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' })
  const [nonce, setNonce] = useState(0)
  const loadRef = useRef(load)

  useEffect(() => {
    loadRef.current = load
  })

  useEffect(() => {
    const ctrl = new AbortController()
    setState({ status: 'loading' })
    loadRef.current(ctrl.signal).then(
      (data) => { if (!ctrl.signal.aborted) setState({ status: 'success', data }) },
      (error) => { if (!ctrl.signal.aborted) setState({ status: 'error', error }) },
    )
    return () => ctrl.abort()
  }, [key, nonce])

  const reload = useCallback(() => setNonce((n) => n + 1), [])
  return { ...state, reload }
}
```

```ts
// features/offers/application/useOffers.ts
import { useDep } from '@/shared/lib/di'
import { useAsync } from '@/shared/lib/useAsync'
import { OfferRepositoryToken, type NearbyQuery } from '@/entities/offer'

export function useNearbyOffers(q: NearbyQuery) {
  const offers = useDep(OfferRepositoryToken)   // 포트만 받는다. 구현체(HttpOfferRepository)를 모른다
  return useAsync((signal) => offers.findNearby(q, signal), `${q.lat}|${q.lng}|${q.radiusKm}`)
}
```

- 포트·토큰·구현체·wiring 구조는 `layer-architecture` §6이 정본입니다(F18). application 코드에서 infrastructure를 import하지 않습니다.
- 다른 영역이 소유한 데이터(예: reservations 화면의 할인 정보)도 같은 방식으로 entities 토큰을 `useDep`해 읽습니다. 영역끼리 import하지 않습니다.
- 정리된 요청의 결과로 상태를 바꾸지 않습니다(F10). `signal`은 포트 → infrastructure → `shared/api`까지 넘깁니다.
- `key`는 요청을 결정하는 원시값을 이어 붙인 문자열입니다. 객체를 그대로 쓰면 렌더마다 다시 요청합니다.
- `eslint-disable`로 의존성 경고를 끄지 않습니다(F16). 경고가 나면 `key`를 다시 정합니다.
- 같은 데이터를 여러 화면이 쓰면 공통 조상(page 또는 `app/providers`의 Context)에서 한 번 불러 내려 줍니다. 캐시 계층을 직접 만들지 않습니다.

## 3. 상태 분기 (F10)

컴포넌트는 로딩·에러·빈·성공을 모두 그립니다. 표시 방식(Skeleton, EmptyState, Notice)과 문구는 `../docs/design-system/states.md`, `screens.md`의 E1을 따릅니다.

```tsx
export function OfferList({ query }: { query: NearbyQuery }) {
  const offers = useNearbyOffers(query)
  if (offers.status === 'loading') return <OfferListSkeleton />
  if (offers.status === 'error') return <LoadError error={offers.error} onRetry={offers.reload} />
  if (offers.data.length === 0) return <EmptyState title="주변에 할인 중인 상품이 없어요" />
  return <ul>{offers.data.map((o) => <li key={o.id}><OfferCard offer={o} /></li>)}</ul>
}
```
- 문구는 예시입니다. 실제 문구는 `screens.md` 그대로 씁니다(F13).
- 401은 화면마다 처리하지 않고 `shared/api`의 공통 처리(`api-client` §3)에 맡깁니다.

## 4. 데이터 바꾸기: 요청 훅

```ts
// features/reservations/application/reserveOffer.ts  (유스케이스: 포트만 받는 순수 함수)
import type { Reservation } from '../domain/reservation'
import type { ReservationRepository } from '../domain/reservationRepository'

export function reserveOffer(
  deps: { reservations: ReservationRepository },
  input: { offerId: string; quantity: number },
): Promise<Reservation> {
  return deps.reservations.create(input)
}

// features/reservations/application/useReserveOffer.ts  (훅: 포트를 꺼내 유스케이스에 넘기고 상태를 관리)
import { useState } from 'react'
import { useDep } from '@/shared/lib/di'
import type { Reservation } from '../domain/reservation'
import { ReservationRepositoryToken } from './tokens'
import { reserveOffer } from './reserveOffer'

export function useReserveOffer() {
  const reservations = useDep(ReservationRepositoryToken)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<unknown>(null)

  async function reserve(offerId: string, quantity: number): Promise<Reservation | null> {
    if (pending) return null              // 중복 제출 방지
    setPending(true); setError(null)
    try {
      return await reserveOffer({ reservations }, { offerId, quantity })
    } catch (e) {
      setError(e); return null
    } finally {
      setPending(false)
    }
  }
  return { reserve, pending, error }
}
```
- 제출 중에는 버튼을 비활성화합니다(`pending`). 결제·예약처럼 되돌리기 어려운 요청은 두 번 보내지 않습니다.
- 성공 후 이동(`navigate`)은 컴포넌트가 결과를 보고 합니다. 다른 화면 데이터의 갱신은 그 화면이 다시 마운트될 때 다시 불러오거나, 같은 화면이면 `reload()`를 부릅니다.
- 되돌리기 어려운 동작은 확인 화면을 거칩니다(디자인 시스템 원칙, `screens.md` C3a·C5a·C7 등).

## 5. 라우팅
- `app/router/`에서 `createBrowserRouter`로 라우트를 정의합니다. 라우트 요소는 `pages`의 공개 API만 씁니다.
- 역할별 셸(고객 / 상점주 / 관리자)은 레이아웃 라우트로 나눕니다(`../docs/design-system/layout.md`). 하위 화면(← 있는 화면)에는 TabBar가 없습니다.
- 로그인이 필요한 라우트는 레이아웃 라우트에서 가드합니다. 고객 홈(C1)은 비로그인으로 열립니다.
- URL 파라미터·쿼리는 page에서 읽어 아래로 인자로 넘깁니다. features·entities는 `useParams`를 직접 쓰지 않습니다.
- 정적 배포라 SPA fallback이 필요합니다(`frontend/README.md` 배포 절).

## 6. 폼
- 입력값은 `useState`(필드가 많으면 `useReducer`)로 다룹니다. 폼 라이브러리는 쓰지 않습니다.
- 검증 규칙(이메일 형식, 비밀번호 길이, 수량 범위)은 domain 함수로 두고 컴포넌트는 결과만 표시합니다(F7).
- 서버 검증 에러(`VALIDATION_ERROR` 등)는 `ApiError.errorCode`로 분기해 필드 아래에 표시합니다(F11).
- 숫자 입력은 Stepper 컴포넌트 규칙(`../docs/design-system/components/Stepper/README.md`)을 따릅니다.

## 7. 테스트 (Vitest + Testing Library)

| 대상 | 방법 | 위치 |
| --- | --- | --- |
| domain 함수 | 순수 함수 단위 테스트. 경계값(0, 마감 시각 정각, 재고 1) 포함 | `<slice>/domain/*.test.ts` |
| infrastructure 구현체 | `shared/api`를 `vi.mock`하고 DTO → domain 변환, 엔드포인트·쿼리 확인 | `<slice>/infrastructure/*.test.ts` |
| application 유스케이스 | 포트에 가짜 객체를 넘겨 호출 순서·결과 확인 (React 없음) | `<slice>/application/*.test.ts` |
| application 훅 | 가짜 구현체로 만든 `Container`를 `DepsProvider`로 감싸 `renderHook`. 로딩 → 성공/에러 전이, 언마운트 시 abort | `<slice>/application/*.test.ts` |
| presentation | 가짜 구현체 `DepsProvider` + `render` + `screen.getByRole`. 로딩·빈·에러·성공 네 상태를 모두 확인 | `<slice>/presentation/*.test.tsx` |
| 조립 | `createContainer()`가 중복 없이 만들어지고 핵심 토큰이 풀리는지 | `src/app/container.test.ts` |

- application·presentation 테스트에서 `vi.mock`으로 모듈을 바꾸지 않습니다. 포트에 가짜 구현체를 넣습니다(`layer-architecture` §6.8). `vi.mock`은 infrastructure 테스트의 `shared/api`에만 씁니다.

- 시각은 `vi.useFakeTimers()`와 `vi.setSystemTime()`으로 고정하거나 domain에 `now`를 넘깁니다.
- 요소는 역할·이름(`getByRole('button', { name: '예약하고 결제' })`)으로 찾습니다. 클래스명이나 test-id에 기대지 않습니다.
- 화면 흐름 E2E는 Playwright로 작성합니다(`qa-verification` §4).
