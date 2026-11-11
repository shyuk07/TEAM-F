import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ProductEditPage } from '@/pages/product-edit';
import { ApiError } from '@/shared/api/error';
import { FakeProductRepository } from '../../entities/product/fakes/fakeProductRepository.fake';
import { breadProduct } from '../../entities/product/fakes/products';
import { ownerUser } from '../../features/auth/fakes/users';
import { FakeProductCommands } from '../../features/products/fakes/fakeProductCommands.fake';
import { signedInFakes } from '../../support/authFakes';
import { renderWithOwnerStore } from '../../support/renderWithOwnerStore';

function renderPage(
  opts: { products?: FakeProductRepository; productCommands?: FakeProductCommands } = {},
) {
  return renderWithOwnerStore(<ProductEditPage />, {
    initialEntries: ['/owner/products/p1'],
    routePath: '/owner/products/:productId',
    fakes: signedInFakes(ownerUser),
    ...opts,
  });
}

describe('pages/product-edit ProductEditPage', () => {
  it('로딩 중에는 aria-busy 영역과 뼈대가 보인다', () => {
    const products = new FakeProductRepository();
    products.findById.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage({ products });
    expect(container.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(container.querySelector('.card[aria-hidden="true"]')).not.toBeNull();
  });

  it('성공하면 제목 「상품 수정」과 채워진 폼이 보인다', async () => {
    renderPage();
    expect(await screen.findByDisplayValue('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.getByText('상품 수정', { selector: '.bar .t' })).toBeInTheDocument();
  });

  it.each([
    [404, 'NOT_FOUND'],
    [403, 'FORBIDDEN'],
  ])('%i %s → 「상품을 찾을 수 없어요.」와 「매장으로」 링크', async (status, code) => {
    const products = new FakeProductRepository();
    products.findById.mockRejectedValue(new ApiError(status, code, 'x'));
    renderPage({ products });
    expect(await screen.findByText('상품을 찾을 수 없어요.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '매장으로' })).toHaveAttribute('href', '/owner/store');
  });

  it('500이면 불러오기 오류와 「다시 시도」, 누르면 findById가 다시 불린다', async () => {
    const products = new FakeProductRepository();
    products.findById.mockRejectedValue(new ApiError(500, 'UNKNOWN', 'x'));
    renderPage({ products });
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '상품 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(products.findById).toHaveBeenCalledTimes(2);
  });

  it('저장 성공 → /owner/store로 이동한다', async () => {
    const productCommands = new FakeProductCommands();
    productCommands.update.mockResolvedValue({ ...breadProduct, name: '새 이름' });
    const { router } = renderPage({ productCommands });
    const user = userEvent.setup();
    const name = await screen.findByLabelText(/^상품명/);
    await user.clear(name);
    await user.type(name, '새 이름');
    await user.click(screen.getAllByRole('button', { name: '저장' })[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/store'));
  });

  it(':productId가 findById에 전달된다', async () => {
    const { products } = renderPage();
    await screen.findByDisplayValue('식빵 모둠 5종');
    expect(products.findById.mock.calls[0][0]).toBe('p1');
  });
});
