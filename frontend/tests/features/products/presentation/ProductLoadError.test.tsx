import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { ProductLoadError } from '@/features/products';
import type { ProductLoadFailure } from '@/features/products';

function renderError(failure: ProductLoadFailure) {
  const onRetry = vi.fn();
  const router = createMemoryRouter([
    { path: '*', element: <ProductLoadError failure={failure} onRetry={onRetry} /> },
  ]);
  render(<RouterProvider router={router} />);
  return { onRetry };
}

// C1(D-35): 구분과 문구는 useProduct가 만들고, 이 컴포넌트는 그리기만 한다
describe('features/products presentation ProductLoadError', () => {
  it('notFound: alert에 문구와 「매장으로」 링크, 「다시 시도」는 없다', () => {
    renderError({ kind: 'notFound', message: '상품을 찾을 수 없어요.' });
    expect(screen.getByRole('alert')).toHaveTextContent('상품을 찾을 수 없어요.');
    expect(screen.getByRole('link', { name: '매장으로' })).toHaveAttribute('href', '/owner/store');
    expect(screen.queryByRole('button', { name: '다시 시도' })).toBeNull();
  });

  it('loadFailed: 문구와 「다시 시도」 버튼, 누르면 onRetry 1회, 「매장으로」는 없다', async () => {
    const { onRetry } = renderError({ kind: 'loadFailed', message: '불러오지 못했어요.' });
    expect(screen.getByRole('alert')).toHaveTextContent('불러오지 못했어요.');
    expect(screen.queryByRole('link', { name: '매장으로' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it('message는 전달받은 값을 그대로 그린다(컴포넌트가 문구를 새로 만들지 않음)', () => {
    renderError({ kind: 'notFound', message: '테스트용 임의 문구' });
    expect(screen.getByRole('alert')).toHaveTextContent('테스트용 임의 문구');
    expect(screen.queryByText('상품을 찾을 수 없어요.')).toBeNull();
  });
});
