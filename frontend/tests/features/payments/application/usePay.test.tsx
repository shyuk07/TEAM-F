import type { ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { usePay } from '@/features/payments/application/usePay';
import type { Payment } from '@/features/payments';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { createDepsContainer, createFakes, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';

const input = { reservationId: 'r1', usePoint: 500 };

function setup(fakes: DepsFakes = createFakes()) {
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={createDepsContainer(fakes)}>{children}</DepsProvider>
  );
  return { ...renderHook(() => usePay(), { wrapper }), fakes };
}

describe('usePay', () => {
  it('성공하면 Payment를 돌려주고 error null', async () => {
    const { result, fakes } = setup();
    let paid: Payment | null | undefined;
    await act(async () => {
      paid = await result.current.pay(input);
    });
    expect(fakes.payments.pay).toHaveBeenCalledWith(input, expect.anything());
    expect(paid).toMatchObject({ id: 'p1', reservationId: 'r1' });
    expect(result.current.error).toBeNull();
    expect(result.current.pending).toBe(false);
  });

  it('pending 중 두 번째 호출은 무시한다', async () => {
    const fakes = createFakes();
    const d = deferred<Payment>();
    fakes.payments.pay.mockReturnValue(d.promise);
    const { result } = setup(fakes);
    let first: Promise<Payment | null> | undefined;
    act(() => {
      first = result.current.pay(input);
    });
    await waitFor(() => expect(result.current.pending).toBe(true));
    await act(async () => {
      void result.current.pay(input);
    });
    expect(fakes.payments.pay).toHaveBeenCalledTimes(1);
    await act(async () => {
      d.resolve({ id: 'p1', reservationId: 'r1', amount: 11000, status: 'PAID', paidAt: null });
      await first;
    });
    expect(result.current.pending).toBe(false);
  });

  it('실패하면 null과 error{status, errorCode, message}, pending false', async () => {
    const fakes = createFakes();
    fakes.payments.pay.mockRejectedValue(new ApiError(409, 'CONFLICT', '이미 결제됨'));
    const { result } = setup(fakes);
    let paid: Payment | null | undefined;
    await act(async () => {
      paid = await result.current.pay(input);
    });
    expect(paid).toBeNull();
    expect(result.current.error).toEqual({
      status: 409,
      errorCode: 'CONFLICT',
      message: '이미 결제됨',
    });
    expect(result.current.pending).toBe(false);
  });

  it('언마운트 뒤 응답이 와도 상태를 바꾸지 않는다(오류 없음)', async () => {
    const fakes = createFakes();
    const d = deferred<Payment>();
    fakes.payments.pay.mockReturnValue(d.promise);
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { result, unmount } = setup(fakes);
    let first: Promise<Payment | null> | undefined;
    act(() => {
      first = result.current.pay(input);
    });
    unmount();
    await act(async () => {
      d.resolve({ id: 'p1', reservationId: 'r1', amount: 11000, status: 'PAID', paidAt: null });
      await first;
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});
