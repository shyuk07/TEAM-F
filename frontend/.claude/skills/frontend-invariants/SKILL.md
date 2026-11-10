---
name: frontend-invariants
description: 마감 직전 프로젝트의 프론트엔드(React + TypeScript + Vite) 코드가 어떤 작업에서도 지켜야 하는 불변 규칙(F1~F18)과 코드 작업 공통 완료 게이트의 정본입니다. FSD 계층·slice 공개 API, slice 안 4계층 의존 방향, domain 순수성, fetch 위치, 응답 변환, 비동기 상태 처리, 디자인 시스템·화면 문구·API 명세 일치, 시크릿·의존성·테스트 규칙을 F번호로 정의하고 검사 방법과 상세 위치를 안내합니다. 코드를 설계·구현·리뷰·점검·검증할 때, 발주서에 지킬 규칙을 ID로 넘길 때, 위반을 F번호로 보고할 때 사용합니다.
---

# 프론트엔드 불변 규칙

이 문서는 **규칙의 정본**입니다. 다른 스킬과 에이전트 명세는 규칙 문장을 다시 쓰지 않고 `F번호`로 가리킵니다.
- 규칙을 바꿀 때는 이 문서만 고칩니다.
- FSD 배치: `fsd-structure` / slice 안 4계층: `layer-architecture` / 코드 패턴: `react-implementation` / API: `api-client` / 디자인: `design-system-usage` / 자동 검사: `layer-check`
- 발주서에는 "F1~F18 준수"처럼 ID로 적고, 위반은 `F번호`로 보고합니다.

검사 방법 표기: **자동**(`check_layers.mjs`가 잡음, 괄호 안은 출력 태그) / **도구**(ESLint·Prettier·tsc·Vitest·Playwright) / **정독**(`fe-architect`·`fe-reviewer`가 코드를 읽어 판정) / **실행**(`fe-qa`가 실행해 판정)

## 1. FSD 계층 (바깥 구조)

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| F1 | 계층 순서는 `app > pages > widgets > features > entities > shared`이다. 위 계층만 아래 계층을 import한다. 같은 계층의 다른 slice를 import하지 않는다. | 자동(`[계층방향]`, `[같은계층]`) | `fsd-structure` §2 |
| F2 | slice 밖에서는 그 slice의 공개 API(`<계층>/<slice>/index.ts`)로만 import한다. slice 내부 경로(`@/features/x/domain/...`)를 직접 import하지 않는다. | 자동(`[공개API]`) | `fsd-structure` §3 |
| F3 | `app`과 `shared`에는 slice가 없다. 용도별 폴더(`app/router`, `app/styles`, `shared/api`, `shared/ui`, `shared/lib`, `shared/config`)로만 나눈다. | 자동(`[구조]`) + 정독 | `fsd-structure` §1 |

## 2. slice 안 4계층

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| F4 | slice 안은 `presentation / application / domain / infrastructure` 네 폴더로만 나눈다(쓰지 않는 계층은 만들지 않는다). FSD 세그먼트 이름(`ui`, `model`, `api`, `lib`)을 slice 안에 쓰지 않는다. | 자동(`[구조]`) | `layer-architecture` §1 |
| F5 | 의존 방향: presentation → application·domain, application → domain, infrastructure → domain·application(`import type`만). application과 presentation은 infrastructure를 import하지 않는다. domain은 slice 안 다른 계층을 import하지 않는다. | 자동(`[의존방향]`) | `layer-architecture` §2 |
| F6 | domain은 순수 TypeScript다. `react`, `react-dom`, `react-router`, `fetch`, `window`, `document`, `localStorage`, `import.meta.env`를 쓰지 않는다. | 자동(`[외부의존]`) | `layer-architecture` §3 |
| F7 | 검증·상태 판단·계산·표기 변환(금액, 남은 시간, 상태 문구)은 domain 함수에 둔다. 컴포넌트와 훅에 비즈니스 if-else를 두지 않는다. | 정독 | `layer-architecture` §3 |
| F18 | 계층은 추상(포트)으로만 연결한다. 도메인 데이터 접근은 domain 포트, 유스케이스 전용 기술 기능은 application 포트(`interface`)로 선언하고, 구현체는 infrastructure에 `implements`로 둔다. 토큰은 `application/tokens.ts`에 두고 훅은 `useDep(토큰)`으로 받는다. 구현체를 만드는 곳은 slice의 `wiring.ts`뿐이고, `wiring.ts`를 가져오는 곳은 `app/container.ts`뿐이다. `index.ts`는 구현체와 wiring을 내보내지 않는다. 유스케이스는 포트를 인자로 받고 구현체 기본값을 두지 않는다. | 자동(`[wiring위치]`, `[공개API]`, `[의존방향]`, `[구조]`) + 정독 | `layer-architecture` §6 |

## 3. 서버 통신과 상태

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| F8 | `fetch`는 `shared/api`의 클라이언트에서만 호출한다. slice의 infrastructure는 이 클라이언트를 쓴다. 다른 곳에서 `fetch`를 직접 호출하지 않는다. | 자동(`[fetch위치]`) | `api-client` §2 |
| F9 | API 응답 DTO는 infrastructure에서 domain 타입으로 바꾼다. presentation과 application은 DTO 타입을 쓰지 않는다. | 정독 | `api-client` §4 |
| F10 | 서버 데이터는 application 훅이 로딩·에러·빈 상태를 함께 돌려준다. 컴포넌트는 세 상태를 모두 그린다. effect의 요청은 `AbortController`로 정리하고, 정리된 뒤 상태를 바꾸지 않는다. | 정독 + 도구(Vitest) | `react-implementation` §3 |
| F11 | 에러는 `shared/api`의 `ApiError`(`status`, `errorCode`, `message`)로 다룬다. 화면 분기는 `errorCode`로 하고, 서버 `message`를 그대로 노출할지는 화면 명세를 따른다. | 정독 | `api-client` §3 |
| F17 | 액세스 토큰은 `localStorage`에 두고 `shared/api/tokenStorage.ts`에서만 읽고 쓴다. 토큰을 로그·URL·에러 보고·React 상태·다른 저장소에 두지 않는다. XSS 통로(`dangerouslySetInnerHTML`, `innerHTML`, `eval`, 사용자 입력으로 만든 `javascript:` 링크)를 만들지 않는다. | 정독 | `api-client` §2.1 |

## 4. 디자인·문구·명세

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| F12 | 색·간격·모서리·그림자는 `src/app/styles/tokens.css` 변수와 `bundle.css` 클래스만 쓴다. 새 색(hex·rgb)이나 새 컴포넌트 클래스를 만들지 않는다. 두 파일은 `../docs/design-system`의 복사본이며 직접 고치지 않는다. | 자동(`[하드코딩색]`) + 정독 | `design-system-usage` §2 |
| F13 | 화면 문구는 `screens.md`·`content.md`·`states.md`에 있는 그대로 쓴다. 상태 enum은 `states.md`의 한국어 문구로 바꿔 보여 준다. | 정독 | `design-system-usage` §4 |
| F14 | URI·요청/응답 필드·상태 코드·`error_code`는 `../docs/reference/<모듈>.md`를 따른다. 다르게 구현하면 이유를 보고한다. | 정독 + 실행 | `api-client` §5 |

## 5. 저장소 위생과 테스트

| ID | 규칙 | 검사 | 상세 |
| --- | --- | --- | --- |
| F15 | `.env*.local`·시크릿을 커밋하지 않는다. `VITE_` 값은 빌드 결과에 노출되므로 비밀 값을 넣지 않는다. 의존성은 `npm install`로만 추가하고 `package-lock.json`을 함께 커밋한다. | 정독 + 실행 | `pre-merge-check` §1 |
| F16 | 검사를 통과시키려고 규칙을 끄지 않는다. `any`, `@ts-ignore`, `eslint-disable`, `it.skip`, `it.only`, `test.fixme`를 새로 넣지 않는다. 지우거나 느슨하게 만든 단언은 이유를 보고한다. | 도구 + 정독 | `fe-code-review` §2 |

## 6. 코드 작업 공통 완료 게이트

코드를 바꾼 작업은 아래를 모두 통과해야 완료입니다. 명령의 정본은 이 절이며, 에이전트 명세와 `qa-verification`, `pre-merge-check`는 이 절을 가리킵니다. 모두 `frontend` 폴더에서 실행합니다.

명령은 한 줄에 하나씩 실행합니다. `&&`·`||`로 잇지 않습니다(Windows PowerShell 5.1은 지원하지 않음). 저장소의 스크립트는 모두 Node(`.mjs`)라서 Windows PowerShell·macOS·Linux에서 같은 명령으로 동작합니다. 셸 스크립트(`.sh`)는 만들지 않습니다.

```powershell
node .claude/skills/layer-check/check_layers.mjs   # 위반 0건 (F1~F6, F8, F12, F18)
npm run lint                                         # 0 error, 0 warning
npm run format:check                                 # Prettier 차이 0
npm run typecheck                                    # tsc 0 error
npm run test                                         # Vitest failed 0, skip 0
npm run build                                        # 성공
```
- 화면 흐름을 바꿨으면 `npm run test:e2e`(Playwright)도 실행합니다(`qa-verification` §4).
- 정독 규칙(F7, F9~F11, F13, F14, F17, F18의 정독 부분)은 수정자가 아닌 `fe-architect`(구조)·`fe-reviewer`(정확성)가 판정합니다.
- `package.json`에 위 스크립트 이름이 없으면 게이트를 통과로 치지 않고 "스크립트 없음"으로 보고합니다. 스크립트 정의는 `qa-verification` §1이 정본입니다.

## 7. 위반 보고 형식

| 심각도 | 파일:줄 | 규칙 | 내용 | 고치는 방법 |
| --- | --- | --- | --- | --- |
| 위반 / 주의 / 미구현 | `src/features/reserve-offer/application/useReserveOffer.ts:4` | F5, F18 | application에서 infrastructure의 `HttpReservationRepository`를 직접 import | `ReservationRepository` 포트를 `useDep(ReservationRepositoryToken)`으로 받고, 구현체 연결은 `wiring.ts`에 둠 |
