import { render, screen } from '@testing-library/react';
import { OfferDetailBody, unavailableMessage, type OfferDetail } from '@/features/offers';
import {
  CANCEL_DEADLINE_LABEL,
  MAX_PER_RESERVATION_TEXT,
  PICKUP_TIME_LABEL,
} from '@/features/offers/domain/offerMessages';
import { at } from '../../../support/clock';
import { CANCEL_POLICY_TEXT, NOTICE, PICKUP_ADDRESS, makeOfferDetail } from '../fakes/offerDetails';

// 기본 detail: 판매 마감 오늘 18:00, 픽업 오늘 18:00–20:00, 취소 가능 오늘 17:00, 남은 3개.
// 표기는 로컬 벽시계 기준이라 로컬 생성자(at)로 시각을 만든다.
const NOW = at(10, 17, 30);

function renderBody(detail: OfferDetail = makeOfferDetail()) {
  return render(<OfferDetailBody detail={detail} now={NOW} />);
}

describe('OfferDetailBody', () => {
  it('상점명·주소, 할인율·할인가·정가(취소선)', () => {
    renderBody();
    expect(screen.getByText(`망원베이커리 · ${PICKUP_ADDRESS}`)).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('6,000원')).toBeInTheDocument();
    expect(screen.getByText('12,000').tagName).toBe('S');
  });

  it('판매 가능이면 「판매 마감 30분 전」과 「남은 3개」', () => {
    renderBody();
    expect(screen.getByText('판매 마감 30분 전')).toBeInTheDocument();
    expect(screen.getByText('남은 3개')).toBeInTheDocument();
  });

  // 사유 문구는 예약 패널 한 곳에만 보인다(오케스트레이터 결정, 리뷰 REQUEST_CHANGES).
  it('품절이면 카운트다운·남은 수량이 없고, 본문에는 사유 문구도 없다', () => {
    renderBody(makeOfferDetail({}, { remainingStock: 0, isSoldOut: true }));
    expect(screen.getByText('6,000원')).toBeInTheDocument();
    expect(screen.queryByText(unavailableMessage('soldOut'))).not.toBeInTheDocument();
    expect(screen.queryByText(/판매 마감/)).not.toBeInTheDocument();
    expect(screen.queryByText(/남은 \d+개/)).not.toBeInTheDocument();
  });

  it('「픽업 시간」 오늘 18:00–20:00, 「취소 가능」 오늘 17:00까지 (이후 취소 불가)', () => {
    renderBody();
    expect(screen.getByText(PICKUP_TIME_LABEL)).toBeInTheDocument();
    expect(screen.getByText('오늘 18:00–20:00')).toBeInTheDocument();
    expect(screen.getByText(CANCEL_DEADLINE_LABEL)).toBeInTheDocument();
    expect(screen.getByText('오늘 17:00까지 (이후 취소 불가)')).toBeInTheDocument();
  });

  it('서버 notice와 「한 번에 최대 5개까지 예약할 수 있어요.」', () => {
    renderBody();
    expect(screen.getByText(NOTICE)).toBeInTheDocument();
    expect(screen.getByText(MAX_PER_RESERVATION_TEXT)).toBeInTheDocument();
  });

  it('description이 있으면 보이고, null이면 없다', () => {
    const { unmount } = renderBody(makeOfferDetail({ description: '버터 소금빵 4개' }));
    expect(screen.getByText('버터 소금빵 4개')).toBeInTheDocument();
    unmount();
    renderBody(makeOfferDetail({ description: null }));
    expect(screen.getByText(NOTICE)).toBeInTheDocument();
    expect(screen.queryByText('버터 소금빵 4개')).not.toBeInTheDocument();
  });

  it('서버 취소 정책 문구(cancelPolicyText)는 보이지 않는다', () => {
    renderBody();
    expect(screen.getByText(NOTICE)).toBeInTheDocument();
    expect(screen.queryByText(CANCEL_POLICY_TEXT)).not.toBeInTheDocument();
  });
});
