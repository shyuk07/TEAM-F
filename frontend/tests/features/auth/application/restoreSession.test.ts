import { restoreSession } from '@/features/auth/application/restoreSession';
import { ApiError } from '@/shared/api/error';
import { FakeAuthGateway } from '../fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';
import { ownerUser } from '../fakes/users';

function setup(hasSession = true) {
  const auth = new FakeAuthGateway();
  const session = new FakeSessionStore(hasSession);
  return { auth, session, deps: { auth, session }, signal: new AbortController().signal };
}

describe('restoreSession', () => {
  it('세션이 없으면 anonymous(other)이고 findMe를 부르지 않는다', async () => {
    const { auth, deps, signal } = setup(false);
    await expect(restoreSession(deps, signal)).resolves.toEqual({
      status: 'anonymous',
      cause: 'other',
    });
    expect(auth.findMe).not.toHaveBeenCalled();
  });

  it('findMe가 성공하면 authenticated다', async () => {
    const { auth, deps, signal } = setup();
    auth.findMe.mockResolvedValue(ownerUser);
    await expect(restoreSession(deps, signal)).resolves.toEqual({
      status: 'authenticated',
      user: ownerUser,
    });
  });

  it.each([
    ['401 UNAUTHORIZED', new ApiError(401, 'UNAUTHORIZED', 'x')],
    ['401 TOKEN_REVOKED', new ApiError(401, 'TOKEN_REVOKED', 'x')],
    ['403', new ApiError(403, 'FORBIDDEN', 'x')],
  ])('%s이면 세션을 지우고 anonymous(other)다', async (_name, err) => {
    const { auth, session, deps, signal } = setup();
    auth.findMe.mockRejectedValue(err);
    await expect(restoreSession(deps, signal)).resolves.toEqual({
      status: 'anonymous',
      cause: 'other',
    });
    expect(session.clear).toHaveBeenCalled();
  });

  it.each([
    ['NETWORK_ERROR', new ApiError(0, 'NETWORK_ERROR', '네트워크')],
    ['500', new ApiError(500, 'INTERNAL', '서버')],
  ])('%s이면 error 상태이고 세션을 지우지 않는다', async (_name, err) => {
    const { auth, session, deps, signal } = setup();
    auth.findMe.mockRejectedValue(err);
    await expect(restoreSession(deps, signal)).resolves.toEqual({
      status: 'error',
      errorCode: err.errorCode,
      message: err.message,
    });
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('이미 abort된 signal이면 null이다', async () => {
    const { deps } = setup();
    const c = new AbortController();
    c.abort();
    await expect(restoreSession(deps, c.signal)).resolves.toBeNull();
  });
});
