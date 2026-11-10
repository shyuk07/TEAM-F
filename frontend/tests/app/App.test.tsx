import { render, screen } from '@testing-library/react';
import { App } from '@/app/App';
import { createContainer } from '@/app/container';
import { DepsProvider } from '@/shared/lib/DepsProvider';

describe('App', () => {
  it('루트 경로에서 자리 표시 화면을 보여 준다', () => {
    render(
      <DepsProvider container={createContainer()}>
        <App />
      </DepsProvider>,
    );
    expect(screen.getByRole('heading', { name: '마감 직전' })).toBeInTheDocument();
  });
});
