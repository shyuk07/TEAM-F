import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ProductList } from '@/features/products';
import { ApiError } from '@/shared/api/error';
import { FakeProductRepository } from '../../../entities/product/fakes/fakeProductRepository.fake';
import { breadProduct, noCategoryProduct } from '../../../entities/product/fakes/products';
import { renderProducts } from '../fakes/renderProducts';

const rowLinks = () =>
  screen
    .queryAllByRole('link')
    .filter((a) => /^\/owner\/products\/(?!new$)/.test(a.getAttribute('href') ?? ''));

describe('features/products presentation ProductList', () => {
  it('로딩: 뼈대 3개가 보이고 상품 행·빈 상태는 없다', () => {
    const repo = new FakeProductRepository();
    repo.findByStore.mockReturnValue(new Promise(() => {}));
    const { container } = renderProducts(<ProductList storeId="s1" />, { repo });
    expect(container.querySelectorAll('.card[aria-hidden="true"]')).toHaveLength(3);
    expect(rowLinks()).toHaveLength(0);
    expect(screen.queryByText('아직 등록한 상품이 없어요')).toBeNull();
  });

  it('성공: 개수·행·보조 줄·상태 태그·링크가 그려진다', async () => {
    renderProducts(<ProductList storeId="s1" />);
    expect(await screen.findByText('상품 2개')).toBeInTheDocument();
    expect(rowLinks()).toHaveLength(2);
    expect(screen.getByText('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.getByText('바게트')).toBeInTheDocument();
    expect(screen.getByText('빵 · 12,000원')).toBeInTheDocument();
    expect(screen.getByText('빵 · 4,000원')).toBeInTheDocument();
    expect(screen.getByText('노출')).toHaveClass('tag', 'ok');
    expect(screen.getByText('숨김')).toHaveClass('tag', 'mute');
    expect(screen.getByRole('link', { name: /식빵 모둠 5종/ })).toHaveAttribute(
      'href',
      '/owner/products/p1',
    );
    expect(screen.getByRole('link', { name: /바게트/ })).toHaveAttribute(
      'href',
      '/owner/products/p2',
    );
    expect(screen.getByRole('link', { name: '+ 상품 등록' })).toHaveAttribute(
      'href',
      '/owner/products/new',
    );
  });

  it('카테고리 없는 상품의 보조 줄은 「12,000원」', async () => {
    const repo = new FakeProductRepository();
    repo.findByStore.mockResolvedValue({
      items: [noCategoryProduct],
      page: 1,
      size: 100,
      total: 1,
    });
    renderProducts(<ProductList storeId="s1" />, { repo });
    const row = await screen.findByRole('link', { name: /단팥빵/ });
    expect(within(row).getByText('12,000원')).toBeInTheDocument();
  });

  it('items가 total보다 적으면 개수는 total, 행은 items 수', async () => {
    const repo = new FakeProductRepository();
    const items = Array.from({ length: 100 }, (_, i) => ({
      ...breadProduct,
      id: `p${i + 1}`,
      name: `상품${i + 1}`,
    }));
    repo.findByStore.mockResolvedValue({ items, page: 1, size: 100, total: 130 });
    renderProducts(<ProductList storeId="s1" />, { repo });
    expect(await screen.findByText('상품 130개')).toBeInTheDocument();
    expect(rowLinks()).toHaveLength(100);
  });

  it('빈(total 0): 안내 문구와 「상품 등록」 링크가 있고 행은 없다', async () => {
    const repo = new FakeProductRepository();
    repo.findByStore.mockResolvedValue({ items: [], page: 1, size: 100, total: 0 });
    renderProducts(<ProductList storeId="s1" />, { repo });
    expect(await screen.findByText('아직 등록한 상품이 없어요')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '상품 등록' })).toHaveAttribute(
      'href',
      '/owner/products/new',
    );
    expect(rowLinks()).toHaveLength(0);
  });

  it('오류: alert에 불러오기 문구, 「다시 시도」를 누르면 findByStore가 다시 불린다', async () => {
    const repo = new FakeProductRepository();
    repo.findByStore.mockRejectedValue(new ApiError(500, 'UNKNOWN', 'x'));
    renderProducts(<ProductList storeId="s1" />, { repo });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(repo.findByStore).toHaveBeenCalledTimes(2);
  });

  it('findByStore가 storeId로 호출된다', async () => {
    const { repo } = renderProducts(<ProductList storeId="store-77" />);
    await screen.findByText('상품 2개');
    expect(repo.findByStore.mock.calls[0][0]).toBe('store-77');
  });
});
