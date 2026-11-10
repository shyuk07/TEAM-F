import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { MyReservationList } from '@/features/reservations';
import type { ReservationTab } from '@/features/reservations/domain/grouping';
import {
  EMPTY_ACTION_LABEL,
  RETRY_LABEL,
  TAB_ACTIVE_LABEL,
  TAB_PAST_LABEL,
} from '@/features/reservations/domain/messages';
import type { Reservation } from '@/features/reservations';
import { ApiError } from '@/shared/api/error';
import { createFakes, renderWithDeps, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';
import { at, makeReservation } from '../fakes/reservations';

type ListResult = Awaited<ReturnType<DepsFakes['reservations']['listMine']>>;

function renderList(tab: ReservationTab, fakes: DepsFakes = createFakes()) {
  const onTabChange = vi.fn();
  renderWithDeps(
    <MemoryRouter>
      <MyReservationList
        tab={tab}
        onTabChange={onTabChange}
        onCancel={vi.fn()}
        onContinuePayment={vi.fn()}
      />
    </MemoryRouter>,
    { fakes },
  );
  return { onTabChange, fakes };
}

function withItems(items: Reservation[]): DepsFakes {
  const fakes = createFakes();
  fakes.reservations.listMine.mockResolvedValue({ items, page: 1, size: 100, total: items.length });
  return fakes;
}

const activeItem = makeReservation({ id: 'a', productName: '진행 상품', status: 'RESERVED' });
const pastItem = makeReservation({ id: 'p', productName: '지난 상품', status: 'PICKED_UP' });

describe('MyReservationList (C5·C5b)', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(at(16));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('로딩 중에는 aria-busy 영역(Skeleton)이 있다', () => {
    const fakes = createFakes();
    fakes.reservations.listMine.mockReturnValue(deferred<ListResult>().promise);
    renderList('active', fakes);
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('빈 목록이면 「할인 보러 가기」', async () => {
    renderList('active');
    expect(await screen.findByText(EMPTY_ACTION_LABEL)).toBeInTheDocument();
  });

  it('에러면 서버 message와 「다시 시도」, 누르면 다시 조회한다', async () => {
    const fakes = createFakes();
    fakes.reservations.listMine.mockRejectedValueOnce(new ApiError(500, 'INTERNAL', '목록 오류'));
    renderList('active', fakes);
    expect(await screen.findByText('목록 오류')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: RETRY_LABEL }));
    await waitFor(() => expect(fakes.reservations.listMine).toHaveBeenCalledTimes(2));
  });

  it('tab=active면 진행 중 예약만 보인다', async () => {
    renderList('active', withItems([activeItem, pastItem]));
    expect(await screen.findByText(/진행 상품/)).toBeInTheDocument();
    expect(screen.queryByText(/지난 상품/)).not.toBeInTheDocument();
  });

  it('tab=past면 지난 예약만 보인다', async () => {
    renderList('past', withItems([activeItem, pastItem]));
    expect(await screen.findByText(/지난 상품/)).toBeInTheDocument();
    expect(screen.queryByText(/진행 상품/)).not.toBeInTheDocument();
  });

  it('칩 「지난 예약」을 누르면 onTabChange(past), 「진행 중」은 onTabChange(active)', async () => {
    const { onTabChange } = renderList('active', withItems([activeItem, pastItem]));
    await userEvent.click(await screen.findByText(TAB_PAST_LABEL));
    expect(onTabChange).toHaveBeenLastCalledWith('past');
    await userEvent.click(screen.getByText(TAB_ACTIVE_LABEL));
    expect(onTabChange).toHaveBeenLastCalledWith('active');
  });
});
