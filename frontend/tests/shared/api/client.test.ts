import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const jsonRes = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function loadClient(baseUrl?: string) {
  vi.resetModules();
  if (baseUrl !== undefined) vi.stubEnv('VITE_API_BASE_URL', baseUrl);
  const client = await import('@/shared/api/client');
  const error = await import('@/shared/api/error');
  const tokens = await import('@/shared/api/tokenStorage');
  return { ...client, ...error, ...tokens };
}

describe('shared/api/client', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    localStorage.clear();
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('VITE_API_BASE_URL이 비면 /v1/... 상대 경로로 호출한다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('');
    await request('/v1/offers');
    expect(fetchMock.mock.calls[0][0]).toBe('/v1/offers');
  });

  it('VITE_API_BASE_URL이 있으면 앞에 붙여 호출한다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('https://api.example.com');
    await request('/v1/offers');
    expect(fetchMock.mock.calls[0][0]).toBe('https://api.example.com/v1/offers');
  });

  it('기본 메서드는 GET이고 Accept: application/json을 보낸다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('');
    await request('/v1/offers');
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe('GET');
    expect(init.headers.Accept).toBe('application/json');
    expect(init.body).toBeUndefined();
    expect(init.headers['Content-Type']).toBeUndefined();
  });

  it('토큰이 있으면 Authorization: Bearer 헤더를 붙인다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request, saveToken } = await loadClient('');
    saveToken('tok-1');
    await request('/v1/users/me');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer tok-1');
  });

  it('토큰이 없으면 Authorization 헤더가 없다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('');
    await request('/v1/users/me');
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it('auth: false이면 토큰이 있어도 헤더를 붙이지 않는다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request, saveToken } = await loadClient('');
    saveToken('tok-1');
    await request('/v1/auth/login', { method: 'POST', body: {}, auth: false });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });

  it('body가 있으면 JSON 문자열과 Content-Type: application/json을 보낸다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('');
    await request('/v1/reservations', { method: 'POST', body: { offer_id: 'o1', quantity: 2 } });
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe('POST');
    expect(init.headers['Content-Type']).toBe('application/json');
    expect(init.body).toBe(JSON.stringify({ offer_id: 'o1', quantity: 2 }));
  });

  it('AbortSignal을 fetch에 그대로 전달한다', async () => {
    fetchMock.mockResolvedValue(jsonRes({}));
    const { request } = await loadClient('');
    const ctrl = new AbortController();
    await request('/v1/offers', { signal: ctrl.signal });
    expect(fetchMock.mock.calls[0][1].signal).toBe(ctrl.signal);
  });

  it('2xx 응답은 JSON으로 파싱해 돌려준다', async () => {
    fetchMock.mockResolvedValue(jsonRes({ id: 'o1' }));
    const { request } = await loadClient('');
    await expect(request<{ id: string }>('/v1/offers/o1')).resolves.toEqual({ id: 'o1' });
  });

  it('204 응답은 undefined를 돌려준다', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    const { request } = await loadClient('');
    await expect(request('/v1/auth/logout', { method: 'POST' })).resolves.toBeUndefined();
  });

  it('공통 에러 응답은 ApiError(status, errorCode, message)로 던진다', async () => {
    fetchMock.mockResolvedValue(
      jsonRes({ success: false, error_code: 'RESERVATION_CLOSED', message: '마감' }, 409),
    );
    const { request, ApiError } = await loadClient('');
    const err = await request('/v1/reservations', { method: 'POST', body: {} }).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(409);
    expect(err.errorCode).toBe('RESERVATION_CLOSED');
    expect(err.message).toBe('마감');
  });

  it('401도 클라이언트는 ApiError로 던지기만 한다(토큰 삭제는 인증 Context 몫)', async () => {
    fetchMock.mockResolvedValue(
      jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401),
    );
    const { request, saveToken, readToken } = await loadClient('');
    saveToken('tok-1');
    const err = await request('/v1/users/me').catch((e) => e);
    expect(err.status).toBe(401);
    expect(err.errorCode).toBe('UNAUTHORIZED');
    expect(readToken()).toBe('tok-1');
  });

  it('JSON이 아닌 에러 응답은 errorCode UNKNOWN이다', async () => {
    fetchMock.mockResolvedValue(
      new Response('oops', { status: 500, statusText: 'Internal Server Error' }),
    );
    const { request } = await loadClient('');
    const err = await request('/v1/offers').catch((e) => e);
    expect(err.status).toBe(500);
    expect(err.errorCode).toBe('UNKNOWN');
  });

  it('fetch가 실패하면 ApiError(0, NETWORK_ERROR)로 바꾼다', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    const { request, ApiError } = await loadClient('');
    const err = await request('/v1/offers').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(0);
    expect(err.errorCode).toBe('NETWORK_ERROR');
  });

  it('abort된 요청의 실패는 NETWORK_ERROR로 바꾸지 않고 원래 예외를 던진다', async () => {
    const ctrl = new AbortController();
    const abortErr = new DOMException('aborted', 'AbortError');
    fetchMock.mockImplementation(() => {
      ctrl.abort();
      return Promise.reject(abortErr);
    });
    const { request } = await loadClient('');
    await expect(request('/v1/offers', { signal: ctrl.signal })).rejects.toBe(abortErr);
  });

  it('apiGet은 GET으로 signal을 전달한다', async () => {
    fetchMock.mockResolvedValue(jsonRes({ ok: 1 }));
    const { apiGet } = await loadClient('');
    const ctrl = new AbortController();
    await expect(apiGet('/v1/offers', ctrl.signal)).resolves.toEqual({ ok: 1 });
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe('GET');
    expect(init.signal).toBe(ctrl.signal);
  });

  it('apiPost는 POST로 JSON body와 signal을 전달한다', async () => {
    fetchMock.mockResolvedValue(jsonRes({ ok: 1 }, 201));
    const { apiPost } = await loadClient('');
    const ctrl = new AbortController();
    await apiPost('/v1/payments', { a: 1 }, ctrl.signal);
    const init = fetchMock.mock.calls[0][1];
    expect(init.method).toBe('POST');
    expect(init.body).toBe('{"a":1}');
    expect(init.signal).toBe(ctrl.signal);
  });

  describe('multipart 본문 (FormData, products.md §2.1)', () => {
    const form = () => {
      const f = new FormData();
      f.append('name', '식빵');
      f.append('original_price', '12000');
      return f;
    };

    it('body가 FormData이면 fetch에 그 FormData가 그대로 전달된다', async () => {
      fetchMock.mockResolvedValue(jsonRes({ id: 'p1' }, 201));
      const { request } = await loadClient('');
      const body = form();
      await request('/v1/stores/st-1/products', { method: 'POST', body });
      const init = fetchMock.mock.calls[0][1];
      expect(init.method).toBe('POST');
      expect(init.body).toBe(body);
    });

    it('FormData 요청에는 Content-Type 헤더가 없고 Authorization은 있다', async () => {
      fetchMock.mockResolvedValue(jsonRes({ id: 'p1' }, 201));
      const { request, saveToken } = await loadClient('');
      saveToken('tok-1');
      await request('/v1/stores/st-1/products', { method: 'POST', body: form() });
      const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
      expect(Object.keys(headers).map((k) => k.toLowerCase())).not.toContain('content-type');
      expect(headers.Authorization).toBe('Bearer tok-1');
    });

    it('FormData 요청의 401 + UNAUTHORIZED도 인증 실패 핸들러를 1번 부른다', async () => {
      fetchMock.mockResolvedValue(
        jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401),
      );
      const mod = await loadClient('');
      const { onAuthFailure } = await import('@/shared/api/authFailure');
      const handler = vi.fn();
      onAuthFailure(handler);
      await expect(
        mod.request('/v1/stores/st-1/products', { method: 'POST', body: form() }),
      ).rejects.toMatchObject({ status: 401 });
      expect(handler).toHaveBeenCalledTimes(1);
    });
  });

  describe('401 · TOKEN_REVOKED 알림 (authFailure)', () => {
    async function setup(res: Response) {
      fetchMock.mockResolvedValue(res);
      const mod = await loadClient('');
      const { onAuthFailure } = await import('@/shared/api/authFailure');
      const handler = vi.fn();
      const off = onAuthFailure(handler);
      await mod.saveToken('tok-1');
      const err = await mod.request('/v1/stores/me').catch((e) => e);
      return { ...mod, handler, off, err };
    }

    it('401 + UNAUTHORIZED: 핸들러가 정확히 1번 불리고 ApiError가 그대로 던져진다', async () => {
      const { handler, err, ApiError } = await setup(
        jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401),
      );
      expect(handler).toHaveBeenCalledTimes(1);
      expect(err).toBeInstanceOf(ApiError);
      expect(err.status).toBe(401);
    });

    it('401 + TOKEN_REVOKED: 핸들러가 1번 불린다', async () => {
      const { handler } = await setup(
        jsonRes({ success: false, error_code: 'TOKEN_REVOKED', message: 'x' }, 401),
      );
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('401 + 다른 errorCode(INVALID_CREDENTIALS)는 불리지 않는다', async () => {
      const { handler } = await setup(
        jsonRes({ success: false, error_code: 'INVALID_CREDENTIALS', message: 'x' }, 401),
      );
      expect(handler).not.toHaveBeenCalled();
    });

    it('auth: false 요청의 401은 불리지 않는다(로그인 실패)', async () => {
      const mod = await loadClient('');
      const { onAuthFailure } = await import('@/shared/api/authFailure');
      const handler = vi.fn();
      onAuthFailure(handler);
      fetchMock.mockResolvedValue(
        jsonRes({ success: false, error_code: 'INVALID_CREDENTIALS', message: 'x' }, 401),
      );
      await expect(
        mod.request('/v1/auth/login', { method: 'POST', body: {}, auth: false }),
      ).rejects.toMatchObject({ status: 401 });
      expect(handler).not.toHaveBeenCalled();
    });

    it.each([
      [403, 'FORBIDDEN'],
      [404, 'NOT_FOUND'],
      [400, 'VALIDATION_ERROR'],
      [500, 'INTERNAL_ERROR'],
    ])('%i + %s는 불리지 않는다', async (status, errorCode) => {
      const { handler } = await setup(
        jsonRes({ success: false, error_code: errorCode, message: 'x' }, status as number),
      );
      expect(handler).not.toHaveBeenCalled();
    });

    it('NETWORK_ERROR는 불리지 않는다', async () => {
      fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
      const mod = await loadClient('');
      const { onAuthFailure } = await import('@/shared/api/authFailure');
      const handler = vi.fn();
      onAuthFailure(handler);
      await expect(mod.request('/v1/stores/me')).rejects.toMatchObject({ status: 0 });
      expect(handler).not.toHaveBeenCalled();
    });

    it('등록 해제 함수를 부른 뒤에는 불리지 않는다', async () => {
      const { off, handler } = await setup(
        jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401),
      );
      expect(handler).toHaveBeenCalledTimes(1);
      off();
      await setup(jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401));
      expect(handler).toHaveBeenCalledTimes(1);
    });

    it('핸들러가 없어도 오류 없이 ApiError를 던진다', async () => {
      const mod = await loadClient('');
      fetchMock.mockResolvedValue(
        jsonRes({ success: false, error_code: 'UNAUTHORIZED', message: 'x' }, 401),
      );
      await expect(mod.request('/v1/stores/me')).rejects.toMatchObject({ status: 401 });
    });
  });
});
