# feat(frontend): 예약·결제·내 예약 화면과 예약 조회 API 구현

예약에 필요한 수량 선택 패널과 결제·결제 완료·내 예약 화면을 추가합니다. 로그인 후 결제 화면으로 복귀하고, 결제한 예약의 픽업 코드를 확인한 뒤 예약을 취소하고 지난 예약에서 확인할 수 있습니다.

## 변경 사항

- reservations·payments feature의 4계층, 포트·DI wiring, 관련 page와 고객 전용 인증 가드를 연결합니다.
- 고객 PC 화면의 외곽 폭을 테두리 포함 최대 420px로 제한하고 가운데 정렬합니다.
- 예약 목록에 픽업 시간·취소 마감을 제공하고, 본인 예약 단건 조회 `GET /v1/reservations/{reservation_id}`를 추가합니다.
- 예약·결제 설계, API 문서와 화면 ↔ slice 대응표를 갱신합니다.
- 취소 시트의 잘못된 환불 총액 표시를 제거하고, 고정 모달·초점 제한·배경 비활성화를 적용합니다.
- 취소 마감 400·상태 충돌 409 이후 오류 시트를 유지하면서 목록을 다시 조회합니다.

## 검증

| 항목 | 결과 |
| --- | --- |
| 프론트엔드 단위 테스트 | 57파일, 460 passed, failed/skipped/todo 0 |
| 백엔드 전체 pytest | 1847 passed, failed/skipped 0 |
| Playwright E2E | 46 passed, failed/flaky/skipped 0 |
| lint / format:check / typecheck / build | 모두 통과 |
| 프론트엔드·백엔드 계층 검사 | 위반 0 |
| 작업 주석 형식·디자인 CSS 동기화 | 통과 |
| Vite dev·preview SPA fallback / dev API proxy | 통과 |
| HTTP smoke | 51 PASS / 0 FAIL |
| 독립 정확성 재리뷰·구조 정독 | APPROVE / PASS |

E2E 46개는 실서버 예약·결제 4개, 기존 모킹 36개, 새 모달·화면 폭 회귀 6개입니다. 회귀 테스트는 수정 전 실패와 수정 후 통과를 확인했습니다. 모바일 360px·PC 1280px에서 시트 위치·포커스·배경 결제 차단과 PC 외곽 420px를 확인했습니다.

기존 DB에는 접속하지 않았습니다. 별도 tmpfs PostgreSQL 컨테이너의 55437 포트에서 pytest·E2E 전용 DB를 나눠 사용했습니다. 검증용 웹 서버는 종료했습니다.

## 검증 범위와 기존 제한

- 검증 대상은 `fd8a643` 기반의 이번 feature 변경입니다. 현재 main(`3ddea13`)의 추가 15커밋을 통합하지 않았으며, main 통합 결과는 검증하지 않았습니다.
- C2 전체 page 연결, 고객 정식 셸·TabBar, 길찾기, 결제 후 포인트 즉시 갱신 등 기존 미결정 기능은 범위에 포함하지 않습니다.
- 기존 상점주 승인 가드·보호 API 401 세션 정리 FIXME 2개는 유지합니다.
- 예약 목록의 할인별 추가 조회 성능 개선은 후속 과제로 남깁니다.
- DB 스키마·의존성·프로젝트 설정·디자인 CSS 복사본 변경은 없습니다.

자세한 변경·실행 명령·로그 위치·남은 결정은 [Claude 인수인계](https://github.com/shyuk07/TEAM-F/blob/feat/reservations-frontend/docs/handoffs/2026-11-10-reservations-frontend.md)에 정리했습니다.
