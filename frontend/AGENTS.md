# 마감 직전(Last Call) 프론트엔드 작업 진입 맵

이 문서는 메인 세션이 읽는 진입점입니다. 메인 세션은 **오케스트레이터**로서 작업을 나눠 `.claude/agents/`의 에이전트에게 맡기고, 결과를 확인해 사용자에게 보고합니다. 운영 규칙의 정본은 `../docs/operations/frontend-orchestration.md`입니다.

## 빠른 시작 순서

1. AGENTS.md
2. README.md
3. ../docs/operations/frontend-orchestration.md
4. .claude/skills/frontend-invariants/SKILL.md
5. .claude/skills/fsd-structure/SKILL.md
6. ../docs/design-system/README.md

## 오케스트레이터 역할

| 한다 | 하지 않는다 |
|------|-------------|
| 범위 확정(화면 ID·slice), 작업 분할, 발주서 작성 | 설계 결정을 혼자 확정하기 (결정은 사용자) |
| 에이전트 선택과 순서 결정 | 제품 코드·설계안을 직접 고치기 (소유 에이전트에게 재발주) |
| 결과 검증(`git status`, 검사 명령 재실행) | 서브에이전트 보고를 검증 없이 사실로 전달하기 |
| 정합 이슈·결정 항목 정리, 사용자 보고 | git 쓰기(commit/push/merge)를 요청 없이 실행하기 |
| 공용 파일 조정 (쓰기 소유권 표) | `.claude/` 밖 에이전트(전역·플러그인)로 대신하기 |

에이전트 선택, 발주서 필수 항목, 중계 방법, 쓰기 소유권, 표준 흐름은 `../docs/operations/frontend-orchestration.md`를 따릅니다.

## 문서 맵

경로는 모두 `frontend` 폴더 기준입니다.

### 운영 기준선

| 관심사 | 위치 |
|--------|------|
| 프로젝트 개요·스택·로컬 실행·API 연결·배포(Nginx) | `README.md` |
| 오케스트레이션·에이전트 선택·발주서·쓰기 소유권 | `../docs/operations/frontend-orchestration.md` |
| 백엔드 진입 맵 (백엔드 작업은 여기서 하지 않음) | `../backend/AGENTS.md` |

### 화면·디자인 정본 (읽기 전용)

| 관심사 | 위치 |
|--------|------|
| 디자인 원칙·색·글자·간격·컴포넌트 목록 (먼저 읽기) | `../docs/design-system/README.md` |
| 디자인 시스템 사용 안내 | `../docs/design-system/HOW-TO-USE.md` |
| 역할별 셸·720px 반응형·화면 골격·화면 연결 지도 | `../docs/design-system/layout.md` |
| 37개 화면 명세 (화면 ID, API, 컴포넌트, 문구, 동작) | `../docs/design-system/screens.md`, `screens.json` |
| 화면별 엔드포인트 | `../docs/design-system/api-map.md` |
| 상태 enum ↔ 한국어 문구, 화면 계산값 | `../docs/design-system/states.md` |
| 말투·버튼·오류 문구·숫자·시간 표기 | `../docs/design-system/content.md` |
| 미정 항목과 임시 동작 | `../docs/design-system/open-issues.md` |
| 컴포넌트별 규칙·마크업 예시 | `../docs/design-system/components/<이름>/README.md`, `preview.html` |
| 토큰·컴포넌트 CSS 원본 | `../docs/design-system/tokens.json`, `tokens.css`, `components/bundle.css` |
| 원본 와이어프레임 | `../docs/design-system/wireframe.html` |

### API·도메인 정본 (읽기 전용)

| 관심사 | 위치 |
|--------|------|
| 공통 에러 형식·인증 헤더·전체 API 목록 | `../docs/reference/README.md` |
| 모듈별 API 명세 (auth, stores, catalog, reservations, payments, admin) | `../docs/reference/<모듈>.md` |
| 모듈별 도메인 요구 조건 | `../docs/requirements/<모듈>.md` |
| 백엔드 모듈 설계안 | `../docs/design/<모듈>.md` |
| 실제 라우트·응답 스키마 (명세 확인용) | `../backend/src/<모듈>/presentation/router.py`, `schemas.py` |

### 구현 규칙 (스킬)

| 관심사 | 위치 | 읽을 때 |
|--------|------|---------|
| 불변 규칙(F1~F18)·코드 완료 게이트 | `.claude/skills/frontend-invariants/SKILL.md` | 코드를 설계·구현·점검·검증할 때, 발주서에 규칙을 넘길 때 |
| FSD 계층·업무 영역 7개(features)·영역 ↔ 백엔드·명세·화면 대응·공개 API·화면 ↔ slice 대응표 | `.claude/skills/fsd-structure/SKILL.md` | 새 화면·기능의 영역과 위치를 정할 때, slice를 만들거나 옮길 때 |
| slice 안 4계층 책임·의존 방향·설계안 항목 | `.claude/skills/layer-architecture/SKILL.md` §1~§5 | slice 안에 코드를 나눌 때, 설계안을 쓸 때 |
| 추상화(포트)·구현체·의존성 주입(토큰·wiring·container) | `.claude/skills/layer-architecture/SKILL.md` §6 | 포트·구현체·wiring을 만들 때, 가짜 구현체로 테스트할 때 |
| FSD·4계층·주입 규칙 자동 검사 | `.claude/skills/layer-check/SKILL.md`, `check_layers.mjs` | 코드 변경 후, 머지 전 |
| React 코드 패턴(공용 훅·상태 분기·라우팅·폼·테스트) | `.claude/skills/react-implementation/SKILL.md` | React 코드를 쓰거나 고칠 때 |
| API 클라이언트·에러·DTO 변환·명세 대조 | `.claude/skills/api-client/SKILL.md` | API 호출 코드를 쓸 때, 명세를 확인할 때 |
| 디자인 시스템 사용·CSS 복사본 동기화·문구 | `.claude/skills/design-system-usage/SKILL.md`, `scripts/sync_styles.mjs` | 화면·UI를 구현할 때, 디자인 문서가 바뀌었을 때 |
| Vite 서버 실행·SPA fallback·proxy 확인 | `.claude/skills/vite-run/SKILL.md`, `scripts/run_vite.mjs` | 실제 화면을 볼 때, E2E 전 |
| 검증 스크립트·판정 기준·E2E·Red 테스트 | `.claude/skills/qa-verification/SKILL.md` | 검증할 때, 테스트를 먼저 쓸 때 |
| 정확성 리뷰 관점·판정 | `.claude/skills/fe-code-review/SKILL.md` | 변경 코드를 리뷰할 때 |
| 머지 전 점검 순서 | `.claude/skills/pre-merge-check/SKILL.md` | PR·머지 직전 |

### 역할 (에이전트)

| 역할 | 위치 |
|------|------|
| 설계·구조 점검 (`../docs/design/frontend/`와 대응표만 씀) | `.claude/agents/fe-architect.md` |
| 구현 (맡은 slice만 씀) | `.claude/agents/fe-developer.md` |
| 변경 코드 정확성 리뷰 (읽기 전용, 실행 안 함) | `.claude/agents/fe-reviewer.md` |
| 실행 검증·E2E·머지 전 점검 (요청 시 테스트 파일만 씀) | `.claude/agents/fe-qa.md` |

### 실행 아티팩트

| 관심사 | 위치 |
|--------|------|
| slice 설계안 (결정 표 D-번호, 정합 이슈 C-번호, 질문 목록) | `../docs/design/frontend/<slice>.md` |
| 화면 ↔ slice 대응표 | `.claude/skills/fsd-structure/SKILL.md` §7 |
| 의존성 조립 (영역별 wiring을 모으는 유일한 곳) | `src/app/container.ts` |
| 영역별 구현체 ↔ 토큰 연결 (소유한 entities 포트 포함) | `src/features/<영역>/wiring.ts` |
| DI 도구 (토큰·Container·`useDep`) | `src/shared/lib/di.tsx` |
| 디자인 시스템 CSS 복사본 (직접 수정 금지) | `src/app/styles/tokens.css`, `src/app/styles/bundle.css` |
| E2E 테스트 | `e2e/<흐름>.spec.ts` |

## 작업 원칙

어떤 작업(설계·구현·점검·검증·문서·질의 응답)이든 아래 원칙을 지킨다. 작업별 세부 규칙은 문서 맵의 정본 문서에 있다.

- **정본을 먼저 찾는다.** 작업에 해당하는 정본을 문서 맵에서 찾아 읽은 뒤 시작한다. 기억이나 추측으로 규칙을 대신하지 않는다.
- **정본은 하나다.** 같은 내용을 두 곳에 쓰지 않는다. 다른 문서는 정본의 위치만 가리킨다. 정본이 서로 다르면(예: 명세와 백엔드 코드, 화면 명세와 API 명세) 임의로 고르지 않고 양쪽 위치를 적어 보고한다.
- **이 저장소의 도구만 쓴다.** 에이전트와 스킬은 `frontend/.claude/` 안의 것만 사용한다. 맞는 에이전트가 없으면 사용자에게 묻는다.
- **단계를 건너뛰지 않는다.** 범위 확정 → 설계 → 구현 → 점검 → 검증 순서를 지킨다. 설계안 없이 구현을 맡기지 않는다.
- **확정되지 않은 것은 지어내지 않는다.** 모르는 것은 "확인 필요"로 남기고, 임시값을 쓸 때는 임시값임을 표시해 사용자 결정을 받는다. `open-issues.md` 항목은 거기 적힌 임시 동작만 쓴다.
- **범위를 지킨다.** 맡은 범위 밖은 고치지 않고 제안으로 보고한다. 디자인 시스템·API 명세·백엔드 코드는 프론트 작업에서 고치지 않는다.
- **근거로 말한다.** 주장과 완료 보고에는 실행한 명령과 결과, 또는 `파일:위치`를 붙인다. 실행하지 않은 것을 통과로 말하지 않는다.
- **만든 사람과 확인하는 사람을 나눈다.** 자기 산출물을 스스로 합격 판정하지 않는다.
- **검사를 약하게 만들지 않는다.** 통과를 위해 규칙·테스트·검사를 끄거나 건너뛰지 않는다. 실패는 실패로 보고한다.
- **전달은 손실 없이 한다.** 에이전트 사이 정보는 요약하지 않고 파일 경로와 ID로 넘긴다.
- **어느 OS에서나 돌아가게 한다.** 스크립트는 Node(`.mjs`)로 만들고 셸 스크립트를 만들지 않는다. 문서의 명령은 한 줄에 하나씩 쓰고 `&&`·`||`로 잇지 않는다(Windows PowerShell 5.1).
- **되돌리기 어려운 일은 사용자가 정한다.** git 쓰기, 의존성 추가, 외부 게시, 삭제, 설정 변경은 사용자 요청이 있을 때만 한다. 시크릿은 커밋하지 않는다.
- **운영 문서에는 운영만 쓴다.** `AGENTS.md`와 `../docs/operations/`에는 현재 진행 상황이나 특정 기능 이야기를 넣지 않는다.

## 완료 조건

- 작업 유형의 정본(해당 스킬·에이전트 명세)이 정한 완료 조건을 모두 충족한다. 코드를 바꿨으면 `frontend-invariants` §6 완료 게이트를 통과한다.
- 산출물이 맡은 쓰기 범위 안에만 있다(`git status`로 확인).
- 완료 보고에 실행한 검사와 결과, 남은 확인 필요 항목이 들어 있다.
- 사용자가 결정해야 할 항목이 결정되었거나, 미결정으로 명시되어 있다.
