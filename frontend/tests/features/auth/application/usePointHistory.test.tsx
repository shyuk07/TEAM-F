import { act, waitFor } from '@testing-library/react';
import { usePointHistory } from '@/features/auth';
import { ApiError } from '@/shared/api/error';
import { signedInFakes } from '../../../support/authFakes';
import { renderAuthHook } from '../../../support/renderAuthHook';
import { makePointLogs, makePointPage, recentLogs } from '../fakes/points';
import { customerUser } from '../fakes/users';

function setup(pageSize = 3) {
  const fakes = signedInFakes(customerUser);
  return { fakes, run: () => renderAuthHook(() => usePointHistory(pageSize), { fakes }) };
}

describe('usePointHistory', () => {
  it('마운트하면 findPoints({page:0, size:3})를 부르고 balance·logs를 돌려준다', async () => {
    const { fakes, run } = setup(3);
    fakes.account.findPoints.mockResolvedValue(
      makePointPage(recentLogs(), { balance: 1240, size: 3, total: 3 }),
    );
    const { result } = run();
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(fakes.account.findPoints.mock.calls[0]?.[0]).toEqual({ page: 0, size: 3 });
    expect(result.current.balance).toBe(1240);
    expect(result.current.logs).toHaveLength(3);
    expect(result.current.hasMore).toBe(false);
  });

  it('0건이면 empty이고 balance는 있다', async () => {
    const { fakes, run } = setup();
    fakes.account.findPoints.mockResolvedValue(makePointPage([], { balance: 300, total: 0 }));
    const { result } = run();
    await waitFor(() => expect(result.current.status).toBe('empty'));
    expect(result.current.balance).toBe(300);
  });

  it('total 25면 hasMore, loadMore()는 page 1을 받아 이어 붙인다', async () => {
    const { fakes, run } = setup(20);
    fakes.account.findPoints.mockResolvedValueOnce(makePointPage(makePointLogs(20), { total: 25 }));
    fakes.account.findPoints.mockResolvedValueOnce(
      makePointPage(makePointLogs(5, 21), { page: 1, total: 25 }),
    );
    const { result } = run();
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.hasMore).toBe(true);
    act(() => result.current.loadMore());
    await waitFor(() => expect(result.current.logs).toHaveLength(25));
    expect(fakes.account.findPoints.mock.calls[1]?.[0]).toEqual({ page: 1, size: 20 });
    expect(result.current.hasMore).toBe(false);
  });

  it('실패하면 error, balance는 null', async () => {
    const { fakes, run } = setup();
    fakes.account.findPoints.mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    const { result } = run();
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.balance).toBeNull();
  });
});
