import { render, screen } from '@testing-library/react';
import { App } from '@/app/App';
import { createContainer } from '@/app/container';
import { DepsProvider } from '@/shared/lib/DepsProvider';

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('루트 경로에서 홈(C1)을 보여 준다', () => {
    render(
      <DepsProvider container={createContainer()}>
        <App />
      </DepsProvider>,
    );
    expect(screen.getByText('마감직전')).toBeInTheDocument();
  });
});
