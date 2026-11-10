import { API_BASE_URL } from '@/shared/config/env';
import { ApiError, toApiError } from './error';
import { readToken } from './tokenStorage';

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean };

// open-issues: NETWORK_ERROR 문구는 임시 문구, content.md 확정 시 교체
export async function request<T = never>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
  const token = opts.auth === false ? null : readToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: opts.signal,
    });
  } catch (e) {
    if (opts.signal?.aborted) throw e;
    throw new ApiError(
      0,
      'NETWORK_ERROR',
      '네트워크에 연결할 수 없어요. 잠시 후 다시 시도해 주세요.',
    );
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  // TODO: 2xx인데 본문이 JSON이 아니면 SyntaxError가 그대로 올라감 → ApiError(res.status, 'UNKNOWN')로 감쌀지 결정 필요 (fe-reviewer 지적)
  return (await res.json()) as T;
}

export const apiGet = <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal });
export const apiPost = <T>(path: string, body?: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body, signal });
