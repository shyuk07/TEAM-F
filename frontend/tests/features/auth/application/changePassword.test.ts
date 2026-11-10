import { changePassword } from '@/features/auth/application/changePassword';
import type { PasswordChangeForm } from '@/features/auth/domain/passwordChange';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';

const form: PasswordChangeForm = { current: 'old12345', next: 'new12345', confirm: 'new12345' };

function setup() {
  const account = new FakeAccountGateway();
  const session = new FakeSessionStore(true);
  return { account, session, deps: { account, session } };
}

describe('changePassword', () => {
  it('{currentPassword, newPassword}로 호출하고 성공해도 session.clear()를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    await changePassword(deps, form);
    expect(account.changePassword.mock.calls[0]?.[0]).toEqual({
      currentPassword: 'old12345',
      newPassword: 'new12345',
    });
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('401이면 session.clear() 후 같은 오류로 reject한다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.');
    account.changePassword.mockRejectedValue(err);
    await expect(changePassword(deps, form)).rejects.toBe(err);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });

  it('CURRENT_PASSWORD_MISMATCH면 reject하고 clear를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(
      400,
      'CURRENT_PASSWORD_MISMATCH',
      '현재 비밀번호가 올바르지 않습니다.',
    );
    account.changePassword.mockRejectedValue(err);
    await expect(changePassword(deps, form)).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('403이면 reject하고 clear를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(403, 'FORBIDDEN', '정지된 계정입니다.');
    account.changePassword.mockRejectedValue(err);
    await expect(changePassword(deps, form)).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });
});
