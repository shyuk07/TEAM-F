const KEY = 'lastcall.accessToken';

// 사생활 보호 모드·저장소 차단 환경에서는 localStorage 접근이 예외를 던진다. 그때는 로그인 상태를 유지하지 않는다.
export function readToken(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

export function saveToken(token: string): void {
  try {
    localStorage.setItem(KEY, token);
  } catch {
    // 저장 불가: 이번 탭에서만 로그인
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    // 무시
  }
}

// 다른 탭에서 로그인·로그아웃하면 이 탭도 따라가게 한다.
export function onTokenChange(cb: (token: string | null) => void): () => void {
  const handler = (e: StorageEvent) => {
    if (e.key === KEY || e.key === null) cb(readToken());
  };
  window.addEventListener('storage', handler);
  return () => window.removeEventListener('storage', handler);
}
