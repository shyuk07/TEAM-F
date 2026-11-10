import { logout } from '@/features/auth/application/logout';
import { ApiError } from '@/shared/api/error';
import { FakeAuthGateway } from '../fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';

function setup() {
  const auth = new FakeAuthGateway();
  const session = new FakeSessionStore(true);
  return { auth, session, deps: { auth, session } };
}

describe('logout', () => {
  it('서버 호출이 끝난 뒤에 세션을 지운다', async () => {
    const { auth, session, deps } = setup();
    await logout(deps);
    expect(auth.logout.mock.invocationCallOrder[0]).toBeLessThan(
      session.clear.mock.invocationCallOrder[0],
    );
  });

  it('서버가 401 TOKEN_REVOKED로 거절해도 세션을 지우고 resolve한다', async () => {
    const { auth, session, deps } = setup();
    auth.logout.mockRejectedValue(new ApiError(401, 'TOKEN_REVOKED', 'x'));
    await expect(logout(deps)).resolves.toBeUndefined();
    expect(session.clear).toHaveBeenCalled();
  });

  it('NETWORK_ERROR여도 세션을 지우고 resolve한다', async () => {
    const { auth, session, deps } = setup();
    auth.logout.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', 'n'));
    await expect(logout(deps)).resolves.toBeUndefined();
    expect(session.clear).toHaveBeenCalled();
  });

  it('서버 호출과 세션 삭제를 각각 한 번씩만 한다', async () => {
    const { auth, session, deps } = setup();
    await logout(deps);
    expect(auth.logout).toHaveBeenCalledTimes(1);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });
});
