---
name: pre-merge-check
description: 마감 직전 프로젝트에서 브랜치나 PR을 main에 머지하기 전에 실행하는 개발 검증 순서입니다. 계층 규칙, import, 테스트, 실제 실행, 코드 리뷰를 차례로 확인하고 머지 가능 여부를 판단합니다. "머지 전 점검", "PR 검증"을 요청받았을 때 사용합니다.
---

# 머지 전 점검

아래 순서대로 실행하고, 앞 단계가 실패하면 원인을 먼저 보고합니다. 검사를 통과시키려고 규칙이나 테스트를 끄지 않습니다.

## 1. 변경 범위 파악
```bash
git fetch origin main && git diff --stat origin/main...HEAD
```
변경된 모듈과 계층을 정리합니다. `.env`, `.venv`, `__pycache__`가 변경 목록에 있으면 바로 위반입니다.

## 2. 계층 규칙
```bash
python3 .claude/skills/layer-check/check_layers.py
```
위반이 0건이어야 합니다. 변경한 모듈은 `layer-checker` 에이전트로 빈약한 도메인 모델, 레포지토리 변환, 서비스·라우터 책임도 확인합니다.

## 3. 의존성과 import
```bash
uv sync
```
```bash
cd src && uv run python -c "import main"
```
`main.py`를 import하면 등록된 모든 라우터와 모델이 함께 불러와집니다. 실제 DB 연결 없이도 `DATABASE_URL`만 있으면 됩니다.

## 4. 테스트
```bash
uv run pytest -q
```
도메인 규칙을 바꿨는데 테스트가 없으면 "테스트 없음"으로 표시하고, 필요한 테스트 목록을 제안합니다.

## 5. 실제 동작
`fastapi-run` 스킬의 확인 시나리오 중 변경과 관련된 항목을 실행합니다. auth를 바꿨다면 `auth-security-check` 스킬도 실행합니다.

## 6. 코드 리뷰
내장 `code-review` 스킬로 버그를, 필요하면 `simplify` 스킬로 중복과 복잡도를 확인합니다.

## 보고 형식
| 단계 | 결과 | 비고 |
| --- | --- | --- |
| 변경 범위 | | |
| 계층 규칙 | | |
| import | | |
| 테스트 | | |
| 실제 동작 | | |
| 코드 리뷰 | | |

마지막 줄에 **머지 가능 / 수정 후 머지 / 머지 불가** 중 하나와 그 이유를 적습니다.
