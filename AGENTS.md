# 마감 직전(Last Call) 백엔드 작업 진입 맵

## 빠른 시작 순서

1. AGENTS.md
2. README.md
3. .claude/skills/layer-architecture/SKILL.md
4. docs/operations/orchestration.md
5. docs/reference/README.md

## 문서 맵

### 운영 기준선

| 관심사 | 위치 |
|--------|------|
| 프로젝트 개요·스택·로컬 실행 | `README.md` |
| 오케스트레이션·에이전트 중계·쓰기 소유권 | `docs/operations/orchestration.md` |
| API 명세 (공통 에러 형식·권한·전체 목록) | `docs/reference/README.md` |
| 모듈별 API 명세 | `docs/reference/<모듈>.md` |

### 구현 규칙 (스킬)

| 관심사 | 위치 | 읽을 때 |
|--------|------|---------|
| 백엔드 불변 규칙(R1~R16)·코드 완료 게이트 | `.claude/skills/backend-invariants/SKILL.md` | 코드를 설계·구현·점검·검증할 때, 발주서에 규칙을 넘길 때 |
| 4계층 책임·DDD 원칙·DI(container) 구조 | `.claude/skills/layer-architecture/SKILL.md` | 모듈 설계, 추상화·주입, 모듈 간 의존 판단, container.py 수정 시 |
| DB 스키마·관계·SQLAlchemy 매핑 | `.claude/skills/db-schema/SKILL.md`, `schema.sql` | 테이블·컬럼·FK·조인·시드를 다룰 때 |
| 4계층 코드 패턴·예외→HTTP 표 | `.claude/skills/layer-implementation/SKILL.md` | 계층 코드를 쓰거나 고칠 때 |
| 테스트 작성법 | `.claude/skills/layer-implementation/testing.md` | 테스트를 쓸 때 |
| 계층 규칙 자동 검사 | `.claude/skills/layer-check/SKILL.md` | 코드 변경 후, 머지 전 |
| 서버 실행·동작 확인 | `.claude/skills/fastapi-run/SKILL.md` | 실제 동작을 볼 때 |
| 인증·보안 점검 | `.claude/skills/auth-security-check/SKILL.md` | auth·인증 의존성·미들웨어 변경 후 |
| 머지 전 점검 순서 | `.claude/skills/pre-merge-check/SKILL.md` | PR·머지 직전 |
| 정답 예시 코드 | `src/auth/**`, `src/error_handlers.py`, `tests/auth/**` | 패턴이 문서와 다르거나 불분명할 때 (DI·조립은 제외) |

### 역할 (에이전트)

| 역할 | 위치 |
|------|------|
| 설계 (`docs/design/`만 씀) | `.claude/agents/layer-architect.md` |
| 구현 (맡은 모듈만 씀) | `.claude/agents/layer-implementer.md` |
| 계층 규칙 점검 (읽기 전용) | `.claude/agents/layer-checker.md` |
| 변경 코드 정확성 리뷰 (읽기 전용) | `.claude/agents/layer-reviewer.md` |
| 실행·보안·머지 전 검증 (읽기 전용) | `.claude/agents/verifier.md` |

### 실행 아티팩트

| 관심사 | 위치 |
|--------|------|
| 모듈 설계안 (결정 표 D-번호, 정합 이슈 C-번호) | `docs/design/<모듈>.md` |

## 작업 원칙

어떤 작업(설계·구현·점검·검증·문서·질의 응답)이든 아래 원칙을 지킨다. 작업별 세부 규칙은 문서 맵의 정본 문서에 있다.

- **정본을 먼저 찾는다.** 작업에 해당하는 정본을 문서 맵에서 찾아 읽은 뒤 시작한다. 기억이나 추측으로 규칙을 대신하지 않는다.
- **정본은 하나다.** 같은 내용을 두 곳에 쓰지 않는다. 다른 문서는 정본의 위치만 가리킨다. 정본이 서로 다르면 임의로 고르지 않고 보고한다.
- **이 저장소의 도구만 쓴다.** 에이전트와 스킬은 `.claude/` 안의 것만 사용한다.
- **단계를 건너뛰지 않는다.** 범위 확정 → 설계 → 실행 → 점검 → 검증 순서를 지킨다. 앞 단계의 산출물 없이 다음 단계로 가지 않는다.
- **확정되지 않은 것은 지어내지 않는다.** 모르는 것은 "확인 필요"로 남기고, 임시값을 쓸 때는 임시값임을 표시해 사용자 결정을 받는다.
- **범위를 지킨다.** 맡은 범위 밖은 고치지 않고 제안으로 보고한다. 범위를 넓혔다면 넓힌 부분을 표시한다.
- **근거로 말한다.** 주장과 완료 보고에는 실행한 명령과 결과, 또는 `파일:위치`를 붙인다. 실행하지 않은 것을 통과로 말하지 않는다.
- **만든 사람과 확인하는 사람을 나눈다.** 자기 산출물을 스스로 합격 판정하지 않는다.
- **검사를 약하게 만들지 않는다.** 통과를 위해 규칙·테스트·검사를 끄거나 건너뛰지 않는다. 실패는 실패로 보고한다.
- **전달은 손실 없이 한다.** 에이전트 사이 정보는 요약하지 않고 파일 경로와 ID로 넘긴다(`docs/operations/orchestration.md`).
- **되돌리기 어려운 일은 사용자가 정한다.** git 쓰기, 외부 게시, 삭제, 설정 변경은 사용자 요청이 있을 때만 한다. 시크릿은 커밋하지 않는다.
- **운영 문서에는 운영만 쓴다.** `AGENTS.md`와 `docs/operations/`에는 현재 진행 상황이나 특정 기능 이야기를 넣지 않는다.

## 완료 조건

- 작업 유형의 정본(해당 스킬·에이전트 명세)이 정한 완료 조건을 모두 충족한다.
- 산출물이 맡은 쓰기 범위 안에만 있다(`git status`로 확인).
- 완료 보고에 실행한 검사와 결과, 남은 확인 필요 항목이 들어 있다.
- 사용자가 결정해야 할 항목이 결정되었거나, 미결정으로 명시되어 있다.
