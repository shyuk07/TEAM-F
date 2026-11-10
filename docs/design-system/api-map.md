# API 매핑

화면별로 부르는 엔드포인트입니다. 쿼리·응답 형식과 상태 코드는 각 화면 메모(`screens.md`)를 함께 보세요.

| 화면 | 제목 | 엔드포인트 |
|---|---|---|
| A1 | 로그인 | `POST /v1/auth/login {email, password}` |
| A2 | 회원가입 | `POST /v1/auth/signup {email, password, name, phone, role}` |
| A3 | 비밀번호 재설정 | `POST /v1/auth/password-reset/request · /confirm` |
| C8 | 프로필 변경 | `PATCH /v1/users/me {name?, phone?}` |
| C9 | 비밀번호 변경 | `POST /v1/users/me/password {current_password, new_password}` |
| C10 | 로그아웃 확인 | `POST /v1/auth/logout` |
| O8 | 계정 메뉴 | `헤더 "계정" 버튼 (상점주·관리자 공용)` |
| C1 | 홈 · 주변 할인 (비로그인 가능) | `GET /v1/offers` |
| C1a | 위치 · 반경 | `GET /v1/offers?lat&lng&radius_km` |
| C2 | 할인 상세 | `GET /v1/offers/{id}` |
| C3 | 결제 | `POST /v1/payments {reservation_id, use_point}` |
| C3a | 결제 화면 나가기 | `POST /v1/reservations/{id}/cancel` |
| C4 | 결제 완료 | `결제 응답 → 예약 확정` |
| C5 | 내 예약 | `GET /v1/users/me/reservations` |
| C5a | 예약 취소 확인 | `POST /v1/reservations/{id}/cancel` |
| C5b | 내 예약 · 지난 예약 | `GET /v1/users/me/reservations` |
| C6 | 마이 | `GET /v1/users/me · /points` |
| C7 | 회원 탈퇴 확인 | `POST /v1/users/me/withdraw {password}` |
| C11 | 포인트 내역 전체 | `GET /v1/users/me/points?page=0` |
| E1 | 로딩 · 빈 상태 · 취소 마감 | `상태 모음` |
| O0 | 첫 화면 · 상점 개설 | `users.status → POST /v1/stores {pickup_address}` |
| O1 | 오늘 · 픽업 처리 | `POST /v1/reservations/{id}/pickup {pickup_code}` |
| O2 | 할인 관리 · 재고 조정 | `offers · stock-adjustments` |
| O3 | 할인 등록 · 다시 올리기 | `POST /v1/products/{id}/offers · /relist` |
| O4 | 매장 · 상품 | `GET/POST /v1/stores/{id}/products` |
| O5 | 판매 중단 확인 | `POST /v1/offers/{id}/deactivate {reason, cancel_reservations}` |
| O6 | 상품 등록 | `POST /v1/stores/{id}/products` |
| O7 | 상점 폐점 확인 | `POST /v1/stores/{id}/close` |
| O9 | 할인 수정 | `PATCH /v1/offers/{id}` |
| O10 | 재고 조정 (모바일) | `POST /v1/offers/{id}/stock-adjustments {amount, reason?}` |
| O11 | 상품 수정 · 숨기기 | `PATCH /v1/products/{id} · /deactivate · /activate` |
| O12 | 상품 사진 올리기 (1장) | `POST /v1/products/{id}/images → products.product_image` |
| M1 | 승인 · 회원 · 상점 관리 | `/v1/admin/*` |
| M2 | 제재 확인 (예: 회원 정지) | `PATCH /v1/admin/users/{id}/suspend {reason, suspended_until?}` |
| M3 | 회원 탭 · 회원 상세 | `GET /v1/admin/users · /users/{id} · /users/{id}/points` |
| M4 | 포인트 지급 | `POST /v1/admin/users/{id}/points {amount, reason}` |
| M5 | 상점 탭 · 할인 탭 | `PATCH /v1/admin/stores/{id}/suspend·close · /offers/{id}/suspend` |
