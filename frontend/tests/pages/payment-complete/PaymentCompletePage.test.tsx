import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { PaymentCompletePage } from '@/pages/payment-complete';
import type { Reservation } from '@/features/reservations';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { makeReservation } from '../../features/reservations/fakes/reservations';
import { signedInFakes } from '../../support/authFakes';
import { createFakes, renderRoutesWithDeps, type DepsFakes } from '../../support/renderWithDeps';

const routes: RouteObject[] = [
  { path: '/checkout/:reservationId/complete', element: <PaymentCompletePage /> },
  { path: '/reservations', element: <p>내 예약 화면</p> },
];

function customerFakes(): DepsFakes {
  const fakes = createFakes(signedInFakes(customerUser));
  fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'RESERVED' }));
  return fakes;
}

function renderPage(fakes: DepsFakes = customerFakes()) {
  return renderRoutesWithDeps(routes, { initialEntries: ['/checkout/r1/complete'], fakes });
}

describe('PaymentCompletePage (C4)', () => {
  // 픽스처는 2026-11-10 KST 기준. 실제 날짜가 지나도 「픽업 시간 지남」이 되지 않게 현재 시각을 고정한다.
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-11-10T16:00:00+09:00'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('픽업 코드·안내·「예약 확정」·픽업 시간대를 보여 준다', async () => {
    const { fakes } = renderPage();
    expect(await screen.findByText('A12345')).toBeInTheDocument();
    expect(fakes.reservations.get.mock.calls[0]?.[0]).toBe('r1');
    expect(screen.getByText('매장에서 이 코드를 보여 주세요')).toBeInTheDocument();
    expect(screen.getByText('예약 확정')).toBeInTheDocument();
    expect(screen.getByText(/18:00–20:00/)).toBeInTheDocument();
  });

  it('「내 예약 보기」를 누르면 /reservations로 이동한다', async () => {
    const { router } = renderPage();
    await screen.findByText('A12345');
    await userEvent.click(screen.getByText('내 예약 보기'));
    await waitFor(() => expect(router.state.location.pathname).toBe('/reservations'));
  });

  it('불러오는 동안 aria-busy(Skeleton)', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockReturnValue(deferred<Reservation>().promise);
    renderPage(fakes);
    await waitFor(() => expect(document.querySelector('[aria-busy="true"]')).not.toBeNull());
  });

  it('못 찾으면(403) 코드 없이 「내 예약 보기」', async () => {
    const fakes = customerFakes();
    fakes.reservations.get.mockRejectedValue(new ApiError(403, 'FORBIDDEN', '본인 예약 아님'));
    renderPage(fakes);
    expect(await screen.findByText('내 예약 보기')).toBeInTheDocument();
    expect(screen.queryByText('A12345')).not.toBeInTheDocument();
  });
});
