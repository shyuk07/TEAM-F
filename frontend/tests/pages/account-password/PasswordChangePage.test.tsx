import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { InitialEntry } from 'react-router';
import { routes } from '@/app/router/routes';
import {
  PASSWORD_CHANGED_NOTICE,
  PASSWORD_CONFIRM_MISMATCH_MESSAGE,
  PASSWORD_TOO_LONG_MESSAGE,
} from '@/features/auth/domain/accountMessages';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser, ownerUser } from '../../features/auth/fakes/users';
import { signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function renderChange(opts: { fakes?: AuthFakes; entry?: InitialEntry } = {}) {
  return renderRoutesWithAuth(routes, {
    initialEntries: [opts.entry ?? '/account/password'],
    fakes: opts.fakes ?? signedInFakes(customerUser),
  });
}

async function ready() {
  await screen.findByRole('heading', { name: '비밀번호 변경' });
  return userEvent.setup();
}

const current = () => screen.getByLabelText('현재 비밀번호');
const next = () => screen.getByLabelText('새 비밀번호 (8자 이상)');
const confirm = () => screen.getByLabelText('새 비밀번호 확인');
const submitButtons = () => screen.getAllByRole('button', { name: '비밀번호 바꾸기' });

async function fill(
  user: ReturnType<typeof userEvent.setup>,
  values: { current?: string; next?: string; confirm?: string } = {},
) {
  await user.type(current(), values.current ?? 'old12345');
  await user.type(next(), values.next ?? 'new12345');
  await user.type(confirm(), values.confirm ?? values.next ?? 'new12345');
}

function expectAllDisabled(buttons: HTMLElement[], disabled: boolean) {
  for (const b of buttons) {
    if (disabled) expect(b).toHaveAttribute('aria-disabled', 'true');
    else expect(b).not.toHaveAttribute('aria-disabled', 'true');
  }
}

async function submitWithError(err: ApiError) {
  const fakes = signedInFakes(customerUser);
  fakes.account.changePassword.mockRejectedValue(err);
  const result = renderChange({ fakes });
  const user = await ready();
  await fill(user);
  await user.click(submitButtons()[0]);
  return { ...result, user };
}

describe('PasswordChangePage (C9)', () => {
  it('제목·라벨 3개·세션 유지 안내가 있다', async () => {
    renderChange();
    await ready();
    expect(screen.getByRole('heading', { level: 1, name: '비밀번호 변경' })).toBeInTheDocument();
    expect(current()).toBeInTheDocument();
    expect(next()).toBeInTheDocument();
    expect(confirm()).toBeInTheDocument();
    expect(
      screen.getByText('바꿔도 이 기기는 로그인이 유지되고, 다른 기기에서는 로그아웃돼요.'),
    ).toBeInTheDocument();
  });

  it('처음에는 「비밀번호 바꾸기」 두 벌이 비활성이다', async () => {
    renderChange();
    await ready();
    const buttons = submitButtons();
    expect(buttons).toHaveLength(2);
    expectAllDisabled(buttons, true);
  });

  it('확인이 다르면 확인 칸 아래 임시 문구가 보이고 비활성이다', async () => {
    renderChange();
    const user = await ready();
    await fill(user, { confirm: 'new12346' });
    expect(screen.getByText(PASSWORD_CONFIRM_MISMATCH_MESSAGE)).toBeInTheDocument();
    expectAllDisabled(submitButtons(), true);
  });

  it('새 비밀번호가 73바이트면 길이 초과 임시 문구가 보인다', async () => {
    renderChange();
    const user = await ready();
    await user.type(next(), 'a'.repeat(73));
    expect(screen.getByText(PASSWORD_TOO_LONG_MESSAGE)).toBeInTheDocument();
  });

  it('유효하면 활성이고 제출하면 changePassword({currentPassword, newPassword})를 부른다', async () => {
    const { fakes } = renderChange();
    const user = await ready();
    await fill(user);
    expectAllDisabled(submitButtons(), false);
    await user.click(submitButtons()[0]);
    await waitFor(() => expect(fakes.account.changePassword).toHaveBeenCalledTimes(1));
    expect(fakes.account.changePassword.mock.calls[0]?.[0]).toEqual({
      currentPassword: 'old12345',
      newPassword: 'new12345',
    });
  });

  it('성공하면 세 칸을 비우고 완료 문구를 보이며 세션·인증 상태·URL을 유지한다', async () => {
    const { fakes, router } = renderChange();
    const user = await ready();
    await fill(user);
    await user.click(submitButtons()[0]);
    expect(await screen.findByRole('status')).toHaveTextContent(PASSWORD_CHANGED_NOTICE);
    expect(current()).toHaveValue('');
    expect(next()).toHaveValue('');
    expect(confirm()).toHaveValue('');
    expect(fakes.session.clear).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: '비밀번호 변경' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/account/password');
  });

  it('CURRENT_PASSWORD_MISMATCH면 현재 비밀번호 칸 아래 화면 문구를 보이고 입력값을 유지한다', async () => {
    await submitWithError(
      new ApiError(400, 'CURRENT_PASSWORD_MISMATCH', '현재 비밀번호가 올바르지 않습니다.'),
    );
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('현재 비밀번호가 일치하지 않습니다.');
    // 현재 비밀번호 칸 뒤, 새 비밀번호 칸 앞
    expect(
      current().compareDocumentPosition(alert) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(alert.compareDocumentPosition(next()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(current()).toHaveValue('old12345');
    expect(next()).toHaveValue('new12345');
    expect(confirm()).toHaveValue('new12345');
  });

  it('VALIDATION_ERROR면 서버 문구를 보인다', async () => {
    await submitWithError(new ApiError(400, 'VALIDATION_ERROR', '서버 규칙 문구'));
    expect(await screen.findByRole('alert')).toHaveTextContent('서버 규칙 문구');
  });

  it('401이면 세션을 지우고 /login으로 가며 from이 /account/password다', async () => {
    const { router, fakes } = await submitWithError(
      new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.'),
    );
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(fakes.session.clear).toHaveBeenCalled();
    expect(router.state.location.state).toMatchObject({ from: '/account/password' });
  });

  it('제출 중에는 「처리 중…」이고 연타해도 1회다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.changePassword.mockReturnValue(deferred<void>().promise);
    renderChange({ fakes });
    const user = await ready();
    await fill(user);
    await user.click(submitButtons()[0]);
    const busy = await screen.findAllByRole('button', { name: '처리 중…' });
    expect(busy).toHaveLength(2);
    expectAllDisabled(busy, true);
    await user.click(busy[0]);
    await user.click(busy[1]);
    expect(fakes.account.changePassword).toHaveBeenCalledTimes(1);
  });

  it('비밀번호 칸 autoComplete: current-password, new-password, new-password', async () => {
    renderChange();
    await ready();
    expect(current()).toHaveAttribute('autocomplete', 'current-password');
    expect(next()).toHaveAttribute('autocomplete', 'new-password');
    expect(confirm()).toHaveAttribute('autocomplete', 'new-password');
  });

  it('「뒤로」: from이 없는 OWNER는 /owner/today로 간다', async () => {
    renderChange({ fakes: signedInFakes(ownerUser) });
    await ready();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/owner/today');
  });

  it('403이면 서버 문구를 보인다', async () => {
    await submitWithError(new ApiError(403, 'FORBIDDEN', '정지된 계정입니다.'));
    expect(await screen.findByRole('alert')).toHaveTextContent('정지된 계정입니다.');
  });
});
