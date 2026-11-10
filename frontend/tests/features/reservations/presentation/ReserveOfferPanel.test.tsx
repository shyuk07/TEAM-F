import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  ReserveOfferPanel,
  type ReserveOfferPanelProps,
} from '@/features/reservations/presentation/ReserveOfferPanel';
import type { CreatedReservation } from '@/features/reservations/domain/reservation';
import {
  PENDING_EXISTS_MESSAGE,
  PROCESSING_LABEL,
  RESERVE_CONTINUE_LABEL,
} from '@/features/reservations/domain/messages';
import { ApiError } from '@/shared/api/error';
import { createFakes, renderWithDeps, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';
import { makeReservation } from '../fakes/reservations';

function isDisabled(el: HTMLElement): boolean {
  return (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true';
}

function renderPanel(over: Partial<ReserveOfferPanelProps> = {}, fakes: DepsFakes = createFakes()) {
  const props: ReserveOfferPanelProps = {
    offerId: 'o1',
    unitPrice: 6000,
    remainingStock: 10,
    reservable: true,
    unavailableReason: null,
    isLoggedIn: true,
    onRequireLogin: vi.fn(),
    onGoToCheckout: vi.fn(),
    ...over,
  };
  renderWithDeps(<ReserveOfferPanel {...props} />, { fakes });
  return { props, fakes };
}

const plus = () => screen.getByRole('button', { name: '+' });
const minus = () => screen.getByRole('button', { name: '-' });

describe('ReserveOfferPanel (C2 예약 영역)', () => {
  it('기본 수량 1, 버튼 「예약하고 결제 6,000원」', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: '예약하고 결제 6,000원' })).toBeInTheDocument();
  });

  it('+를 누르면 금액이 수량만큼 바뀐다', async () => {
    renderPanel();
    await userEvent.click(plus());
    expect(screen.getByRole('button', { name: '예약하고 결제 12,000원' })).toBeInTheDocument();
  });

  it('재고 10이면 +를 4번 눌러 5가 된 뒤 + 비활성', async () => {
    renderPanel();
    const user = userEvent.setup();
    for (let i = 0; i < 4; i += 1) await user.click(plus());
    expect(screen.getByRole('button', { name: '예약하고 결제 30,000원' })).toBeInTheDocument();
    expect(isDisabled(plus())).toBe(true);
  });

  it('재고 3이면 3에서 + 비활성', async () => {
    renderPanel({ remainingStock: 3 });
    const user = userEvent.setup();
    await user.click(plus());
    await user.click(plus());
    expect(screen.getByRole('button', { name: '예약하고 결제 18,000원' })).toBeInTheDocument();
    expect(isDisabled(plus())).toBe(true);
  });

  it('수량 1에서 - 비활성', () => {
    renderPanel();
    expect(isDisabled(minus())).toBe(true);
  });

  it('reservable=false면 버튼 비활성 + 사유 표시', () => {
    renderPanel({ reservable: false, unavailableReason: '품절됐어요' });
    expect(isDisabled(screen.getByRole('button', { name: /예약하고 결제/ }))).toBe(true);
    expect(screen.getByText('품절됐어요')).toBeInTheDocument();
  });

  it('비로그인 클릭 → onRequireLogin(수량), 저장소 호출 없음', async () => {
    const { props, fakes } = renderPanel({ isLoggedIn: false });
    await userEvent.click(plus());
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    expect(props.onRequireLogin).toHaveBeenCalledWith(2);
    expect(fakes.reservations.create).not.toHaveBeenCalled();
  });

  it('처리 중에는 「처리 중…」 비활성', async () => {
    const fakes = createFakes();
    const d = deferred<CreatedReservation>();
    fakes.reservations.create.mockReturnValue(d.promise);
    renderPanel({}, fakes);
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    const busy = await screen.findByRole('button', { name: PROCESSING_LABEL });
    expect(isDisabled(busy)).toBe(true);
  });

  it('201이면 onGoToCheckout(새 예약 id)', async () => {
    const { props } = renderPanel();
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    await waitFor(() => expect(props.onGoToCheckout).toHaveBeenCalledWith('r-new'));
  });

  it('409 PENDING이면 중복 문구 + 「결제 이어하기」가 찾은 id로 이동한다', async () => {
    const fakes = createFakes();
    fakes.reservations.create.mockRejectedValue(
      new ApiError(409, 'PENDING_RESERVATION_EXISTS', '서버 문구'),
    );
    fakes.reservations.listMine.mockResolvedValue({
      items: [makeReservation({ id: 'found', offerId: 'o1', status: 'PENDING_PAYMENT' })],
      page: 1,
      size: 100,
      total: 1,
    });
    const { props } = renderPanel({}, fakes);
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    expect(await screen.findByText(PENDING_EXISTS_MESSAGE)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: RESERVE_CONTINUE_LABEL }));
    expect(props.onGoToCheckout).toHaveBeenCalledWith('found');
  });

  it('409 OUT_OF_STOCK이면 서버 message를 보여 준다', async () => {
    const fakes = createFakes();
    fakes.reservations.create.mockRejectedValue(
      new ApiError(409, 'OUT_OF_STOCK', '재고 부족 문구'),
    );
    renderPanel({}, fakes);
    await userEvent.click(screen.getByRole('button', { name: /예약하고 결제/ }));
    expect(await screen.findByText('재고 부족 문구')).toBeInTheDocument();
  });
});
