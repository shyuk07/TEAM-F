import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { ApiError } from '@/shared/api/error';
import { MyReservationsPage } from '@/pages/my-reservations';
import {
  CANCEL_SHEET_CONFIRM_LABEL,
  RESERVE_CONTINUE_LABEL,
  TAB_PAST_LABEL,
} from '@/features/reservations/domain/messages';
import { customerUser } from '../../features/auth/fakes/users';
import { at, makeReservation } from '../../features/reservations/fakes/reservations';
import { signedInFakes } from '../../support/authFakes';
import { createFakes, renderRoutesWithDeps, type DepsFakes } from '../../support/renderWithDeps';

const routes: RouteObject[] = [
  { path: '/me/reservations', element: <MyReservationsPage /> },
  { path: '/checkout/:reservationId', element: <p>결제 화면</p> },
  { path: '/', element: <p>홈 화면</p> },
];

const reserved = makeReservation({ id: 'a', productName: '진행 상품', status: 'RESERVED' });
const pendingPay = makeReservation({
  id: 'pp',
  offerId: 'o2',
  productName: '대기 상품',
  status: 'PENDING_PAYMENT',
});
const picked = makeReservation({ id: 'p', productName: '지난 상품', status: 'PICKED_UP' });

function fakesWithList(): DepsFakes {
  const fakes = createFakes(signedInFakes(customerUser));
  const items = [reserved, pendingPay, picked];
  fakes.reservations.listMine.mockResolvedValue({ items, page: 1, size: 100, total: 3 });
  return fakes;
}

function renderPage(entry = '/me/reservations', fakes: DepsFakes = fakesWithList()) {
  return renderRoutesWithDeps(routes, { initialEntries: [entry], fakes });
}

describe('MyReservationsPage (C5·C5b)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(at(16));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('제목 「내 예약」과 진행 중 예약을 보여 준다', async () => {
    renderPage();
    expect(screen.getByRole('heading', { name: '내 예약' })).toBeInTheDocument();
    expect(await screen.findByText(/진행 상품/)).toBeInTheDocument();
    expect(screen.queryByText(/지난 상품/)).not.toBeInTheDocument();
  });

  it('?tab=past면 지난 예약을 보여 준다', async () => {
    renderPage('/me/reservations?tab=past');
    expect(await screen.findByText(/지난 상품/)).toBeInTheDocument();
    expect(screen.queryByText(/진행 상품/)).not.toBeInTheDocument();
  });

  it('칩 「지난 예약」을 누르면 쿼리 tab=past가 된다', async () => {
    const { router } = renderPage();
    await screen.findByText(/진행 상품/);
    await userEvent.click(screen.getByText(TAB_PAST_LABEL));
    await waitFor(() => expect(router.state.location.search).toBe('?tab=past'));
    expect(await screen.findByText(/지난 상품/)).toBeInTheDocument();
  });

  it('「결제 이어하기」를 누르면 C3 경로로 이동한다', async () => {
    const { router } = renderPage();
    await userEvent.click(await screen.findByRole('button', { name: RESERVE_CONTINUE_LABEL }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/checkout/pp'));
  });

  it('「예약 취소」 → 시트에서 확인하면 취소 후 목록을 다시 불러온다', async () => {
    const { fakes } = renderPage();
    await userEvent.click(await screen.findByText('예약 취소 · 17:00까지'));
    await userEvent.click(await screen.findByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }));
    await waitFor(() => expect(fakes.reservations.cancel.mock.calls[0]?.[0]).toBe('a'));
    await waitFor(() => expect(fakes.reservations.listMine).toHaveBeenCalledTimes(2));
  });

  it.each([
    [400, 'CANCELLATION_DEADLINE_PASSED', '취소 가능 시각이 지났습니다.'],
    [409, 'INVALID_RESERVATION_STATUS', '이미 픽업된 예약입니다.'],
  ])(
    '%s 취소 실패도 오류를 유지하면서 최신 예약 목록을 다시 읽는다',
    async (status, code, message) => {
      const fakes = fakesWithList();
      const latest = makeReservation({ ...reserved, status: 'PICKED_UP' });
      fakes.reservations.listMine
        .mockResolvedValueOnce({ items: [reserved], page: 1, size: 100, total: 1 })
        .mockResolvedValue({ items: [latest], page: 1, size: 100, total: 1 });
      fakes.reservations.cancel.mockRejectedValue(new ApiError(status, code, message));
      renderPage('/me/reservations', fakes);
      await userEvent.click(await screen.findByText('예약 취소 · 17:00까지'));
      await userEvent.click(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }));
      expect(await screen.findByText(message)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL })).toBeEnabled();
      await waitFor(() => expect(fakes.reservations.listMine).toHaveBeenCalledTimes(2));
      await userEvent.click(screen.getByRole('button', { name: '돌아가기' }));
      expect(screen.queryByText('예약 취소 · 17:00까지')).not.toBeInTheDocument();
      await userEvent.click(screen.getByText(TAB_PAST_LABEL));
      expect(await screen.findByText('픽업 완료')).toBeInTheDocument();
    },
  );
});
