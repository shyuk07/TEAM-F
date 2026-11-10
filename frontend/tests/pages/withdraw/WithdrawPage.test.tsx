import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import { ApiError } from '@/shared/api/error';
import { signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { deferred } from '../../features/auth/fakes/deferred';
import { makePointPage, makePointLogs } from '../../features/auth/fakes/points';
import { customerUser } from '../../features/auth/fakes/users';

function withBalance(): AuthFakes {
  const fakes = signedInFakes(customerUser);
  fakes.account.findPoints.mockResolvedValue(
    makePointPage(makePointLogs(1), { balance: 1240, size: 1, total: 1 }),
  );
  return fakes;
}

function renderWithdraw(fakes: AuthFakes = withBalance()) {
  return renderRoutesWithAuth(routes, { initialEntries: ['/me/withdraw'], fakes });
}

const submitButton = () => screen.getByRole('button', { name: '탈퇴하기' });

describe('WithdrawPage (C7)', () => {
  it('제목 「회원 탈퇴」와 탈퇴 안내 상자(예약 임시 문구, 1,240P 소멸, 되돌릴 수 없어요.)', async () => {
    const fakes = withBalance();
    renderWithdraw(fakes);
    expect(await screen.findByRole('heading', { level: 1, name: '회원 탈퇴' })).toBeInTheDocument();
    expect(screen.getByText('탈퇴하면 이렇게 돼요')).toBeInTheDocument();
    expect(screen.getByText('진행 중 예약')).toBeInTheDocument();
    expect(screen.getByText('모두 취소·환불')).toBeInTheDocument();
    expect(screen.getByText('남은 포인트')).toBeInTheDocument();
    expect(await screen.findByText('1,240P 소멸')).toBeInTheDocument();
    expect(screen.getByText('되돌릴 수 없어요.')).toBeInTheDocument();
    expect(fakes.account.findPoints.mock.calls[0]?.[0]).toEqual({ page: 0, size: 1 });
  });

  it('「현재 비밀번호 *」는 password·current-password 칸이고 「탈퇴하기」는 처음에 비활성', async () => {
    renderWithdraw();
    const input = await screen.findByLabelText('현재 비밀번호 *');
    expect(input).toHaveAttribute('type', 'password');
    expect(input).toHaveAttribute('autocomplete', 'current-password');
    expect(submitButton()).toHaveAttribute('aria-disabled', 'true');
  });

  it('「취소」는 /me로 가는 링크', async () => {
    renderWithdraw();
    expect(await screen.findByRole('link', { name: '취소' })).toHaveAttribute('href', '/me');
  });

  it('제출하면 account.withdraw(pw)·session.clear 뒤 /로 간다', async () => {
    const fakes = withBalance();
    const { router } = renderWithdraw(fakes);
    await userEvent.type(await screen.findByLabelText('현재 비밀번호 *'), 'pw123456');
    await userEvent.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(fakes.account.withdraw.mock.calls[0]?.[0]).toBe('pw123456');
    expect(fakes.session.clear).toHaveBeenCalled();
  });

  it('CURRENT_PASSWORD_MISMATCH면 칸 아래 「비밀번호가 일치하지 않습니다.」, 입력은 유지', async () => {
    const fakes = withBalance();
    fakes.account.withdraw.mockRejectedValue(
      new ApiError(400, 'CURRENT_PASSWORD_MISMATCH', '현재 비밀번호가 올바르지 않습니다.'),
    );
    const { router } = renderWithdraw(fakes);
    const input = await screen.findByLabelText('현재 비밀번호 *');
    await userEvent.type(input, 'wrong-pw');
    await userEvent.click(submitButton());
    expect(await screen.findByText('비밀번호가 일치하지 않습니다.')).toBeInTheDocument();
    expect(screen.queryByText('현재 비밀번호가 올바르지 않습니다.')).not.toBeInTheDocument();
    expect(input).toHaveValue('wrong-pw');
    expect(router.state.location.pathname).toBe('/me/withdraw');
  });

  it('처리 중에는 「처리 중…」이고 연타해도 한 번만 요청한다', async () => {
    const fakes = withBalance();
    const d = deferred<void>();
    fakes.account.withdraw.mockReturnValue(d.promise);
    renderWithdraw(fakes);
    await userEvent.type(await screen.findByLabelText('현재 비밀번호 *'), 'pw123456');
    await userEvent.click(submitButton());
    const pending = await screen.findByRole('button', { name: '처리 중…' });
    expect(pending).toHaveAttribute('aria-disabled', 'true');
    await userEvent.click(pending);
    expect(fakes.account.withdraw).toHaveBeenCalledTimes(1);
  });
});
