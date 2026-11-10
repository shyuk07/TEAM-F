// shared/api의 ApiError를 application에서 직접 import할 수 없어(F5) 필요한 필드만 구조로 읽는다.
export type ErrorInfo = { status: number; errorCode: string; message: string };

export function readErrorInfo(e: unknown): ErrorInfo {
  if (e !== null && typeof e === 'object') {
    const o = e as Record<string, unknown>;
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
