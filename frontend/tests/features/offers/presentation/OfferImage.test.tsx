import { fireEvent, render, screen } from '@testing-library/react';
import { OfferImage } from '@/features/offers';
import { PRODUCT_IMAGE_PLACEHOLDER } from '@/features/offers/domain/offerMessages';

describe('OfferImage', () => {
  it('urls가 있으면 첫 장을 img(alt=상품명)로 보인다', () => {
    render(<OfferImage urls={['https://x/a.jpg', 'https://x/b.jpg']} alt="소금빵 세트" />);
    const img = screen.getByRole('img', { name: '소금빵 세트' });
    expect(img).toHaveAttribute('src', 'https://x/a.jpg');
    expect(screen.getAllByRole('img')).toHaveLength(1);
  });

  it('urls가 빈 배열이면 .ph 「상품 이미지」, img 없음', () => {
    render(<OfferImage urls={[]} alt="소금빵 세트" />);
    const ph = screen.getByText(PRODUCT_IMAGE_PLACEHOLDER);
    expect(ph).toHaveClass('ph');
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('img가 로드에 실패하면 .ph로 바뀐다', () => {
    render(<OfferImage urls={['https://x/broken.jpg']} alt="소금빵 세트" />);
    fireEvent.error(screen.getByRole('img', { name: '소금빵 세트' }));
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    expect(screen.getByText(PRODUCT_IMAGE_PLACEHOLDER)).toHaveClass('ph');
  });
});
