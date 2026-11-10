import { render, screen } from '@testing-library/react';
import { OfferCard } from '@/features/offers';
import {
  minutesFromNow,
  nearby,
  now,
  offerEnded,
  offerOnSale,
  offerScheduled,
  offerSoldOut,
} from '../fakes/offers';

describe('OfferCard', () => {
  it('판매 중: 상점·거리, 상품명, 할인율·가격·정가(취소선), 픽업, 마감 라벨, 남은 수량', () => {
    render(<OfferCard item={nearby(offerOnSale, 0.4)} now={now} />);
    expect(screen.getByText('망원베이커리 · 0.4km')).toBeInTheDocument();
    expect(screen.getByText('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.getByText('50%')).toBeInTheDocument();
    expect(screen.getByText('6,000원')).toBeInTheDocument();
    expect(screen.getByText('12,000').tagName).toBe('S');
    expect(screen.getByText('오늘 18:00–20:00')).toBeInTheDocument();
    expect(screen.getByText(/^픽업/)).toBeInTheDocument();
    expect(screen.getByText('판매 마감 42분 전')).toBeInTheDocument();
    expect(screen.getByText('남은 3개')).toBeInTheDocument();
  });

  it('거리가 null이면 「·」과 「km」가 없다', () => {
    const { container } = render(<OfferCard item={nearby(offerOnSale, null)} now={now} />);
    expect(screen.getByText('망원베이커리')).toBeInTheDocument();
    expect(container.textContent).not.toContain('·');
    expect(container.textContent).not.toContain('km');
  });

  it('품절: 태그 「품절」, 마감 라벨·남은 수량이 없다', () => {
    render(<OfferCard item={nearby(offerSoldOut)} now={now} />);
    const tag = screen.getByText('품절');
    expect(tag).toHaveClass('tag', 'mute');
    expect(screen.queryByText(/판매 마감/)).not.toBeInTheDocument();
    expect(screen.queryByText(/남은/)).not.toBeInTheDocument();
  });

  it('판매 종료: 태그 「판매 종료」, 마감 라벨·남은 수량이 없다', () => {
    render(<OfferCard item={nearby(offerEnded)} now={now} />);
    expect(screen.getByText('판매 종료')).toHaveClass('tag', 'mute');
    expect(screen.queryByText(/판매 마감/)).not.toBeInTheDocument();
    expect(screen.queryByText(/남은/)).not.toBeInTheDocument();
  });

  it('판매 예정: 태그 「판매 예정」(mute 아님)', () => {
    render(<OfferCard item={nearby(offerScheduled)} now={now} />);
    const tag = screen.getByText('판매 예정');
    expect(tag).toHaveClass('tag');
    expect(tag).not.toHaveClass('mute');
    expect(screen.queryByText(/판매 마감/)).not.toBeInTheDocument();
  });

  it('now가 바뀌면 마감 라벨이 바뀐다', () => {
    const item = nearby(offerOnSale);
    const { rerender } = render(<OfferCard item={item} now={now} />);
    expect(screen.getByText('판매 마감 42분 전')).toBeInTheDocument();
    rerender(<OfferCard item={item} now={minutesFromNow(1)} />);
    expect(screen.getByText('판매 마감 41분 전')).toBeInTheDocument();
  });

  it('링크도 버튼도 아니다(카드는 이동하지 않는다)', () => {
    render(<OfferCard item={nearby(offerOnSale)} now={now} />);
    expect(screen.getByText('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.queryAllByRole('link')).toHaveLength(0);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });
});
