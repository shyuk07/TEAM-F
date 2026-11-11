import { withdrawAccount } from '@/features/auth/application/withdraw';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';

function setup() {
  const account = new FakeAccountGateway();
  const session = new FakeSessionStore(true);
  return { account, session, deps: { account, session } };
}

describe('withdrawAccount', () => {
  it("성공하면 account.withdraw('pw') 뒤 session.clear() 순서로 부른다", async () => {
    const { account, session, deps } = setup();
    const order: string[] = [];
    account.withdraw.mockImplementation(() => {
      order.push('withdraw');
      return Promise.resolve();
    });
    session.clear.mockImplementation(() => {
      order.push('clear');
    });
    await withdrawAccount(deps, 'pw');
    expect(account.withdraw.mock.calls[0]?.[0]).toBe('pw');
    expect(order).toEqual(['withdraw', 'clear']);
  });

  it('CURRENT_PASSWORD_MISMATCH(400)면 clear 없이 reject', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(
      400,
      'CURRENT_PASSWORD_MISMATCH',
      '현재 비밀번호가 올바르지 않습니다.',
    );
    account.withdraw.mockRejectedValue(err);
    await expect(withdrawAccount(deps, 'pw')).rejects.toBe(err);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('401이면 session.clear() 뒤 reject', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(401, 'UNAUTHORIZED', 'x');
    account.withdraw.mockRejectedValue(err);
    await expect(withdrawAccount(deps, 'pw')).rejects.toBe(err);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });
});
