// 401·TOKEN_REVOKED 감지를 세션 정리로 잇는 공용 채널 (docs/design/frontend/stores.md §2.2)
type AuthFailureHandler = () => void;

let handler: AuthFailureHandler | null = null;

// 등록은 해제 함수를 돌려주는 onAuthFailure 하나로 통일한다(D-9).
export function onAuthFailure(newHandler: AuthFailureHandler): () => void {
  handler = newHandler;
  return () => {
    if (handler === newHandler) handler = null;
  };
}

export function setAuthFailureHandler(newHandler: AuthFailureHandler | null): void {
  handler = newHandler;
}

export function notifyAuthFailure(): void {
  handler?.();
}
