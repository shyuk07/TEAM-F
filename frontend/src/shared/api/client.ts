import { API_BASE_URL } from '@/shared/config/env';
import { ApiError, toApiError } from './error';
import { notifyAuthFailure } from './authFailure';
import { readToken } from './tokenStorage';

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean };

export async function request<T = never>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  // multipart 본문(FormData)은 그대로 보내고 Content-Type을 지정하지 않는다. 브라우저가 경계 문자열을 붙인다.
  const isForm = opts.body instanceof FormData;
  if (opts.body !== undefined && !isForm) headers['Content-Type'] = 'application/json';
  const token = opts.auth === false ? null : readToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: opts.method ?? 'GET',
      headers,
      body:
        opts.body === undefined
          ? undefined
          : isForm
            ? (opts.body as FormData)
            : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  } catch (e) {
    if (opts.signal?.aborted) throw e;
    // TODO: NETWORK_ERROR 문구는 임시 문구(해요체, 사용자 결정)다. content.md의 네트워크 오류 문구로 교체한다.
    //   왜: content.md에 네트워크 오류 문구가 없다 (api-client SKILL §2)
    //   언제: 결정 후 (디자인 시스템: content.md 네트워크 오류 문구 확정)
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      '네트워크에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.',
    );
  }
  if (!res.ok) {
    const err = await toApiError(res);
    if (
      opts.auth !== false &&
      err.status === 401 &&
      (err.errorCode === 'UNAUTHORIZED' || err.errorCode === 'TOKEN_REVOKED')
    ) {
      // 세션 만료·토큰 무효만 알린다. 403·400·404·5xx·NETWORK_ERROR는 세션 만료가 아니다(§2.2).
      notifyAuthFailure();
    }
    throw err;
  }
  if (res.status === 204) return undefined as T;
  // TODO: 2xx인데 본문이 JSON이 아니면 SyntaxError가 그대로 올라감 → ApiError(res.status, 'UNKNOWN')로 감쌀지 결정 필요
  //   왜: 배포 환경에서 proxy가 빠져 index.html(200)을 받으면 화면이 ApiError로 분기하지 못한다 (fe-reviewer 지적)
  //   언제: 결정 후 (사용자: 비JSON 2xx를 ApiError로 감쌀지)
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal });
export const apiPost = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body, signal });
