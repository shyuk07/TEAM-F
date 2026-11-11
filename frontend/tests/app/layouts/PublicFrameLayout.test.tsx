import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { PublicFrameLayout } from '@/app/layouts/PublicFrameLayout';

function renderFrame() {
  const router = createMemoryRouter(
    [
      {
        element: <PublicFrameLayout />,
        children: [{ path: '/x', element: <div className="app">내용</div> }],
      },
    ],
    { initialEntries: ['/x'] },
  );
  return render(<RouterProvider router={router} />);
}

describe('PublicFrameLayout', () => {
  it('자식 라우트 내용이 customer 프레임 안에 렌더된다', () => {
    renderFrame();
    const frame = document.querySelector('[data-shell="customer"]');
    expect(frame).not.toBeNull();
    expect(frame).toContainElement(screen.getByText('내용'));
  });

  it('프레임 직계 .app은 자식 라우트가 그린 하나뿐이다', () => {
    renderFrame();
    expect(document.querySelectorAll('[data-shell="customer"] > .app')).toHaveLength(1);
  });

  it('세션 가드 없이 내용이 보이고 TabBar는 없다', () => {
    renderFrame();
    expect(screen.getByText('내용')).toBeInTheDocument();
    expect(document.querySelector('.tabs')).toBeNull();
  });
});
