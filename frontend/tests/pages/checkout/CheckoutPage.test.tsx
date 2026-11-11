import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { CheckoutPage } from '@/pages/checkout';
import type { Reservation } from '@/features/reservations';
import { LEAVE_CONTINUE_LABEL } from '@/features/reservations/domain/messages';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { makeReservation } from '../../features/reservations/fakes/reservations';
import { signedInFakes } from '../../support/authFakes';
import { createFakes, renderRoutesWithDeps, type DepsFakes } from '../../support/renderWithDeps';

const routes: RouteObject[] = [
  { path: '/checkout/:reservationId', element: <CheckoutPage /> },
  { path: '/checkout/:reservationId/complete', element: <p>결제 완료 화면</p> },
  { path: '/me/reservations', element: <p>내 예약 화면</p> },
];

function customerFakes(): DepsFakes {
  return createFakes(signedInFakes({ ...customerUser, point: 1240 }));
}

function renderPage(fakes: DepsFakes = customerFakes()) {
  return renderRoutesWithDeps(routes, { initialEntries: ['/checkout/r1'], fakes });
}

function pending(): DepsFakes {
  const fakes = customerFakes();
  fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'PENDING_PAYMENT' }));
  return fakes;
}

describe('CheckoutPage (C3)', () => {
  it('예약을 불러오는 동안 aria-busy(Skeleton)', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockReturnValue(deferred<Reservation>().promise);
    renderPage(fakes);
    await waitFor(() => expect(document.querySelector('[aria-busy="true"]')).not.toBeNull());
    expect(screen.queryByRole('button', { name: /결제하기/ })).not.toBeInTheDocument();
  });

  it('경로의 reservationId로 단건 조회한다', async () => {
    const fakes = pending();
    renderPage(fakes);
    await waitFor(() => expect(fakes.reservations.get).toHaveBeenCalled());
    expect(fakes.reservations.get.mock.calls[0]?.[0]).toBe('r1');
  });

  it('PENDING_PAYMENT면 결제 폼(총액·보유 포인트)', async () => {
    renderPage(pending());
    expect(await screen.findByRole('button', { name: '결제하기 11,500원' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '전액' }));
    expect(screen.getByRole('button', { name: '결제하기 10,300원' })).toBeInTheDocument();
  });

  it('못 찾으면(404) 결제 폼 없이 「내 예약 보기」', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockRejectedValue(new ApiError(404, 'NOT_FOUND', '없음'));
    renderPage(fakes);
    expect(await screen.findByText('내 예약 보기')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /결제하기/ })).not.toBeInTheDocument();
  });

  it('PENDING_PAYMENT가 아니면 결제 폼 대신 「내 예약 보기」(D-6)', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'RESERVED' }));
    renderPage(fakes);
    expect(await screen.findByText('내 예약 보기')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /결제하기/ })).not.toBeInTheDocument();
  });

  it('뒤로 가기(←)를 누르면 C3a 시트가 열린다', async () => {
    renderPage(pending());
    await screen.findByRole('button', { name: /결제하기/ });
    await userEvent.click(screen.getByRole('button', { name: /←|뒤로/ }));
    expect(await screen.findByRole('button', { name: LEAVE_CONTINUE_LABEL })).toBeInTheDocument();
  });

  it('결제에 성공하면 C4 경로로 이동한다', async () => {
    const { router } = renderPage(pending());
    await userEvent.click(await screen.findByRole('button', { name: /결제하기/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/checkout/r1/complete'));
  });
});
