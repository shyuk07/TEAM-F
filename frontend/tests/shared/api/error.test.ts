import { describe, expect, it } from 'vitest';
import { ApiError, toApiError } from '@/shared/api/error';

describe('ApiError', () => {
  it('status, errorCode, message를 담는 Error이다', () => {
    const e = new ApiError(409, 'EMAIL_DUPLICATED', '중복');
    expect(e).toBeInstanceOf(Error);
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(409);
    expect(e.errorCode).toBe('EMAIL_DUPLICATED');
    expect(e.message).toBe('중복');
  });
});

describe('toApiError', () => {
  it('공통 에러 형식을 ApiError로 바꾼다', async () => {
    const res = new Response(
      JSON.stringify({ success: false, error_code: 'INVALID_CREDENTIALS', message: '틀림' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } },
    );
    const e = await toApiError(res);
    expect(e).toBeInstanceOf(ApiError);
    expect(e.status).toBe(401);
    expect(e.errorCode).toBe('INVALID_CREDENTIALS');
    expect(e.message).toBe('틀림');
  });

  it('message가 없으면 빈 문자열이다', async () => {
    const res = new Response(JSON.stringify({ error_code: 'NOT_FOUND' }), { status: 404 });
    const e = await toApiError(res);
    expect(e.errorCode).toBe('NOT_FOUND');
    expect(e.message).toBe('');
  });

  it('JSON이 아닌 응답은 UNKNOWN과 statusText로 만든다', async () => {
    const res = new Response('<html>bad gateway</html>', {
      status: 502,
      statusText: 'Bad Gateway',
    });
    const e = await toApiError(res);
    expect(e.status).toBe(502);
    expect(e.errorCode).toBe('UNKNOWN');
    expect(e.message).toBe('Bad Gateway');
  });

  it('error_code가 문자열이 아닌 JSON은 UNKNOWN이다', async () => {
    const res = new Response(JSON.stringify({ detail: 'x' }), {
      status: 422,
      statusText: 'Unprocessable',
    });
    const e = await toApiError(res);
    expect(e.errorCode).toBe('UNKNOWN');
    expect(e.status).toBe(422);
  });
});
