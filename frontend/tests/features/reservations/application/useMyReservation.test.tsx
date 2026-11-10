import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useMyReservation } from '@/features/reservations';
import type { Reservation } from '@/features/reservations';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { createDepsContainer, createFakes, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';
import { makeReservation } from '../fakes/reservations';

function setup(fakes: DepsFakes = createFakes(), id = 'r1') {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={createDepsContainer(fakes)}>{children}</DepsProvider>
  );
  return { ...renderHook(() => useMyReservation(id), { wrapper }), fakes };
}

describe('useMyReservation (단건 조회 repo.get)', () => {
  it('loading에서 시작해 get(id) 결과로 success', async () => {
    const fakes = createFakes();
    const r = makeReservation({ id: 'r1' });
    fakes.reservations.get.mockResolvedValue(r);
    const { result } = setup(fakes);
    expect(result.current).toEqual({ status: 'loading' });
    await waitFor(() => expect(result.current).toEqual({ status: 'success', reservation: r }));
    expect(fakes.reservations.get.mock.calls[0]?.[0]).toBe('r1');
    expect(fakes.reservations.listMine).not.toHaveBeenCalled();
  });

  it.each([403, 404])('%i이면 notFound', async (status) => {
    const fakes = createFakes();
    fakes.reservations.get.mockRejectedValue(new ApiError(status, 'X', '없음'));
    const { result } = setup(fakes);
    await waitFor(() => expect(result.current).toEqual({ status: 'notFound' }));
  });

  it('그 밖의 오류는 error와 errorCode·message', async () => {
    const fakes = createFakes();
    fakes.reservations.get.mockRejectedValue(new ApiError(500, 'INTERNAL', '서버 오류'));
    const { result } = setup(fakes);
    await waitFor(() =>
      expect(result.current).toEqual({
        status: 'error',
        errorCode: 'INTERNAL',
        message: '서버 오류',
      }),
    );
  });

  it('언마운트하면 signal이 abort되고 이후 상태가 바뀌지 않는다', async () => {
    const fakes = createFakes();
    const d = deferred<Reservation>();
    fakes.reservations.get.mockReturnValue(d.promise);
    const { result, unmount } = setup(fakes);
    await waitFor(() => expect(fakes.reservations.get).toHaveBeenCalled());
    const signal = fakes.reservations.get.mock.calls[0]?.[1];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      d.resolve(makeReservation());
    });
    expect(result.current).toEqual({ status: 'loading' });
  });
});
