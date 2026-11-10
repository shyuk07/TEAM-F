import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useMyReservations } from '@/features/reservations/application/useMyReservations';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { createDepsContainer, createFakes, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';
import { at, makeReservation } from '../fakes/reservations';

type ListResult = Awaited<ReturnType<DepsFakes['reservations']['listMine']>>;

function setup(fakes: DepsFakes = createFakes()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={createDepsContainer(fakes)}>{children}</DepsProvider>
  );
  return { ...renderHook(() => useMyReservations(), { wrapper }), fakes };
}

describe('useMyReservations', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(at(16));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('loading에서 시작해 success가 되고 진행 중/지난 예약으로 나뉜다', async () => {
    const fakes = createFakes();
    const active = makeReservation({ id: 'a', status: 'RESERVED' });
    const past = makeReservation({ id: 'p', status: 'PICKED_UP' });
    fakes.reservations.listMine.mockResolvedValue({
      items: [active, past],
      page: 1,
      size: 100,
      total: 2,
    });
    const { result } = setup(fakes);
    expect(result.current.status).toBe('loading');
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current).toMatchObject({ active: [active], past: [past] });
  });

  it('빈 목록이면 success, 두 탭 모두 빈 배열', async () => {
    const { result } = setup();
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current).toMatchObject({ active: [], past: [] });
  });

  it('오류면 error와 errorCode·message', async () => {
    const fakes = createFakes();
    fakes.reservations.listMine.mockRejectedValue(new ApiError(500, 'INTERNAL', '서버 오류'));
    const { result } = setup(fakes);
    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current).toMatchObject({ errorCode: 'INTERNAL', message: '서버 오류' });
  });

  it('언마운트하면 signal이 abort되고 이후 상태가 바뀌지 않는다', async () => {
    const fakes = createFakes();
    const d = deferred<ListResult>();
    fakes.reservations.listMine.mockReturnValue(d.promise);
    const { result, unmount } = setup(fakes);
    await waitFor(() => expect(fakes.reservations.listMine).toHaveBeenCalled());
    const signal = fakes.reservations.listMine.mock.calls[0]?.[1];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      d.resolve({ items: [], page: 1, size: 100, total: 0 });
    });
    expect(result.current.status).toBe('loading');
  });

  it('reload()는 다시 조회한다', async () => {
    const { result, fakes } = setup();
    await waitFor(() => expect(result.current.status).toBe('success'));
    act(() => result.current.reload());
    await waitFor(() => expect(fakes.reservations.listMine).toHaveBeenCalledTimes(2));
  });
});
