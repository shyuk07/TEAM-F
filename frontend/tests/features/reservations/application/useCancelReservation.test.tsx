import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useCancelReservation } from '@/features/reservations/application/useCancelReservation';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { createDepsContainer, createFakes, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';

type CancelResult = Awaited<ReturnType<DepsFakes['reservations']['cancel']>>;

function setup(fakes: DepsFakes = createFakes()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={createDepsContainer(fakes)}>{children}</DepsProvider>
  );
  return { ...renderHook(() => useCancelReservation(), { wrapper }), fakes };
}

describe('useCancelReservation', () => {
  it('성공하면 true, error null', async () => {
    const { result, fakes } = setup();
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.cancel('r1');
    });
    expect(fakes.reservations.cancel).toHaveBeenCalledWith('r1', expect.anything());
    expect(ok).toBe(true);
    expect(result.current.error).toBeNull();
    expect(result.current.pending).toBe(false);
  });

  it('pending 동안 두 번째 호출은 무시한다', async () => {
    const fakes = createFakes();
    const d = deferred<CancelResult>();
    fakes.reservations.cancel.mockReturnValue(d.promise);
    const { result } = setup(fakes);
    let first: Promise<boolean> | undefined;
    act(() => {
      first = result.current.cancel('r1');
    });
    await waitFor(() => expect(result.current.pending).toBe(true));
    await act(async () => {
      void result.current.cancel('r1');
    });
    expect(fakes.reservations.cancel).toHaveBeenCalledTimes(1);
    await act(async () => {
      d.resolve({ id: 'r1', status: 'CANCELLED', cancelledBy: 'CUSTOMER' });
      await first;
    });
    expect(result.current.pending).toBe(false);
  });

  it('400이면 false와 error(errorCode·message)', async () => {
    const fakes = createFakes();
    fakes.reservations.cancel.mockRejectedValue(
      new ApiError(400, 'CANCELLATION_DEADLINE_PASSED', '마감 지남'),
    );
    const { result } = setup(fakes);
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.cancel('r1');
    });
    expect(ok).toBe(false);
    expect(result.current.error).toEqual({
      errorCode: 'CANCELLATION_DEADLINE_PASSED',
      message: '마감 지남',
    });
    expect(result.current.pending).toBe(false);
  });
});
