import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { ProductNewPage } from '@/pages/product-new';
import { createdProduct } from '../../entities/product/fakes/products';
import { ownerUser } from '../../features/auth/fakes/users';
import { signedInFakes } from '../../support/authFakes';
import { renderWithOwnerStore } from '../../support/renderWithOwnerStore';

function renderPage() {
  return renderWithOwnerStore(<ProductNewPage />, {
    initialEntries: ['/owner/products/new'],
    fakes: signedInFakes(ownerUser),
  });
}

async function fillAndSubmit(name: string) {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText(/^상품명/), '식빵');
  await user.type(screen.getByLabelText(/^정상 가격/), '12000');
  await user.click(screen.getAllByRole('button', { name })[0]);
}

describe('pages/product-new ProductNewPage', () => {
  it('AppBar 제목 「상품 등록」과 「뒤로」 링크(→ /owner/store)가 있다', async () => {
    renderPage();
    expect(await screen.findByText('상품 등록', { selector: '.bar .t' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/owner/store');
  });

  it('「등록만」 성공 → /owner/store로 이동하고 상점 id로 create를 부른다', async () => {
    const { router, productCommands } = renderPage();
    await fillAndSubmit('등록만');
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/store'));
    expect(productCommands.create.mock.calls[0][0]).toBe('st-1');
  });

  it('「등록하고 할인 만들기」 성공 → /owner/offers/new?productId=<새 상품 id>로 이동한다', async () => {
    const { router } = renderPage();
    await fillAndSubmit('등록하고 할인 만들기');
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/offers/new'));
    expect(router.state.location.search).toBe(`?productId=${createdProduct.id}`);
  });
});
