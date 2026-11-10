import { render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router';
import { routes } from '@/app/router/routes';
import { Container } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(
    <DepsProvider container={new Container([])}>
      <RouterProvider router={router} />
    </DepsProvider>,
  );
  return router;
}

describe('routes', () => {
  it('/owner는 /owner/today로 이동한다', () => {
    const router = renderAt('/owner');
    expect(router.state.location.pathname).toBe('/owner/today');
  });

  it.each([
    ['/owner/today', 'O1 오늘'],
    ['/owner/offers', 'O2 할인'],
    ['/owner/store', 'O4 매장'],
  ])('%s: 제목 「%s」과 TabBar·TopNav 링크가 있다', (path, title) => {
    renderAt(path);
    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(2);
  });

  it.each([
    ['/owner/offers/new', 'O3 할인 등록'],
    ['/owner/products/new', 'O6 상품 등록'],
    ['/owner/products/p1', 'O11 상품 수정'],
  ])('%s: 제목 「%s」이 있고 TabBar는 없다(TopNav만)', (path, title) => {
    renderAt(path);
    expect(screen.getByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(1);
  });

  it('/owner/products/p1은 productId를 표시한다', () => {
    renderAt('/owner/products/p1');
    expect(screen.getByText(/p1/)).toBeInTheDocument();
  });

  it('/login은 셸 없이 로그인 자리를 그린다', () => {
    renderAt('/login');
    expect(screen.queryAllByRole('link', { name: '오늘' })).toHaveLength(0);
    expect(document.querySelector('a[href="/owner/today"]')).toBeNull();
    expect(screen.getByRole('heading')).toBeInTheDocument();
  });

  it('/는 「마감 직전」을 보여 준다', () => {
    renderAt('/');
    expect(screen.getByRole('heading', { name: '마감 직전' })).toBeInTheDocument();
  });

  it.each(['/nope', '/owner/nope'])('%s는 /로 이동한다', (path) => {
    const router = renderAt(path);
    expect(router.state.location.pathname).toBe('/');
  });
});
