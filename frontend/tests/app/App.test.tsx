import { render, screen } from '@testing-library/react';
import { App } from '@/app/App';

describe('App', () => {
  it('루트 경로에서 자리 표시 화면을 보여 준다', () => {
    render(<App />);
    expect(screen.getByRole('heading', { name: '마감 직전' })).toBeInTheDocument();
  });
});
