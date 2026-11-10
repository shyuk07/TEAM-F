import {
  confirmPasswordReset,
  requestPasswordReset,
} from '@/features/auth/application/passwordReset';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';

const input = { email: 'a@b.c', code: '123456', newPassword: 'pw123456' };

function setup() {
  const account = new FakeAccountGateway();
  const session = new FakeSessionStore(true);
  return { account, session, deps: { account, session } };
}

describe('requestPasswordReset', () => {
  it('이메일 앞뒤 공백을 지워 요청한다', async () => {
    const { account, deps } = setup();
    await requestPasswordReset(deps, ' a@b.c ');
    expect(account.requestPasswordReset.mock.calls[0]?.[0]).toBe('a@b.c');
  });

  it('요청 실패를 그대로 전파한다', async () => {
    const { account, deps } = setup();
    const err = new ApiError(0, 'NETWORK_ERROR', '네트워크 문구');
    account.requestPasswordReset.mockRejectedValue(err);
    await expect(requestPasswordReset(deps, 'a@b.c')).rejects.toBe(err);
  });
});

describe('confirmPasswordReset', () => {
  it('확인 성공 뒤 session.clear()를 부른다(순서)', async () => {
    const { account, session, deps } = setup();
    await confirmPasswordReset(deps, input);
    expect(account.confirmPasswordReset.mock.calls[0]?.[0]).toEqual(input);
    expect(session.clear).toHaveBeenCalledTimes(1);
    expect(account.confirmPasswordReset.mock.invocationCallOrder[0]).toBeLessThan(
      session.clear.mock.invocationCallOrder[0],
    );
  });

  it('INVALID_RESET_CODE면 clear를 부르지 않고 같은 오류로 reject한다', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(
      400,
      'INVALID_RESET_CODE',
      '재설정 코드가 올바르지 않거나 만료되었습니다.',
    );
    account.confirmPasswordReset.mockRejectedValue(err);
    await expect(confirmPasswordReset(deps, input)).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('VALIDATION_ERROR면 clear를 부르지 않는다', async () => {
    const { account, session, deps } = setup();
    account.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '서버 규칙 문구'),
    );
    await expect(confirmPasswordReset(deps, input)).rejects.toBeInstanceOf(ApiError);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('게이트웨이 호출과 clear는 각 1회다', async () => {
    const { account, session, deps } = setup();
    await confirmPasswordReset(deps, input);
    expect(account.confirmPasswordReset).toHaveBeenCalledTimes(1);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });
});
