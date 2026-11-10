import { login } from '@/features/auth/application/login';
import { ApiError } from '@/shared/api/error';
import { FakeAuthGateway } from '../fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';
import { ownerUser } from '../fakes/users';

const input = { email: 'a@b.c', password: 'pw' };

function setup() {
  const auth = new FakeAuthGateway();
  const session = new FakeSessionStore(false);
  return { auth, session, deps: { auth, session } };
}

describe('login', () => {
  it('login → save → findMe 순서로 부르고 User를 돌려준다', async () => {
    const { auth, session, deps } = setup();
    auth.login.mockResolvedValue({ accessToken: 't1', status: 'APPROVED' });
    auth.findMe.mockResolvedValue(ownerUser);

    const user = await login(deps, input);

    expect(auth.login).toHaveBeenCalledWith('a@b.c', 'pw');
    expect(session.save).toHaveBeenCalledWith('t1');
    const order = [
      auth.login.mock.invocationCallOrder[0],
      session.save.mock.invocationCallOrder[0],
      auth.findMe.mock.invocationCallOrder[0],
    ];
    expect(order).toEqual([...order].sort((x, y) => x - y));
    expect(user).toBe(ownerUser);
  });

  it('auth.login이 401로 실패하면 저장하지 않고 같은 오류로 reject한다', async () => {
    const { auth, session, deps } = setup();
    const err = new ApiError(401, 'INVALID_CREDENTIALS', 'x');
    auth.login.mockRejectedValue(err);

    await expect(login(deps, input)).rejects.toBe(err);
    expect(session.save).not.toHaveBeenCalled();
  });

  it.each([
    ['403 FORBIDDEN', new ApiError(403, 'FORBIDDEN', '정지')],
    ['401 UNAUTHORIZED', new ApiError(401, 'UNAUTHORIZED', 'x')],
    ['NETWORK_ERROR', new ApiError(0, 'NETWORK_ERROR', 'n')],
  ])('findMe가 %s로 실패하면 세션을 지우고 같은 오류로 reject한다', async (_name, err) => {
    const { auth, session, deps } = setup();
    auth.findMe.mockRejectedValue(err);

    await expect(login(deps, input)).rejects.toBe(err);
    expect(session.clear).toHaveBeenCalled();
  });
});
