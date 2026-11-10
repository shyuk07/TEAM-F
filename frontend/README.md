# 마감 직전 (Last Call) — Frontend

마감 시간이 가까워진 매장의 할인 음식을 고객이 예약하고,
결제 후 직접 픽업하는 서비스의 프론트엔드 프로젝트입니다.

## 기술 스택

- Node.js 24 LTS
- npm
- React
- TypeScript
- Vite (개발 서버·빌드)
- React Router

최종 결과물은 정적 파일(`dist/`)로 빌드해 배포합니다.

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
