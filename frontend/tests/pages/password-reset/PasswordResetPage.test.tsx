import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { InitialEntry, RouteObject } from 'react-router';
import { PASSWORD_RESET_DONE_NOTICE } from '@/features/auth';
import { LoginPage } from '@/pages/login';
import { PasswordResetPage } from '@/pages/password-reset';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

const routes: RouteObject[] = [
  { path: '/password-reset', element: <PasswordResetPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <p>홈 화면</p> },
  { path: '/owner/today', element: <p>오늘 화면</p> },
];

function renderReset(opts: { fakes?: AuthFakes; entry?: InitialEntry } = {}) {
  return renderRoutesWithAuth(routes, {
    initialEntries: [opts.entry ?? '/password-reset'],
    fakes: opts.fakes ?? anonymousFakes(),
  });
}

async function ready() {
  await screen.findByRole('heading', { name: '비밀번호 재설정' });
  return userEvent.setup();
}

type User = ReturnType<typeof userEvent.setup>;

const emailInput = () => screen.getByLabelText('가입한 이메일');
const sendButton = () => screen.getByRole('button', { name: '코드 보내기' });
const confirmButtons = () => screen.getAllByRole('button', { name: '비밀번호 바꾸기' });

async function sendCode(user: User, email = 'a@b.c') {
  await user.type(emailInput(), email);
  await user.click(sendButton());
  return screen.findByLabelText('6자리 코드');
}

async function fillStep2(user: User, code = '123456', password = 'pw123456') {
  await user.type(screen.getByLabelText('6자리 코드'), code);
  await user.type(screen.getByLabelText('새 비밀번호 (8자 이상)'), password);
}

function expectAllDisabled(buttons: HTMLElement[], disabled: boolean) {
  for (const b of buttons) {
    if (disabled) expect(b).toHaveAttribute('aria-disabled', 'true');
    else expect(b).not.toHaveAttribute('aria-disabled', 'true');
  }
}

describe('PasswordResetPage (A3)', () => {
  it('제목 「비밀번호 재설정」과 /login으로 가는 「뒤로」 링크가 있다', async () => {
    renderReset();
    await ready();
    expect(screen.getByRole('heading', { level: 1, name: '비밀번호 재설정' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/login');
  });

  it('처음에는 1단계만 있고 「비밀번호 바꾸기」 두 벌이 비활성이다', async () => {
    renderReset();
    await ready();
    expect(screen.getByText('1단계 · 코드 받기')).toBeInTheDocument();
    expect(emailInput()).toBeInTheDocument();
    expect(sendButton()).toBeInTheDocument();
    expect(screen.getByText('가입된 이메일이면 6자리 코드를 보내요.')).toBeInTheDocument();
    expect(screen.queryByText('2단계 · 새 비밀번호')).not.toBeInTheDocument();
    const buttons = confirmButtons();
    expect(buttons).toHaveLength(2);
    expectAllDisabled(buttons, true);
  });

  it('이메일이 비어 있으면 「코드 보내기」가 비활성이다', async () => {
    renderReset();
    await ready();
    expect(sendButton()).toHaveAttribute('aria-disabled', 'true');
  });

  it('「코드 보내기」를 누르면 요청하고 2단계가 나타난다', async () => {
    const { fakes } = renderReset();
    const user = await ready();
    await sendCode(user);
    expect(fakes.account.requestPasswordReset.mock.calls[0]?.[0]).toBe('a@b.c');
    expect(screen.getByText('2단계 · 새 비밀번호')).toBeInTheDocument();
    expect(screen.getByLabelText('6자리 코드')).toBeInTheDocument();
    expect(screen.getByLabelText('새 비밀번호 (8자 이상)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '코드 다시 받기' })).toBeInTheDocument();
  });

  it('코드 칸은 in code 클래스, 숫자 입력, 최대 6자, one-time-code다', async () => {
    renderReset();
    const user = await ready();
    const code = await sendCode(user);
    expect(code).toHaveClass('in', 'code');
    expect(code).toHaveAttribute('inputmode', 'numeric');
    expect(code).toHaveAttribute('maxlength', '6');
    expect(code).toHaveAttribute('autocomplete', 'one-time-code');
  });

  it('코드 6자리와 8자 비밀번호면 활성이고 코드가 5자리면 비활성이다', async () => {
    renderReset();
    const user = await ready();
    await sendCode(user);
    await fillStep2(user);
    expectAllDisabled(confirmButtons(), false);
    await user.type(screen.getByLabelText('6자리 코드'), '{Backspace}');
    expectAllDisabled(confirmButtons(), true);
  });

  it('제출하면 확인을 요청하고 세션을 정리한 뒤 /login에서 완료 안내를 보인다', async () => {
    const { fakes, router } = renderReset();
    const user = await ready();
    await sendCode(user);
    await fillStep2(user);
    await user.click(confirmButtons()[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(fakes.account.confirmPasswordReset.mock.calls[0]?.[0]).toEqual({
      email: 'a@b.c',
      code: '123456',
      newPassword: 'pw123456',
    });
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
    expect(await screen.findByRole('status')).toHaveTextContent(PASSWORD_RESET_DONE_NOTICE);
  });

  it('state.from=/owner/offers로 들어와 완료하면 A1의 state.from이 유지된다', async () => {
    const { router } = renderReset({
      entry: { pathname: '/password-reset', state: { from: '/owner/offers' } },
    });
    const user = await ready();
    await sendCode(user);
    await fillStep2(user);
    await user.click(confirmButtons()[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toMatchObject({ from: '/owner/offers' });
  });

  it('INVALID_RESET_CODE면 화면 문구를 보이고 코드·비밀번호와 URL을 유지한다', async () => {
    const fakes = anonymousFakes();
    fakes.account.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, 'INVALID_RESET_CODE', '재설정 코드가 올바르지 않거나 만료되었습니다.'),
    );
    const { router } = renderReset({ fakes });
    const user = await ready();
    await sendCode(user);
    await fillStep2(user);
    await user.click(confirmButtons()[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.',
    );
    expect(screen.getByLabelText('6자리 코드')).toHaveValue('123456');
    expect(screen.getByLabelText('새 비밀번호 (8자 이상)')).toHaveValue('pw123456');
    expect(router.state.location.pathname).toBe('/password-reset');
  });

  it('VALIDATION_ERROR면 서버 문구를 보인다', async () => {
    const fakes = anonymousFakes();
    fakes.account.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '서버 비밀번호 규칙 문구'),
    );
    renderReset({ fakes });
    const user = await ready();
    await sendCode(user);
    await fillStep2(user);
    await user.click(confirmButtons()[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent('서버 비밀번호 규칙 문구');
  });

  it('「코드 다시 받기」는 같은 이메일로 다시 요청한다', async () => {
    const { fakes } = renderReset();
    const user = await ready();
    await sendCode(user);
    await user.click(screen.getByRole('button', { name: '코드 다시 받기' }));
    await waitFor(() => expect(fakes.account.requestPasswordReset).toHaveBeenCalledTimes(2));
    expect(fakes.account.requestPasswordReset.mock.calls[1]?.[0]).toBe('a@b.c');
  });

  it('코드를 보낸 뒤 이메일을 고치면 2단계가 닫히고, 다시 보내면 코드 칸이 비어 있다', async () => {
    renderReset();
    const user = await ready();
    await sendCode(user);
    await user.type(screen.getByLabelText('6자리 코드'), '123456');
    await user.type(emailInput(), 'x');
    expect(screen.queryByText('2단계 · 새 비밀번호')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('6자리 코드')).not.toBeInTheDocument();
    await user.click(sendButton());
    expect(await screen.findByLabelText('6자리 코드')).toHaveValue('');
  });

  it('코드 요청 대기 중에는 이메일 칸이 readOnly라 고칠 수 없고, 응답 뒤 보낸 이메일로 2단계가 열린다', async () => {
    const fakes = anonymousFakes();
    const request = deferred<void>();
    fakes.account.requestPasswordReset.mockReturnValueOnce(request.promise);
    renderReset({ fakes });
    const user = await ready();
    await user.type(emailInput(), 'a@b.c');
    await user.click(sendButton());
    await screen.findByRole('button', { name: '처리 중…' });
    expect(emailInput()).toHaveAttribute('readonly');
    await user.type(emailInput(), 'x');
    expect(emailInput()).toHaveValue('a@b.c');
    request.resolve();
    expect(await screen.findByLabelText('6자리 코드')).toBeInTheDocument();
    expect(emailInput()).not.toHaveAttribute('readonly');
    expect(emailInput()).toHaveValue('a@b.c');
  });

  it('「코드 다시 받기」 대기 중에도 이메일 칸이 readOnly라 2단계가 닫히지 않고, 응답 뒤 다시 고칠 수 있다', async () => {
    const fakes = anonymousFakes();
    renderReset({ fakes });
    const user = await ready();
    await sendCode(user);
    const resend = deferred<void>();
    fakes.account.requestPasswordReset.mockReturnValueOnce(resend.promise);
    await user.click(screen.getByRole('button', { name: '코드 다시 받기' }));
    await screen.findByRole('button', { name: '처리 중…' });
    expect(emailInput()).toHaveAttribute('readonly');
    await user.type(emailInput(), 'x');
    expect(emailInput()).toHaveValue('a@b.c');
    expect(screen.getByText('2단계 · 새 비밀번호')).toBeInTheDocument();
    resend.resolve();
    await screen.findByRole('button', { name: '코드 보내기' });
    expect(emailInput()).not.toHaveAttribute('readonly');
    expect(screen.getByLabelText('6자리 코드')).toBeInTheDocument();
    expect(fakes.account.requestPasswordReset.mock.calls[1]?.[0]).toBe('a@b.c');
  });

  it('코드 요청이 NETWORK_ERROR면 1단계 상자 안에 그 문구가 보이고 2단계는 없다', async () => {
    const fakes = anonymousFakes();
    fakes.account.requestPasswordReset.mockRejectedValue(
      new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'),
    );
    renderReset({ fakes });
    const user = await ready();
    await user.type(emailInput(), 'a@b.c');
    await user.click(sendButton());
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('네트워크 문구');
    const box = emailInput().closest('.box');
    expect(box).not.toBeNull();
    expect(within(box as HTMLElement).getByRole('alert')).toBe(alert);
    expect(screen.queryByText('2단계 · 새 비밀번호')).not.toBeInTheDocument();
  });

  it('요청 중·확인 중에는 「처리 중…」이고 연타해도 각 1회다', async () => {
    const fakes = anonymousFakes();
    const request = deferred<void>();
    const confirm = deferred<void>();
    fakes.account.requestPasswordReset.mockReturnValueOnce(request.promise);
    fakes.account.confirmPasswordReset.mockReturnValueOnce(confirm.promise);
    renderReset({ fakes });
    const user = await ready();
    await user.type(emailInput(), 'a@b.c');
    await user.click(sendButton());
    const busySend = await screen.findByRole('button', { name: '처리 중…' });
    await user.click(busySend);
    expect(fakes.account.requestPasswordReset).toHaveBeenCalledTimes(1);
    request.resolve();
    await screen.findByLabelText('6자리 코드');

    await fillStep2(user);
    await user.click(confirmButtons()[0]);
    const busyConfirm = await screen.findAllByRole('button', { name: '처리 중…' });
    expect(busyConfirm).toHaveLength(2);
    expectAllDisabled(busyConfirm, true);
    await user.click(busyConfirm[0]);
    await user.click(busyConfirm[1]);
    expect(fakes.account.confirmPasswordReset).toHaveBeenCalledTimes(1);
  });

  it('이미 로그인한 CUSTOMER가 /password-reset에 오면 /로 이동한다', async () => {
    const { router } = renderReset({ fakes: signedInFakes(customerUser) });
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
