import { HttpAccountGateway } from '@/features/auth/infrastructure/httpAccountGateway';
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
  email: 'customer@test.com',
  name: '김고객',
  phone: '010-2',
  role: 'CUSTOMER',
  users_point: 120,
  created_at: '2026-01-02T03:04:05Z',
  status: 'APPROVED',
};

type Options = { method?: string; body?: unknown; signal?: AbortSignal; auth?: boolean };

function lastPath(): unknown {
  return request.mock.calls.at(-1)?.[0];
}

function lastOptions(): Options {
  const call = request.mock.calls.at(-1);
  return (call?.[1] ?? {}) as Options;
}

describe('HttpAccountGateway', () => {
  const gateway = new HttpAccountGateway();

  beforeEach(() => {
    request.mockReset();
  });

  describe('signup', () => {
    it('/v1/auth/signup에 {email,password,name,phone,role}을 auth:false로 POST하고 undefined를 돌려준다', async () => {
      request.mockResolvedValue(meDto);
      const result = await gateway.signup({
        email: 'a@b.c',
        password: 'pw123456',
        name: '홍길동',
        phone: '010-1',
        role: 'CUSTOMER',
      });
      expect(result).toBeUndefined();
      expect(lastPath()).toBe('/v1/auth/signup');
      expect(lastOptions()).toMatchObject({ method: 'POST', auth: false });
      expect(lastOptions().body).toEqual({
        email: 'a@b.c',
        password: 'pw123456',
        name: '홍길동',
        phone: '010-1',
        role: 'CUSTOMER',
      });
    });

    it('409 ApiError를 그대로 던진다', async () => {
      const err = new ApiError(409, 'EMAIL_DUPLICATED', '이미 가입된 이메일입니다.');
      request.mockRejectedValue(err);
      await expect(
        gateway.signup({
          email: 'a@b.c',
          password: 'pw123456',
          name: '홍길동',
          phone: '010-1',
          role: 'CUSTOMER',
        }),
      ).rejects.toBe(err);
    });
  });

  describe('requestPasswordReset', () => {
    it('/v1/auth/password-reset/request에 {email}을 auth:false로 POST한다', async () => {
      request.mockResolvedValue(undefined);
      await gateway.requestPasswordReset('a@b.c');
      expect(lastPath()).toBe('/v1/auth/password-reset/request');
      expect(lastOptions()).toMatchObject({ method: 'POST', auth: false });
      expect(lastOptions().body).toEqual({ email: 'a@b.c' });
    });
  });

  describe('confirmPasswordReset', () => {
    it('/v1/auth/password-reset/confirm에 {email, code, new_password}를 auth:false로 POST한다', async () => {
      request.mockResolvedValue(undefined);
      await gateway.confirmPasswordReset({
        email: 'a@b.c',
        code: '123456',
        newPassword: 'pw123456',
      });
      expect(lastPath()).toBe('/v1/auth/password-reset/confirm');
      expect(lastOptions()).toMatchObject({ method: 'POST', auth: false });
      expect(lastOptions().body).toEqual({
        email: 'a@b.c',
        code: '123456',
        new_password: 'pw123456',
      });
    });
  });

  describe('updateProfile', () => {
    it('PATCH /v1/users/me 본문은 넣은 키만 담는다({phone}, name 키 없음)', async () => {
      request.mockResolvedValue(meDto);
      await gateway.updateProfile({ phone: '010-2' });
      expect(lastPath()).toBe('/v1/users/me');
      expect(lastOptions().method).toBe('PATCH');
      expect(lastOptions().body).toEqual({ phone: '010-2' });
      expect(Object.keys(lastOptions().body as object)).toEqual(['phone']);
    });

    it('name·phone 둘 다 보내면 둘 다 담는다', async () => {
      request.mockResolvedValue(meDto);
      await gateway.updateProfile({ name: '김고객', phone: '010-2' });
      expect(lastOptions().body).toEqual({ name: '김고객', phone: '010-2' });
    });

    it('응답 DTO를 User로 바꾼다(point는 users_point, createdAt은 Date)', async () => {
      request.mockResolvedValue(meDto);
      const user = await gateway.updateProfile({ phone: '010-2' });
      expect(user).toEqual({
        id: 'u1',
        email: 'customer@test.com',
        name: '김고객',
        phone: '010-2',
        role: 'CUSTOMER',
        status: 'APPROVED',
        point: 120,
        createdAt: new Date('2026-01-02T03:04:05Z'),
      });
      expect(user.createdAt).toBeInstanceOf(Date);
    });

    it('알 수 없는 role이면 reject한다', async () => {
      request.mockResolvedValue({ ...meDto, role: 'WEIRD' });
      // 변환 단계의 거절인지 확인한다(알 수 없는 값이 오류에 드러남).
      await expect(gateway.updateProfile({ phone: '010-2' })).rejects.toThrow(/WEIRD/);
    });
  });

  describe('changePassword', () => {
    it('/v1/users/me/password에 {current_password, new_password}를 POST하고 auth 옵션을 끄지 않는다', async () => {
      request.mockResolvedValue(undefined);
      await gateway.changePassword({ currentPassword: 'old12345', newPassword: 'new12345' });
      expect(lastPath()).toBe('/v1/users/me/password');
      expect(lastOptions().method).toBe('POST');
      expect(lastOptions().body).toEqual({
        current_password: 'old12345',
        new_password: 'new12345',
      });
      expect(lastOptions().auth).not.toBe(false);
    });
  });

  describe('signal 전달', () => {
    it('다섯 메서드 모두 signal을 넘긴다', async () => {
      const c = new AbortController();
      request.mockResolvedValue(undefined);
      await gateway.signup(
        { email: 'a@b.c', password: 'pw123456', name: 'n', phone: 'p', role: 'CUSTOMER' },
        c.signal,
      );
      expect(lastOptions().signal).toBe(c.signal);
      await gateway.requestPasswordReset('a@b.c', c.signal);
      expect(lastOptions().signal).toBe(c.signal);
      await gateway.confirmPasswordReset(
        { email: 'a@b.c', code: '123456', newPassword: 'pw123456' },
        c.signal,
      );
      expect(lastOptions().signal).toBe(c.signal);
      await gateway.changePassword({ currentPassword: 'a', newPassword: 'b' }, c.signal);
      expect(lastOptions().signal).toBe(c.signal);
      request.mockResolvedValue(meDto);
      await gateway.updateProfile({ phone: '010-2' }, c.signal);
      expect(lastOptions().signal).toBe(c.signal);
    });
  });
});
