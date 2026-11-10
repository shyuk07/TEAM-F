import { render, screen } from '@testing-library/react';
import { RouterProvider, createMemoryRouter, type RouteObject } from 'react-router';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { OwnerTopNav } from '@/widgets/owner-nav';

function Page() {
  return (
    <>
      <p>본문</p>
      <OwnerTopNav />
    </>
  );
}

function renderLayout(tabBar: boolean) {
  const testRoutes: RouteObject[] = [
    {
      element: <OwnerLayout />,
      children: [
        { path: '/owner/today', element: <Page />, handle: tabBar ? { tabBar: true } : {} },
      ],
    },
  ];
  const router = createMemoryRouter(testRoutes, { initialEntries: ['/owner/today'] });
  return render(<RouterProvider router={router} />);
}

describe('OwnerLayout', () => {
  it('handle.tabBar가 true면 TabBar가 Outlet 내용 뒤에 온다', () => {
    renderLayout(true);
    const tabs = document.querySelector('.tabs');
    expect(tabs).not.toBeNull();
    const nav = screen.getByText('본문').parentElement;
    expect(nav?.lastElementChild).toBe(tabs);
  });

  it('handle.tabBar가 없으면 TabBar가 없다', () => {
    renderLayout(false);
    expect(document.querySelector('.tabs')).toBeNull();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(1);
  });

  it('프레임 요소에 app 클래스가 있다', () => {
    const { container } = renderLayout(true);
    expect(container.firstElementChild).toHaveClass('app');
  });

  it('탭 화면에서 「오늘」 링크가 TabBar와 TopNav 두 곳에 있다', () => {
    renderLayout(true);
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(2);
  });
});
