import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { OfferCard } from '@/features/offers';
import { fixNow, restoreNow } from '../../../support/clock';
import { makeNearby } from '../fakes/offers';

function renderCard(imageUrls: string[]) {
  const { container } = render(
    <MemoryRouter>
      <OfferCard item={makeNearby({}, null, imageUrls)} now={new Date()} />
    </MemoryRouter>,
  );
  const link = screen.getByRole('link', { name: /소금빵 세트/ });
  return { container, link };
}

describe('OfferCard 사진', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('imageUrls[0]이 있으면 사진 자리에 img.ph(src 첫 장, alt 빈 값, loading lazy)', () => {
    const { link } = renderCard(['https://x/a.jpg', 'https://x/b.jpg']);
    const imgs = link.querySelectorAll('img');
    expect(imgs).toHaveLength(1);
    const img = imgs[0]!;
    expect(img).toHaveClass('ph');
    expect(img).toHaveAttribute('src', 'https://x/a.jpg');
    expect(img).toHaveAttribute('alt', '');
    expect(img).toHaveAttribute('loading', 'lazy');
    expect(link.querySelector('div.ph')).toBeNull();
    expect(link).toHaveTextContent('망원베이커리');
    expect(link).toHaveTextContent('6,000원');
  });

  it('imageUrls가 비면 div.ph(aria-hidden), img 없음', () => {
    const { link } = renderCard([]);
    expect(link.querySelector('img')).toBeNull();
    expect(link.querySelector('div.ph')).toHaveAttribute('aria-hidden', 'true');
  });

  it('img 로드에 실패하면 div.ph(aria-hidden)로 바뀐다', () => {
    const { link } = renderCard(['https://x/a.jpg']);
    const img = link.querySelector('img');
    expect(img).not.toBeNull();
    fireEvent.error(img!);
    expect(link.querySelector('img')).toBeNull();
    expect(link.querySelector('div.ph')).toHaveAttribute('aria-hidden', 'true');
  });
});
