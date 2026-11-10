import { HttpAuthGateway } from '@/features/auth/infrastructure/httpAuthGateway';
import { ApiError } from '@/shared/api/error';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

// apiGet·apiPost는 실제 client처럼 request를 거치게 해서, 구현이 무엇을 쓰든 request 호출로 확인한다.
vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

const meDto = {
  id: 'u1',
  email: 'owner@test.com',
  name: '망원베이커리',
  phone: '010-1111-2222',
  role: 'OWNER',
  users_point: 120,
  created_at: '2026-01-02T03:04:05Z',
  status: 'APPROVED',
};

function lastOptions(): { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean } {
  const call = request.mock.calls.at(-1);
  return (call?.[1] ?? {}) as ReturnType<typeof lastOptions>;
}

describe('HttpAuthGateway', () => {
  const gateway = new HttpAuthGateway();

  beforeEach(() => {
    request.mockReset();
  });

  describe('login', () => {
    it('/v1/auth/login에 {email,password}를 POST하고 auth:false로 호출한다', async () => {
      request.mockResolvedValue({ access_token: 't', token_type: 'bearer', status: 'APPROVED' });
      await gateway.login('a@b.c', 'pw');
      expect(request.mock.calls.at(-1)?.[0]).toBe('/v1/auth/login');
      expect(lastOptions()).toMatchObject({
        method: 'POST',
        body: { email: 'a@b.c', password: 'pw' },
        auth: false,
      });
    });

    it('응답을 {accessToken,status}로 바꾸고 token_type은 버린다', async () => {
      request.mockResolvedValue({ access_token: 't', token_type: 'bearer', status: 'APPROVED' });
      const result = await gateway.login('a@b.c', 'pw');
      expect(result).toEqual({ accessToken: 't', status: 'APPROVED' });
      expect(result).not.toHaveProperty('token_type');
    });

    it('알 수 없는 status면 reject한다', async () => {
      request.mockResolvedValue({ access_token: 't', token_type: 'bearer', status: 'WEIRD' });
      await expect(gateway.login('a@b.c', 'pw')).rejects.toThrow();
    });
  });

  describe('logout', () => {
    it('/v1/auth/logout을 본문 없이 POST하고 undefined를 돌려준다', async () => {
      request.mockResolvedValue(undefined);
      await expect(gateway.logout()).resolves.toBeUndefined();
      expect(request.mock.calls.at(-1)?.[0]).toBe('/v1/auth/logout');
      expect(lastOptions().method).toBe('POST');
      expect(lastOptions().body).toBeUndefined();
    });
  });

  describe('findMe', () => {
    it('GET /v1/users/me 응답을 User로 바꾼다(createdAt은 Date, point는 users_point)', async () => {
      request.mockResolvedValue(meDto);
      const user = await gateway.findMe();
      expect(request.mock.calls.at(-1)?.[0]).toBe('/v1/users/me');
      expect(lastOptions().method ?? 'GET').toBe('GET');
      expect(user).toEqual({
        id: 'u1',
        email: 'owner@test.com',
        name: '망원베이커리',
        phone: '010-1111-2222',
        role: 'OWNER',
        status: 'APPROVED',
        point: 120,
        createdAt: new Date('2026-01-02T03:04:05Z'),
      });
      expect(user.createdAt).toBeInstanceOf(Date);
    });

    it('name·phone이 null이면 null을 유지한다', async () => {
      request.mockResolvedValue({ ...meDto, name: null, phone: null });
      const user = await gateway.findMe();
      expect(user.name).toBeNull();
      expect(user.phone).toBeNull();
    });

    it('알 수 없는 role이면 reject한다', async () => {
      request.mockResolvedValue({ ...meDto, role: 'WEIRD' });
      await expect(gateway.findMe()).rejects.toThrow();
    });
  });

  describe('signal 전달', () => {
    it('login은 signal을 넘긴다', async () => {
      request.mockResolvedValue({ access_token: 't', token_type: 'bearer', status: 'APPROVED' });
      const c = new AbortController();
      await gateway.login('a@b.c', 'pw', c.signal);
      expect(lastOptions().signal).toBe(c.signal);
    });

    it('logout은 signal을 넘긴다', async () => {
      request.mockResolvedValue(undefined);
      const c = new AbortController();
      await gateway.logout(c.signal);
      expect(lastOptions().signal).toBe(c.signal);
    });

    it('findMe는 signal을 넘긴다', async () => {
      request.mockResolvedValue(meDto);
      const c = new AbortController();
      await gateway.findMe(c.signal);
      expect(lastOptions().signal).toBe(c.signal);
    });
  });

  describe('오류 전파', () => {
    it('login의 401 ApiError를 그대로 던진다', async () => {
      const err = new ApiError(401, 'INVALID_CREDENTIALS', 'x');
      request.mockRejectedValue(err);
      await expect(gateway.login('a@b.c', 'pw')).rejects.toBe(err);
    });

    it('findMe의 401 ApiError를 그대로 던진다', async () => {
      const err = new ApiError(401, 'TOKEN_REVOKED', 'x');
      request.mockRejectedValue(err);
      await expect(gateway.findMe()).rejects.toBe(err);
    });
  });
});
