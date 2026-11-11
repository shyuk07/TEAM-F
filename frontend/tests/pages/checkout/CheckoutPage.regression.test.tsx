import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterProvider, createMemoryRouter, type RouteObject } from 'react-router';
import { CheckoutPage } from '@/pages/checkout';
import type { Payment } from '@/features/payments';
import { LEAVE_CANCEL_LABEL } from '@/features/reservations/domain/messages';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { makeReservation } from '../../features/reservations/fakes/reservations';
import { signedInFakes } from '../../support/authFakes';
import { createFakes, withDeps, type DepsFakes } from '../../support/renderWithDeps';

// fe-reviewer 지적 1·2 재현: ← 동작과 결제 성공 이동 방식
const routes: RouteObject[] = [
  { path: '/prev', element: <p>이전 화면</p> },
  { path: '/checkout/:reservationId', element: <CheckoutPage /> },
  { path: '/checkout/:reservationId/complete', element: <p>결제 완료 화면</p> },
  { path: '/me/reservations', element: <p>내 예약 화면</p> },
  { path: '/', element: <p>홈 화면</p> },
];

function customerFakes(): DepsFakes {
  return createFakes(signedInFakes({ ...customerUser, point: 1240 }));
}

/** 이전 화면(/prev)에서 /checkout/r1로 들어온 기록을 만든다. */
function renderPage(fakes: DepsFakes) {
  const router = createMemoryRouter(routes, {
    initialEntries: ['/prev', '/checkout/r1'],
    initialIndex: 1,
  });
  render(withDeps(fakes, <RouterProvider router={router} />));
  return { router, fakes };
}

const back = () => screen.getByRole('button', { name: /←|뒤로/ });

function isDisabled(el: HTMLElement): boolean {
  return (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true';
}

describe('CheckoutPage 회귀: 결제 대기가 아니면 ←는 시트 없이 뒤로 간다', () => {
  it.each([
    ['RESERVED', () => Promise.resolve(makeReservation({ status: 'RESERVED' }))],
    ['notFound(404)', () => Promise.reject(new ApiError(404, 'NOT_FOUND', '없음'))],
    ['error(500)', () => Promise.reject(new ApiError(500, 'INTERNAL', '서버 오류'))],
  ])('%s: ← → 이전 화면, 취소 시트·취소 API 없음', async (_label, impl) => {
    const fakes = customerFakes();
    fakes.reservations.get.mockImplementation(impl);
    const { router } = renderPage(fakes);
    await screen.findByText('내 예약 보기');
    await userEvent.click(back());
    await waitFor(() => expect(router.state.location.pathname).toBe('/prev'));
    expect(screen.queryByRole('button', { name: LEAVE_CANCEL_LABEL })).not.toBeInTheDocument();
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
  });
});

describe('CheckoutPage 회귀: 결제 성공 이동은 replace', () => {
  it('C4로 이동한 뒤 뒤로 가면 결제 화면이 아니라 이전 화면이다', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'PENDING_PAYMENT' }));
    const { router } = renderPage(fakes);
    await userEvent.click(await screen.findByRole('button', { name: /결제하기/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/checkout/r1/complete'));
    await router.navigate(-1);
    await waitFor(() => expect(router.state.location.pathname).toBe('/prev'));
  });
});

describe('CheckoutPage 회귀: 결제 처리 중에는 나가기·취소가 막힌다', () => {
  it('pending 동안 ←는 비활성이거나 눌러도 시트가 열리지 않고 취소 API 0회', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'PENDING_PAYMENT' }));
    fakes.payments.pay.mockReturnValue(deferred<Payment>().promise);
    const { router } = renderPage(fakes);
    await userEvent.click(await screen.findByRole('button', { name: /결제하기/ }));
    await screen.findByRole('button', { name: '처리 중…' });
    const b = back();
    if (!isDisabled(b)) await userEvent.click(b);
    expect(screen.queryByRole('button', { name: LEAVE_CANCEL_LABEL })).not.toBeInTheDocument();
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
    expect(router.state.location.pathname).toBe('/checkout/r1');
  });

  it('시트가 열린 뒤 결제가 처리 중이면 「예약 취소하고 나가기」가 비활성이다', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'PENDING_PAYMENT' }));
    fakes.payments.pay.mockReturnValue(deferred<Payment>().promise);
    renderPage(fakes);
    const pay = await screen.findByRole('button', { name: /결제하기/ });
    await userEvent.click(back());
    const cancelBtn = await screen.findByRole('button', { name: LEAVE_CANCEL_LABEL });
    // 시트가 떠 있어도 결제 버튼은 화면에 남아 있다. 결제를 시작한다.
    await userEvent.click(pay);
    await screen.findByRole('button', { name: '처리 중…' });
    if (!isDisabled(cancelBtn) && cancelBtn.isConnected) await userEvent.click(cancelBtn);
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
  });
});
