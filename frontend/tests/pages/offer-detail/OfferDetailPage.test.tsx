import { act, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { InitialEntry } from 'react-router';
import { routes } from '@/app/router/routes';
import { BACK_LABEL, RETRY_LABEL } from '@/features/auth';
import {
  OFFER_DETAIL_LOAD_FAILED_MESSAGE,
  OFFER_NOT_FOUND_MESSAGE,
  unavailableMessage,
  type OfferDetail,
} from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { NOW, fixNow, restoreNow } from '../../support/clock';
import { renderRoutesWithOfferDetail } from '../../support/renderWithOfferDetail';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { makeOfferDetail } from '../../features/offers/fakes/offerDetails';

// 시각: 고정 NOW(2026-11-10 17:18 로컬), 기본 할인은 18:00 판매 마감·남은 3개·6,000원.

type Opts = { fakes: AuthFakes; entry?: InitialEntry };

function renderDetail(opts: Opts) {
  return renderRoutesWithOfferDetail(routes, {
    initialEntries: [opts.entry ?? '/offers/o1'],
    fakes: opts.fakes,
  });
}

function withDetail(detail: OfferDetail = makeOfferDetail(), fakes: AuthFakes = anonymousFakes()) {
  fakes.offers.findById.mockResolvedValue(detail);
  return fakes;
}

const reserveButton = () => screen.findByRole('button', { name: /^예약하고 결제/ });
const stepperValue = () => document.querySelector('.cta .step b')?.textContent;

describe('OfferDetailPage (C2)', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('로딩: 스켈레톤, 제목 「할인 상세」, 예약 버튼 없음', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findById.mockReturnValue(deferred<OfferDetail>().promise);
    renderDetail({ fakes });
    expect(await screen.findByRole('heading', { level: 1, name: '할인 상세' })).toBeInTheDocument();
    expect(document.querySelectorAll('.sk')).toHaveLength(3);
    expect(screen.queryByRole('button', { name: /예약하고 결제/ })).not.toBeInTheDocument();
    expect(fakes.offers.findById.mock.calls[0]?.[0]).toBe('o1');
  });

  it('성공: h1이 상품명, 버튼 「예약하고 결제 6,000원」(수량 1)', async () => {
    renderDetail({ fakes: withDetail() });
    expect(
      await screen.findByRole('heading', { level: 1, name: '소금빵 세트' }),
    ).toBeInTheDocument();
    expect(await reserveButton()).toHaveAccessibleName('예약하고 결제 6,000원');
    expect(stepperValue()).toBe('1');
  });

  it('오류: 문구와 「다시 시도」, 누르면 다시 요청해 상세를 보인다', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findById
      .mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', ''))
      .mockResolvedValueOnce(makeOfferDetail());
    renderDetail({ fakes });
    expect(await screen.findByText(OFFER_DETAIL_LOAD_FAILED_MESSAGE)).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: '할인 상세' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /예약하고 결제/ })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: RETRY_LABEL }));
    expect(
      await screen.findByRole('heading', { level: 1, name: '소금빵 세트' }),
    ).toBeInTheDocument();
    expect(fakes.offers.findById).toHaveBeenCalledTimes(2);
  });

  it('404: 「할인을 찾을 수 없어요.」와 「홈으로」(/) 링크, 예약 버튼 없음', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findById.mockRejectedValue(new ApiError(404, 'OFFER_NOT_FOUND', ''));
    renderDetail({ fakes });
    expect(await screen.findByText(OFFER_NOT_FOUND_MESSAGE)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '홈으로' })).toHaveAttribute('href', '/');
    expect(screen.queryByRole('button', { name: /예약하고 결제/ })).not.toBeInTheDocument();
  });

  it.each<[string, unknown, string]>([
    ["state.from = '/?sort=price'", { from: '/?sort=price' }, '/?sort=price'],
    ['state 없음', undefined, '/'],
    ["state.from = '//evil.com'", { from: '//evil.com' }, '/'],
  ])('← 링크: %s → %s', async (_name, state, href) => {
    renderDetail({ fakes: withDetail(), entry: { pathname: '/offers/o1', state } });
    await screen.findByRole('heading', { level: 1, name: '소금빵 세트' });
    expect(screen.getByRole('link', { name: BACK_LABEL })).toHaveAttribute('href', href);
  });

  it('품절: 예약 버튼 비활성, 사유 「품절됐어요.」', async () => {
    renderDetail({
      fakes: withDetail(makeOfferDetail({}, { remainingStock: 0, isSoldOut: true })),
    });
    expect(await reserveButton()).toBeDisabled();
    // 사유는 예약 패널 한 곳에만(본문 중복 없음)
    expect(screen.getAllByText(unavailableMessage('soldOut'))).toHaveLength(1);
  });

  it('비로그인: 수량 2로 올려 예약하면 /login, state { from: /offers/o1?qty=2, entry: reservation }', async () => {
    const { router } = renderDetail({ fakes: withDetail() });
    await reserveButton();
    await userEvent.click(screen.getByRole('button', { name: '+' }));
    await userEvent.click(await reserveButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/offers/o1?qty=2', entry: 'reservation' });
  });

  it('로그인 상태로 /offers/o1?qty=2 진입 → 스테퍼 2, 「예약하고 결제 12,000원」', async () => {
    renderDetail({
      fakes: withDetail(makeOfferDetail(), signedInFakes(customerUser)),
      entry: '/offers/o1?qty=2',
    });
    expect(await screen.findByRole('button', { name: '예약하고 결제 12,000원' })).toBeEnabled();
    expect(stepperValue()).toBe('2');
  });

  it('?qty=9, 남은 재고 3 → 스테퍼 3(패널이 자름)', async () => {
    renderDetail({
      fakes: withDetail(makeOfferDetail(), signedInFakes(customerUser)),
      entry: '/offers/o1?qty=9',
    });
    expect(await screen.findByRole('button', { name: '예약하고 결제 18,000원' })).toBeEnabled();
    expect(stepperValue()).toBe('3');
  });

  it('로그인 + 예약 성공(201, id r1) → /checkout/r1', async () => {
    const { router, fakes } = renderDetail({
      fakes: withDetail(makeOfferDetail(), signedInFakes(customerUser)),
    });
    fakes.reservations.create.mockResolvedValue({
      id: 'r1',
      offerId: 'o1',
      quantity: 1,
      unitPrice: 6000,
      totalPrice: 6000,
      status: 'PENDING_PAYMENT',
      createdAt: NOW,
      storeName: '망원베이커리',
      productName: '소금빵 세트',
    });
    const button = await reserveButton();
    await waitFor(() => expect(button).toBeEnabled());
    await userEvent.click(button);
    await waitFor(() => expect(router.state.location.pathname).toBe('/checkout/r1'));
    expect(fakes.reservations.create.mock.calls[0]?.[0]).toEqual({ offerId: 'o1', quantity: 1 });
  });

  it('A1 왕복: 비로그인 예약(수량 2) → A1 안내 → 로그인 → /offers/o1?qty=2, 스테퍼 2(자동 예약 안 함)', async () => {
    const fakes = withDetail();
    fakes.auth.findMe.mockResolvedValue(customerUser);
    const { router } = renderDetail({ fakes });
    await reserveButton();
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: '+' }));
    await user.click(await reserveButton());
    expect(await screen.findByText('예약을 이어가려면 로그인하세요.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('이메일'), 'customer@test.com');
    await user.type(screen.getByLabelText('비밀번호'), 'pw');
    await user.click(screen.getByRole('button', { name: '로그인' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/offers/o1'));
    expect(router.state.location.search).toBe('?qty=2');
    expect(await screen.findByRole('button', { name: '예약하고 결제 12,000원' })).toBeEnabled();
    expect(stepperValue()).toBe('2');
  });
});

describe('OfferDetailPage (C2) 시계', () => {
  afterEach(() => vi.useRealTimers());

  it('시계가 30초 지나 salesEnd를 넘기면 버튼 비활성 + 「판매가 종료됐어요.」', async () => {
    vi.useFakeTimers({
      now: NOW,
      toFake: ['Date', 'setInterval', 'clearInterval'],
      shouldAdvanceTime: true,
    });
    const detail = makeOfferDetail({}, { salesEnd: new Date(NOW.getTime() + 20_000) });
    renderDetail({ fakes: withDetail(detail) });
    const button = await reserveButton();
    expect(button).toBeEnabled();
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    await waitFor(() => expect(button).toBeDisabled());
    // 사유는 예약 패널 한 곳에만(본문 중복 없음)
    expect(screen.getAllByText(unavailableMessage('ended'))).toHaveLength(1);
  });
});
