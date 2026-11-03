# 마감 직전(Last Call) 백엔드 작업 진입 맵

## 빠른 시작 순서

1. AGENTS.md
2. README.md
3. docs/operations/architecture.md
4. docs/operations/orchestration.md
5. docs/reference/README.md

## 문서 맵

### 운영 기준선

| 관심사 | 위치 |
|--------|------|
| 프로젝트 개요·스택·로컬 실행 | `README.md` |
| 4계층·DDD 아키텍처 원칙 | `docs/operations/architecture.md` |
| 오케스트레이션·에이전트 중계·쓰기 소유권 | `docs/operations/orchestration.md` |
| API 명세 (공통 에러 형식·권한·전체 목록) | `docs/reference/README.md` |
| 모듈별 API 명세 | `docs/reference/<모듈>.md` |

### 구현 규칙 (스킬)

| 관심사 | 위치 | 읽을 때 |
|--------|------|---------|
| DB 스키마·관계·SQLAlchemy 매핑 | `.claude/skills/db-schema/SKILL.md`, `schema.sql` | 테이블·컬럼·FK·조인·시드를 다룰 때 |
| 4계층 코드 패턴·예외→HTTP 표 | `.claude/skills/layer-implementation/SKILL.md` | 계층 코드를 쓰거나 고칠 때 |
| 테스트 작성법 | `.claude/skills/layer-implementation/testing.md` | 테스트를 쓸 때 |
| 계층 규칙 자동 검사 | `.claude/skills/layer-check/SKILL.md` | 코드 변경 후, 머지 전 |
| 서버 실행·동작 확인 | `.claude/skills/fastapi-run/SKILL.md` | 실제 동작을 볼 때 |
| 인증·보안 점검 | `.claude/skills/auth-security-check/SKILL.md` | auth·인증 의존성·미들웨어 변경 후 |
| 머지 전 점검 순서 | `.claude/skills/pre-merge-check/SKILL.md` | PR·머지 직전 |
| 정답 예시 코드 | `src/auth/**`, `src/error_handlers.py`, `tests/auth/**` | 패턴이 문서와 다르거나 불분명할 때 |

### 역할 (에이전트)

| 역할 | 위치 |
|------|------|
| 설계 (`docs/design/`만 씀) | `.claude/agents/layer-architect.md` |
| 구현 (맡은 모듈만 씀) | `.claude/agents/layer-implementer.md` |
| 계층 규칙 점검 (읽기 전용) | `.claude/agents/layer-checker.md` |
| 실행·보안·머지 전 검증 (읽기 전용) | `.claude/agents/verifier.md` |

### 실행 아티팩트

| 관심사 | 위치 |
|--------|------|
| 모듈 설계안 (결정 표 D-번호, 정합 이슈 C-번호) | `docs/design/<모듈>.md` |

## 작업 원칙

- `.claude/` 안의 에이전트와 스킬만 사용한다.
- 설계 → 구현 → 점검 → 검증 순서를 건너뛰지 않는다. 설계안 없이 구현을 맡기지 않는다.
- 문서와 `src/auth/**`가 다르면 auth 코드를 따르고 문서를 고친다.
- 의존 방향을 지킨다: presentation → application → domain, application → infrastructure → domain. domain은 순수 파이썬이다.
- 비즈니스 규칙은 도메인 메서드에 둔다. 서비스는 조회 → 도메인 메서드 → `save()` → `commit()`만 조율한다.
- 레포지토리는 도메인 객체만 주고받는다. `commit()`은 서비스가 한다.
- router·service에서 `HTTPException`을 만들지 않는다. 모듈 전용 도메인 예외를 내고 전역 핸들러가 변환한다.
- 모듈 사이 협력은 상대 모듈의 application 서비스로만 한다. 순환 의존은 포트로 끊고 조립은 presentation에서 한다.
- 확정되지 않은 규칙은 지어내지 않는다. 임시 기본값과 함께 설계안 결정 표에 올리고 사용자가 확정한다.
- 스키마를 바꾸면 `schema.sql`과 `db-schema/SKILL.md`를 함께 고친다.
- 에이전트 사이 전달은 요약이 아니라 "파일 경로 + ID"로 한다. 발주서 필수 항목은 `docs/operations/orchestration.md` §3.2를 따른다.
- 수정자와 점검자를 분리한다. 구현한 에이전트에게 자기 결과를 점검시키지 않는다.
- 검사를 통과시키려고 규칙·테스트를 끄거나 skip하지 않는다.
- `.env`·시크릿을 커밋하지 않는다. git 쓰기는 사용자 요청이 있을 때만 한다.

## 완료 조건

- `python3 .claude/skills/layer-check/check_layers.py` 위반 0건.
- `(cd src && uv run python -c "import main")` 성공.
- `uv run pytest -rs` failed 0건, DB 테스트(`db` 마커) skip 0건.
- `layer-checker` 지적 사항 해소.
- `verifier` 실행 검증 통과 (머지 전에는 `pre-merge-check` 보고 형식의 "머지 가능").
