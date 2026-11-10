import { updateProfile } from '@/features/auth/application/updateProfile';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';
import { customerUser } from '../fakes/users';

function setup() {
  const account = new FakeAccountGateway(customerUser);
  const session = new FakeSessionStore(true);
  return { account, session, deps: { account, session } };
}

describe('updateProfile', () => {
  it('patch를 그대로 보내고 응답 User를 돌려준다', async () => {
    const { account, deps } = setup();
    const user = await updateProfile(deps, { phone: '010-2' });
    expect(account.updateProfile.mock.calls[0]?.[0]).toEqual({ phone: '010-2' });
    expect(user).toEqual({ ...customerUser, phone: '010-2' });
  });

  it('넘긴 signal을 account.updateProfile에 그대로 전달한다', async () => {
    const { account, deps } = setup();
    const signal = new AbortController().signal;
    await updateProfile(deps, { phone: '010-2' }, signal);
    expect(account.updateProfile.mock.calls[0]?.[1]).toBe(signal);
  });

  it('401 TOKEN_REVOKED면 session.clear() 후 같은 오류로 reject한다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.');
    account.updateProfile.mockRejectedValue(err);
    await expect(updateProfile(deps, { phone: '010-2' })).rejects.toBe(err);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });

  it('403이면 reject하고 clear를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(403, 'FORBIDDEN', '정지된 계정입니다.');
    account.updateProfile.mockRejectedValue(err);
    await expect(updateProfile(deps, { phone: '010-2' })).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('400이면 reject하고 clear를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(400, 'VALIDATION_ERROR', '서버 규칙 문구');
    account.updateProfile.mockRejectedValue(err);
    await expect(updateProfile(deps, { phone: '010-2' })).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });
});
