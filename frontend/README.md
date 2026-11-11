# 마감 직전 (Last Call) — Frontend

마감 시간이 가까워진 매장의 할인 음식을 고객이 예약하고,
결제 후 직접 픽업하는 서비스의 프론트엔드 프로젝트입니다.

## 기술 스택

- **Runtime & Tooling**: Node.js 24 LTS, npm, Vite 6
- **Framework & Core**: React 19, TypeScript 5
- **Routing**: React Router 8
- **Testing**: Vitest, Playwright (E2E), React Testing Library
- **Code Quality**: ESLint 10, Prettier

최종 결과물은 정적 파일(`dist/`)로 빌드해 배포합니다.

## 프로젝트 구조 (Feature-Sliced Design)

유지보수성과 확장성을 위해 **FSD(Feature-Sliced Design)** 아키텍처 패턴을 따릅니다. 상위 계층은 하위 계층만 참조할 수 있습니다.

```
frontend/src/
├── app/          # 애플리케이션 초기화, 전역 라우터, 인증/테마 프로바이더, 글로벌 스타일
├── pages/        # 라우트 단위 페이지 컴포넌트 (총 28개 화면)
├── widgets/      # 페이지를 구성하는 복합 독립 UI 블록 (Header, BottomNav, StoreBanner 등)
├── features/     # 사용자의 인터랙션과 동작 단위 (로그인 폼, 결제 처리, 마감할인 등록 등)
├── entities/     # 핵심 비즈니스 엔티티 모델, 슬라이스 상태, 도메인 API (User, Store, Offer 등)
└── shared/       # 범용 재사용 컴포넌트(Button, Input, Modal), 공통 API 클라이언트, 디자인 토큰
```

### 구현된 주요 화면 및 기능

| 구분 | 주요 화면 | 기능 설명 |
|:---|:---|:---|
| **공통/인증** | `/login`, `/signup`<br>`/password-reset` | 이메일/비밀번호 회원가입, JWT 로그인, 비밀번호 재설정 요청 및 변경 |
| **고객 (Customer)** | `/` (Home)<br>`/offers/:id`<br>`/checkout`<br>`/payments/complete`<br>`/my/reservations`<br>`/my`, `/point-history` | - 내 주변 마감할인 실시간 탐색 및 지도 보기<br>- 마감 할인 상세 정보(정가/할인가, 잔여 재고, 픽업 시간)<br>- 수량 선택, 포인트 복합 모의 결제<br>- 4자리 픽업 번호 확인 및 예약 취소 요청<br>- 내 정보 수정, 포인트 적립/사용 내역 확인 |
| **상점주 (Owner)** | `/owner/start`<br>`/owner/store`<br>`/owner/products/new`, `edit`<br>`/owner/offers/new`, `edit`<br>`/owner/today` | - 신규 상점 입점 신청 및 사업자 정보 등록<br>- 매장 기본 정보 및 운영 시간 관리<br>- 기본 메뉴(상품) 등록 및 수정<br>- 오늘의 마감 할인(수량, 할인율, 픽업 기한) 등록/수정/중단<br>- 실시간 당일 예약 접수 확인 및 픽업 번호 대조 완료 처리 |
| **관리자 (Admin)** | `/admin/approvals`<br>`/admin/users`<br>`/admin/moderation` | - 점주 신규 입점 신청 목록 심사 (승인 / 반려)<br>- 회원 목록 조회, 경고/정지 및 강제 탈퇴 제재<br>- 신고된 부적합 상점·상품 강제 판매 중단 및 폐점 |

## 로컬 개발 환경 실행

### 1. 사전 준비

다음 프로그램이 필요합니다.

- Node.js 24 LTS (npm 포함)
- Git

버전 확인:

```powershell
node -v
npm -v
```

### 2. 라이브러리 설치

`frontend` 폴더에서 실행합니다.

```powershell
npm install
```

### 3. 백엔드 실행

API를 호출하려면 백엔드 서버가 먼저 실행 중이어야 합니다. 실행 방법은 `../backend/README.md`를 봅니다. 백엔드는 `http://localhost:8001`에서 실행됩니다.

### 4. 개발 서버 실행

```powershell
npm run dev
```

브라우저에서 터미널에 표시된 주소(기본 `http://localhost:5173`)로 접속합니다.

## NPM 스크립트 가이드

| 명령어 | 설명 |
|:---|:---|
| `npm run dev` | Vite 로컬 개발 서버 실행 (기본 포트 5173, `/v1` 백엔드 프록시 연동) |
| `npm run build` | TypeScript 타입 검사 후 프로덕션 정적 번들 빌드 (`dist/` 생성) |
| `npm run preview` | 프로덕션 빌드 결과물(`dist/`) 로컬 미리보기 서버 구동 |
| `npm run typecheck` | TypeScript 타입 에러 검사 (출력 없이 종료코드 판정) |
| `npm run lint` | ESLint 기반 코드 스타일 및 잠재적 버그 정적 분석 |
| `npm run format` | Prettier를 사용한 전체 프론트엔드 코드 포맷팅 자동 수정 |
| `npm run format:check` | Prettier 포맷팅 준수 여부 검사 |
| `npm run test` | Vitest 기반 컴포넌트 및 단위 테스트 실행 |
| `npm run test:e2e` | Playwright 기반 E2E 시나리오 테스트 실행 |

## 백엔드 API 연결

### 개발: Vite proxy

개발 서버는 `/v1`로 시작하는 요청을 백엔드로 그대로 전달합니다. 경로는 바꾸지 않습니다.

| 프론트에서 호출 | 실제 전달 대상 |
|---|---|
| `/v1/...` | `http://localhost:8001/v1/...` |

`vite.config.ts` 설정:

```ts
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/v1': 'http://localhost:8001',
    },
  },
})
```

개발 중에는 `VITE_API_BASE_URL`을 비워 둡니다. 이 값이 비어 있으면 요청이 같은 주소의 `/v1/...`로 나가고 proxy가 백엔드로 전달합니다.

### 배포: `VITE_API_BASE_URL`

배포용 빌드에서는 API 서버 주소를 `VITE_API_BASE_URL`로 지정합니다. 이 값은 빌드할 때 코드에 들어가므로 **빌드 전에** 설정해야 합니다.

```powershell
$env:VITE_API_BASE_URL = "https://api.example.com"
npm run build
```

코드에서는 다음처럼 읽습니다.

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''
fetch(`${API_BASE_URL}/v1/...`)
```

> 프론트와 API가 다른 도메인에 있으면 백엔드에 CORS 설정이 필요합니다. 현재 백엔드에는 CORS 설정이 없습니다.

`VITE_`로 시작하는 값은 빌드 결과물에 그대로 노출됩니다. 비밀 값을 넣지 않습니다.

## 빌드와 배포

### 빌드

```powershell
npm run build
```

결과물은 `dist/` 폴더에 생성됩니다.

### 빌드 결과 미리보기

```powershell
npm run preview
```

### 배포 (Vercel + Render)

현재 배포는 프론트를 Vercel, 백엔드·DB를 Render에 둡니다.

- Vercel 프로젝트: 저장소 `shyuk07/TEAM-F`, Root Directory `frontend`. 빌드 설정은 `frontend/vercel.json`에 있습니다.
- `vercel.json`의 `rewrites`가 `/v1/...` 요청을 Render 백엔드(`https://lastcall-api-ggzn.onrender.com`)로 넘깁니다. 브라우저에는 같은 주소로 보이므로 CORS 설정이 필요 없고, `VITE_API_BASE_URL`은 **비워 둡니다**.
- 나머지 경로는 `index.html`로 돌려줘 새로고침해도 404가 나지 않습니다(SPA fallback).
- 카카오맵은 Vercel 환경변수 `VITE_KAKAO_MAP_JS_KEY`가 필요하고, 카카오 개발자 콘솔의 JavaScript SDK 도메인에 배포 주소를 등록해야 합니다.
- Render 무료 서버는 한동안 요청이 없으면 잠들어, 첫 요청이 30~60초 걸릴 수 있습니다.

### 배포 (Nginx)

`dist/` 폴더의 정적 파일을 Nginx로 서비스합니다.

React Router의 `BrowserRouter`를 쓰므로, 없는 경로(예: `/stores/1`)로 들어온 요청에도 `index.html`을 돌려줘야 합니다(SPA fallback). 이 설정이 없으면 새로고침하거나 주소를 직접 입력했을 때 404가 납니다.

Nginx `server` 블록 설정:

```nginx
server {
    listen 80;
    server_name example.com;

    # dist/ 내용을 올린 경로
    root /usr/share/nginx/html;
    index index.html;

    location / {
        # 파일 → 디렉터리 → 없으면 index.html (SPA fallback)
        try_files $uri $uri/ /index.html;
    }
}
```

- `server_name`과 `root`는 실제 배포 환경에 맞게 바꿉니다.
- `/assets/...`처럼 실제로 있는 파일은 그대로 응답하고, 없는 경로만 `index.html`로 넘깁니다.
- 설정을 바꾼 뒤에는 문법 검사 후 다시 읽어 들입니다.

```bash
nginx -t
nginx -s reload
```

## 디자인 시스템

화면 구현에 쓰는 토큰, 컴포넌트, 화면 명세는 `../docs/design-system/`에 있습니다. 읽는 순서는 `../docs/design-system/README.md`를 봅니다.

## npm 스크립트

| 명령 | 설명 |
|---|---|
| `npm run dev` | 개발 서버 실행 |
| `npm run build` | 타입 검사 후 정적 파일 빌드 (`dist/`) |
| `npm run preview` | 빌드 결과를 로컬에서 미리보기 |
