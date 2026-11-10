import type { ErrorInfo } from './errorInfo';

// 내부 파일(공개 API 아님): 4개 폼 훅의 공통 제출 상태 전이
export type SubmitState = { pending: boolean; error: ErrorInfo | null; done: boolean };

export function useSubmit<A extends unknown[], R>(
  run: (...args: A) => Promise<R>,
): { state: SubmitState; submit(...args: A): Promise<R | undefined>; reset(): void } {
  void run;
  throw new Error('not implemented: useSubmit');
}
