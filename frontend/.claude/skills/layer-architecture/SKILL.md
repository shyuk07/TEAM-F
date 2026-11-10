---
name: layer-architecture
description: 마감 직전 프론트엔드에서 FSD slice(pages, widgets, features, entities) 안을 나누는 4계층(presentation, application, domain, infrastructure)의 책임, 의존 방향, 계층별로 둘 것과 두지 않을 것, 계층 판단 예시를 정합니다. slice 안에 코드를 어디에 둘지 정할 때, 컴포넌트·훅·도메인 함수·API 함수를 나눌 때, 계층 간 import가 허용되는지 판단할 때 사용합니다. slice를 어느 FSD 계층에 둘지는 fsd-structure, 코드 패턴은 react-implementation, 자동 검사는 layer-check를 씁니다.
---

# slice 안 4계층

이 스킬은 **slice 안에서 무엇을 어디에 두고 왜 그렇게 하는가**를 정합니다. 규칙 ID(F4~F10)는 `frontend-invariants`가 정본입니다.

## 1. 계층 책임

| 계층 | 책임 | 파일 예시 | 두지 않는 것 |
| --- | --- | --- | --- |
| presentation | 그리기, 사용자 입력 받기, 로딩·에러·빈 상태 표시 | `OfferCard.tsx`, `ReserveButton.tsx` | fetch, 비즈니스 계산, DTO |
| application | 유스케이스 흐름. 서버 호출 조합, 비동기 상태(로딩·에러·데이터), 성공 후 다음 동작 | `useOffers.ts`, `useReserveOffer.ts` | JSX, 금액·시간 계산 규칙 |
| domain | 타입, 업무 규칙, 계산, 표기 변환. 순수 함수 | `offer.ts`(`Offer` 타입, `minutesUntilClose`, `canReserve`) | React, fetch, 브라우저 API, env |
| infrastructure | 서버 API 호출 함수, DTO 타입, DTO → domain 변환 | `offerApi.ts`(`fetchOffers`, `toOffer`) | React, 상태, 화면 문구 |

FSD 세그먼트 이름(`ui`, `model`, `api`, `lib`)은 slice 안에서 쓰지 않습니다(F4). 쓰지 않는 계층 폴더는 만들지 않습니다.

## 2. 의존 방향 (F5)

```text
presentation ──▶ application ──▶ infrastructure
     │                │                │
     └───────────────▶▼◀───────────────┘
                    domain
```

| 계층 | import할 수 있는 slice 안 계층 | 그 외 |
| --- | --- | --- |
| presentation | application, domain | 아래 FSD 계층의 공개 API, `shared/ui`, `shared/lib` |
| application | domain, infrastructure | 아래 FSD 계층의 공개 API, `shared/lib`, `react` |
| infrastructure | domain | `shared/api`, `shared/config` |
| domain | 없음 | 아래 FSD 계층 공개 API의 **타입과 순수 함수**, `shared/lib`의 순수 함수 |

- presentation은 infrastructure를 import하지 않습니다. 서버 호출은 반드시 application 훅을 거칩니다.
- 왜: 화면이 서버 형식을 모르면, 백엔드 응답이 바뀌어도 infrastructure의 변환 함수 하나만 고치면 됩니다.
- application이 infrastructure 함수를 직접 부르는 것은 허용합니다. 이 프로젝트는 fetch + React 내장 상태만 쓰므로 주입 계층을 따로 두지 않습니다. 테스트에서는 `vi.mock`으로 infrastructure 모듈을 바꿉니다.

## 3. domain 순수성 (F6, F7)

- domain 파일은 Node에서 React·브라우저 없이 import하고 테스트할 수 있어야 합니다.
- 현재 시각이 필요한 규칙은 `now: Date`를 인자로 받습니다. 함수 안에서 `new Date()`를 부르지 않습니다(테스트 고정이 어려움).
- 화면에 보일 계산값(할인율, "판매 마감 N분 전", 상태 문구)은 `../docs/design-system/states.md`의 "화면에서 계산하는 값"을 domain 함수로 만듭니다.

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

| 코드 | 계층 | 이유 |
| --- | --- | --- |
| `GET /v1/offers` 호출과 응답 → `Offer[]` 변환 | infrastructure | 서버 형식을 아는 유일한 곳 |
| `useOffers()`가 로딩·에러·데이터를 돌려줌 | application | 비동기 흐름 |
| 재고 0이면 예약 버튼 비활성 판단 | domain(`canReserve`) | 업무 규칙 |
| 비활성 버튼을 `btn` 클래스로 그림 | presentation | 그리기 |
| 예약 성공 후 결제 화면(C3)으로 이동 | application(훅이 `onSuccess` 콜백 또는 결과 반환) + presentation(`navigate`) | 흐름은 훅, 라우터 호출은 컴포넌트 |
| `RESERVATION_CLOSED` 에러를 화면 문구로 바꿈 | domain(코드 → 문구 표) 또는 presentation(`content.md` 문구) | 화면 명세에 따라 |

## 5. 설계안에 적을 것

`fe-architect`는 `../docs/design/frontend/<slice>.md`에 slice마다 아래를 적습니다.
1. FSD 계층과 slice 이름, 대응 화면 ID
2. 계층별 파일 목록과 각 파일의 export
3. domain 타입·규칙 함수와 입력·출력, 경계값
4. infrastructure: 엔드포인트, DTO 필드 ↔ domain 필드 대응
5. application 훅이 돌려주는 값(데이터·로딩·에러)과 성공·실패 후 동작
6. presentation: 화면 상태(로딩·빈·에러·권한 없음)별 표시와 사용하는 디자인 시스템 컴포넌트
7. 공개 API(`index.ts`) 목록
8. 결정 표: `D-번호 | 항목 | 값 | 임시/확정 | 근거`. 설계자가 정한 값은 "임시", 사용자가 정한 값만 "확정"
9. 정합 이슈: `C-번호 | 내용 | 양쪽 근거(파일:절)`. 명세 ↔ 백엔드 코드, 화면 명세 ↔ API 명세, 다른 slice 설계안과의 불일치, 요청 범위를 넘은 추가
10. 차단 이슈와 질문 목록: 명세·디자인 문서의 "확인 필요", 백엔드에 없는 엔드포인트, `open-issues.md` 항목

D-번호·C-번호는 설계안 파일 안에서 1부터 매기고, 한 번 매긴 번호는 바꾸거나 다시 쓰지 않습니다. 다른 파일에서 가리킬 때는 `<slice>.md D-3`처럼 파일명과 함께 씁니다.
