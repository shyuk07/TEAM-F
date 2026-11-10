import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, RouterProvider, createMemoryRouter } from 'react-router';
import { MyReservationList } from '@/features/reservations';
import { formatDate, formatTime, formatTimeRange } from '@/features/reservations/domain/format';
import { ReserveOfferPanel } from '@/features/reservations/presentation/ReserveOfferPanel';
import { ApiError } from '@/shared/api/error';
import { createFakes, renderWithDeps, withDeps } from '../../support/renderWithDeps';
import { at, makeReservation } from './fakes/reservations';

// fe-reviewer 지적 3·4·6 재현

describe('회귀 3: 진행 중 탭은 현재 시각(useNow)으로 다시 나뉜다', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'] });
    vi.setSystemTime(at(19, 59, 50));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('pickup_end(20:00)가 지나면 RESERVED 예약이 진행 중 탭에서 빠진다', async () => {
    const fakes = createFakes();
    const r = makeReservation({ id: 'a', productName: '진행 상품', status: 'RESERVED' });
    fakes.reservations.listMine.mockResolvedValue({ items: [r], page: 1, size: 100, total: 1 });
    renderWithDeps(
      <MemoryRouter>
        <MyReservationList
          tab="active"
          onTabChange={vi.fn()}
          onCancel={vi.fn()}
          onContinuePayment={vi.fn()}
        />
      </MemoryRouter>,
      { fakes },
    );
    await act(async () => {});
    await act(async () => {});
    expect(screen.getByText(/진행 상품/)).toBeInTheDocument();
    await act(async () => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.queryByText(/진행 상품/)).not.toBeInTheDocument();
  });
});

describe('회귀 4: ID를 못 찾은 중복 예약의 「내 예약 보기」는 라우터 링크다', () => {
  it('누르면 라우터 안에서 /me/reservations로 이동한다', async () => {
    const fakes = createFakes();
    fakes.reservations.create.mockRejectedValue(
      new ApiError(409, 'PENDING_RESERVATION_EXISTS', '중복'),
    );
    const router = createMemoryRouter(
      [
        {
          path: '/offer',
          element: (
            <ReserveOfferPanel
              offerId="o1"
              unitPrice={6000}
              remainingStock={10}
              reservable
              unavailableReason={null}
              isLoggedIn
              onRequireLogin={vi.fn()}
              onGoToCheckout={vi.fn()}
            />
          ),
        },
        { path: '/me/reservations', element: <p>내 예약 화면</p> },
      ],
      { initialEntries: ['/offer'] },
    );
    render(withDeps(fakes, <RouterProvider router={router} />));
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    await userEvent.click(await screen.findByText('내 예약 보기'));
    expect(router.state.location.pathname).toBe('/me/reservations');
    expect(await screen.findByText('내 예약 화면')).toBeInTheDocument();
  });
});

describe('회귀 6: 시각 표시는 브라우저 시간대와 무관하게 Asia/Seoul', () => {
  // 브라우저가 UTC 시간대인 것처럼 로컬 getter를 UTC 값으로 바꾼다.
  beforeEach(() => {
    vi.spyOn(Date.prototype, 'getHours').mockImplementation(function (this: Date) {
      return this.getUTCHours();
    });
    vi.spyOn(Date.prototype, 'getMinutes').mockImplementation(function (this: Date) {
      return this.getUTCMinutes();
    });
    vi.spyOn(Date.prototype, 'getDate').mockImplementation(function (this: Date) {
      return this.getUTCDate();
    });
    vi.spyOn(Date.prototype, 'getMonth').mockImplementation(function (this: Date) {
      return this.getUTCMonth();
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('09:00Z → 18:00', () => {
    expect(formatTime(new Date('2026-11-10T09:00:00Z'))).toBe('18:00');
  });

  it('09:00Z–11:00Z → 18:00–20:00', () => {
    expect(
      formatTimeRange(new Date('2026-11-10T09:00:00Z'), new Date('2026-11-10T11:00:00Z')),
    ).toBe('18:00–20:00');
  });

  it('2026-11-06T16:00Z(KST 11/07 01:00) → 11/07', () => {
    expect(formatDate(new Date('2026-11-06T16:00:00Z'))).toBe('11/07');
  });
});
