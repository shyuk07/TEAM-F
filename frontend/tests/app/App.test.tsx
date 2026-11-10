import { render, screen } from '@testing-library/react';
import { App } from '@/app/App';
import { createContainer } from '@/app/container';
import { DepsProvider } from '@/shared/lib/DepsProvider';

describe('App', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  // D-27: 홈 로고는 와이어프레임 문구 「마감직전」(기존 자리 page 「마감 직전」에서 교체)
  it('루트 경로에서 홈(C1) 로고 「마감직전」을 보여 준다', async () => {
    render(
      <DepsProvider container={createContainer()}>
        <App />
      </DepsProvider>,
    );
    expect(await screen.findByRole('heading', { name: '마감직전' })).toBeInTheDocument();
  });
});
