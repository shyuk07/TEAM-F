import { loadPoints } from '@/features/auth/application/points';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { FakeSessionStore } from '../fakes/fakeSessionStore.fake';
import { makePointPage, recentLogs } from '../fakes/points';

function setup() {
  const account = new FakeAccountGateway();
  const session = new FakeSessionStore(true);
  return { account, session, deps: { account, session } };
}

describe('loadPoints', () => {
  it('성공하면 findPoints 결과를 그대로 돌려주고 signal을 넘긴다', async () => {
    const { account, session, deps } = setup();
    const page = makePointPage(recentLogs(), { size: 3, total: 3 });
    account.findPoints.mockResolvedValue(page);
    const signal = new AbortController().signal;
    await expect(loadPoints(deps, { page: 0, size: 3 }, signal)).resolves.toBe(page);
    expect(account.findPoints).toHaveBeenCalledWith({ page: 0, size: 3 }, signal);
    expect(session.clear).not.toHaveBeenCalled();
  });

  it('401이면 session.clear() 뒤 같은 오류로 reject', async () => {
    const { account, session, deps } = setup();
    const err = new ApiError(401, 'UNAUTHORIZED', 'x');
    account.findPoints.mockRejectedValue(err);
    await expect(loadPoints(deps, { page: 0, size: 3 })).rejects.toBe(err);
    expect(session.clear).toHaveBeenCalledTimes(1);
  });
});
