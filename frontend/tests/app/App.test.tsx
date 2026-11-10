import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { App } from '@/app/App';
import { createContainer } from '@/app/container';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { saveToken } from '@/shared/api/tokenStorage';

const jsonRes = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const meDto = {
  id: 'u-owner',
  email: 'owner@test.com',
  name: '망원베이커리',
  phone: '010-1111-2222',
  role: 'OWNER',
  status: 'APPROVED',
  users_point: 0,
  created_at: '2026-01-02T03:04:05Z',
};

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

  it('보호 요청이 401 TOKEN_REVOKED를 받으면 상점주가 /login( A1)으로 이동하고 토큰이 지워진다', async () => {
    const fetchMock = vi.fn((input: string | URL) => {
      const url = String(input);
      if (url.endsWith('/v1/users/me')) return Promise.resolve(jsonRes(meDto));
      return Promise.resolve(
        jsonRes({ success: false, error_code: 'TOKEN_REVOKED', message: '재로그인' }, 401),
      );
    });
    vi.stubGlobal('fetch', fetchMock);
    saveToken('tok-1');
    window.history.replaceState(null, '', '/owner/today');
    render(
      <DepsProvider container={createContainer()}>
        <App />
      </DepsProvider>,
    );
    await waitFor(() => expect(window.location.pathname).toBe('/login'));
    await screen.findByRole('heading', { name: '로그인' });
    expect(localStorage.getItem('lastcall.accessToken')).toBeNull();
    vi.unstubAllGlobals();
  });
});
