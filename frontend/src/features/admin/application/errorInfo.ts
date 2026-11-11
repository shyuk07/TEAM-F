import type { ErrorInfo } from '../domain/actionError';

// shared/api의 ApiError를 application에서 직접 import할 수 없어(F5) 필요한 필드만 구조로 읽는다.
export function readErrorInfo(e: unknown): ErrorInfo {
  if (typeof e === 'object' && e !== null) {
    const o = e as { status?: unknown; errorCode?: unknown; message?: unknown };
    if (typeof o.status === 'number' && typeof o.errorCode === 'string') {
      return {
        status: o.status,
        errorCode: o.errorCode,
        message: typeof o.message === 'string' ? o.message : '',
      };
    }
  }
  return { status: 0, errorCode: 'UNKNOWN', message: '' };
}
