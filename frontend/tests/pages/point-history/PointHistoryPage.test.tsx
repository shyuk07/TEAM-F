import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import { signedInFakes, type AuthFakes } from '../../support/authFakes';
import { at } from '../../support/clock';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { makePointLog, makePointLogs, makePointPage } from '../../features/auth/fakes/points';
import { customerUser } from '../../features/auth/fakes/users';

function renderPoints(fakes: AuthFakes) {
  return renderRoutesWithAuth(routes, { initialEntries: ['/me/points'], fakes });
}

function withLogs(): AuthFakes {
  const fakes = signedInFakes(customerUser);
  fakes.account.findPoints.mockResolvedValue(
    makePointPage([
      makePointLog(),
      makePointLog({
        id: 'pl0',
        amount: -500,
        type: 'USE',
        balanceAfter: null,
        createdAt: at(6, 12, 0),
      }),
    ]),
  );
  return fakes;
}

describe('PointHistoryPage (C11)', () => {
  it('제목 「포인트」, ← 는 /me, 탭 바 없음', async () => {
    renderPoints(withLogs());
    expect(await screen.findByRole('heading', { level: 1, name: '포인트' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/me');
    expect(screen.queryByRole('navigation', { name: '고객 메뉴' })).not.toBeInTheDocument();
  });

  it('「보유 포인트」 1,240P와 적립 안내', async () => {
    const fakes = withLogs();
    renderPoints(fakes);
    expect(await screen.findByText('보유 포인트')).toBeInTheDocument();
    expect(await screen.findByText('1,240P')).toBeInTheDocument();
    expect(screen.getByText('결제 금액의 1% 적립 · 100P 단위로 사용')).toBeInTheDocument();
    expect(fakes.account.findPoints.mock.calls[0]?.[0]).toEqual({ page: 0, size: 20 });
  });

  it('행: 「11/07 18:02 · 잔액 1,240P」, 잔액 없는 옛 내역은 「· 잔액」 생략', async () => {
    renderPoints(withLogs());
    expect(await screen.findByText('11/07 18:02 · 잔액 1,240P')).toBeInTheDocument();
    expect(screen.getByText('11/06 12:00')).toBeInTheDocument();
    expect(screen.getByText('+115P')).toBeInTheDocument();
    expect(screen.getByText('−500P')).toBeInTheDocument();
  });

  it('total 25면 「더 보기」로 page 1을 받아 25행, 끝나면 버튼 없음', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.findPoints.mockResolvedValueOnce(makePointPage(makePointLogs(20), { total: 25 }));
    fakes.account.findPoints.mockResolvedValueOnce(
      makePointPage(makePointLogs(5, 21), { page: 1, total: 25 }),
    );
    renderPoints(fakes);
    await waitFor(() => expect(screen.getAllByText('적립')).toHaveLength(20));
    await userEvent.click(screen.getByRole('button', { name: '더 보기' }));
    await waitFor(() => expect(screen.getAllByText('적립')).toHaveLength(25));
    expect(fakes.account.findPoints.mock.calls[1]?.[0]).toEqual({ page: 1, size: 20 });
    expect(screen.queryByRole('button', { name: '더 보기' })).not.toBeInTheDocument();
  });

  it('0건이면 「포인트 내역이 없어요」와 「할인 보러 가기」(/)', async () => {
    renderPoints(signedInFakes(customerUser));
    expect(await screen.findByText('포인트 내역이 없어요')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '할인 보러 가기' })).toHaveAttribute('href', '/');
  });
});
