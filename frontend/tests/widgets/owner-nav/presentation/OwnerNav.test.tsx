import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import { OwnerAccountButton, OwnerTabBar, OwnerTopNav } from '@/widgets/owner-nav';

function renderAt(path: string, ui: React.ReactNode) {
  return render(<MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>);
}

function Pathname() {
  return <output data-testid="path">{useLocation().pathname}</output>;
}

describe.each([
  ['OwnerTabBar', OwnerTabBar],
  ['OwnerTopNav', OwnerTopNav],
])('%s', (_name, Nav) => {
  it('오늘·할인·매장 링크 3개가 ROUTES 경로를 가리킨다', () => {
    renderAt('/owner/offers', <Nav />);
    const links = screen.getAllByRole('link');
    expect(links.map((l) => l.textContent)).toEqual(['오늘', '할인', '매장']);
    expect(screen.getByRole('link', { name: '오늘' })).toHaveAttribute('href', ROUTES.ownerToday);
    expect(screen.getByRole('link', { name: '할인' })).toHaveAttribute('href', ROUTES.ownerOffers);
    expect(screen.getByRole('link', { name: '매장' })).toHaveAttribute('href', ROUTES.ownerStore);
  });

  it('현재 항목에만 aria-current="page"가 있다', () => {
    renderAt('/owner/offers', <Nav />);
    expect(screen.getByRole('link', { name: '할인' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: '오늘' })).not.toHaveAttribute('aria-current');
    expect(screen.getByRole('link', { name: '매장' })).not.toHaveAttribute('aria-current');
  });

  it('/login에서는 어느 항목도 활성이 아니다', () => {
    renderAt('/login', <Nav />);
    for (const link of screen.getAllByRole('link')) {
      expect(link).not.toHaveAttribute('aria-current');
    }
  });
});

describe('OwnerTabBar 하위 화면', () => {
  it('/owner/products/p1에서 「매장」이 활성이다', () => {
    renderAt('/owner/products/p1', <OwnerTabBar />);
    expect(screen.getByRole('link', { name: '매장' })).toHaveAttribute('aria-current', 'page');
  });
});

describe('OwnerTopNav 하위 화면', () => {
  it('/owner/offers/new에서 「할인」이 활성이다', () => {
    renderAt('/owner/offers/new', <OwnerTopNav />);
    const nav = screen.getAllByRole('link');
    const active = nav.filter((l) => l.getAttribute('aria-current') === 'page');
    expect(active).toHaveLength(1);
    expect(active[0]).toHaveTextContent('할인');
  });
});

describe('OwnerAccountButton', () => {
  it('접근 이름이 「계정」인 button이고 클릭해도 URL이 바뀌지 않는다', async () => {
    renderAt(
      '/owner/store',
      <>
        <OwnerAccountButton />
        <Pathname />
      </>,
    );
    const button = screen.getByRole('button', { name: '계정' });
    await userEvent.click(button);
    expect(screen.getByTestId('path')).toHaveTextContent('/owner/store');
  });
});
