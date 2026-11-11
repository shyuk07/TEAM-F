import type { ReactNode } from 'react';
import { act, renderHook } from '@testing-library/react';
import { useReserveOffer } from '@/features/reservations/application/useReserveOffer';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { createDepsContainer, createFakes, type DepsFakes } from '../../../support/renderWithDeps';
import { makeReservation } from '../fakes/reservations';

function setup(fakes: DepsFakes = createFakes()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={createDepsContainer(fakes)}>{children}</DepsProvider>
  );
  return { ...renderHook(() => useReserveOffer('o1'), { wrapper }), fakes };
}

describe('useReserveOffer', () => {
  it('처음에는 모든 값이 비어 있다', () => {
    const { result } = setup();
    expect(result.current).toMatchObject({
      pending: false,
      error: null,
      pendingReservationId: null,
      createdReservationId: null,
    });
  });

  it('성공하면 createdReservationId', async () => {
    const { result, fakes } = setup();
    await act(async () => {
      await result.current.submit(2);
    });
    expect(fakes.reservations.create).toHaveBeenCalledWith(
      { offerId: 'o1', quantity: 2 },
      expect.anything(),
    );
    expect(result.current.createdReservationId).toBe('r-new');
    expect(result.current.pending).toBe(false);
  });

  it('409 PENDING_RESERVATION_EXISTS면 pendingReservationId와 error', async () => {
    const fakes = createFakes();
    fakes.reservations.create.mockRejectedValue(
      new ApiError(409, 'PENDING_RESERVATION_EXISTS', '중복'),
    );
    fakes.reservations.listMine.mockResolvedValue({
      items: [makeReservation({ id: 'found', offerId: 'o1', status: 'PENDING_PAYMENT' })],
      page: 1,
      size: 100,
      total: 1,
    });
    const { result } = setup(fakes);
    await act(async () => {
      await result.current.submit(1);
    });
    expect(result.current.pendingReservationId).toBe('found');
    expect(result.current.error).toMatchObject({ errorCode: 'PENDING_RESERVATION_EXISTS' });
    expect(result.current.createdReservationId).toBeNull();
  });

  it('409 OUT_OF_STOCK이면 error만', async () => {
    const fakes = createFakes();
    fakes.reservations.create.mockRejectedValue(new ApiError(409, 'OUT_OF_STOCK', '재고 부족'));
    const { result } = setup(fakes);
    await act(async () => {
      await result.current.submit(1);
    });
    expect(result.current.error).toEqual({ errorCode: 'OUT_OF_STOCK', message: '재고 부족' });
    expect(result.current.pendingReservationId).toBeNull();
    expect(result.current.pending).toBe(false);
  });
});
