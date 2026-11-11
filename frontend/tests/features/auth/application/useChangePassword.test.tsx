import { act, waitFor } from '@testing-library/react';
import { useAuth } from '@/features/auth';
import { useChangePassword } from '@/features/auth/application/useChangePassword';
import type { PasswordChangeForm } from '@/features/auth/domain/passwordChange';
import { ApiError } from '@/shared/api/error';
import { signedInFakes } from '../../../support/authFakes';
import { renderAuthHook } from '../../../support/renderAuthHook';
import { deferred } from '../fakes/deferred';
import { customerUser } from '../fakes/users';

const form: PasswordChangeForm = { current: 'old12345', next: 'new12345', confirm: 'new12345' };

async function setup(fakes = signedInFakes(customerUser)) {
  const hook = renderAuthHook(() => ({ change: useChangePassword(), auth: useAuth() }), { fakes });
  await waitFor(() => expect(hook.result.current.auth.state.status).toBe('authenticated'));
  return hook;
}

describe('useChangePassword', () => {
  it('성공하면 true·done이고 인증 상태와 세션은 그대로다', async () => {
    const { result, fakes } = await setup();
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.change.submit(form);
    });
    expect(ok).toBe(true);
    expect(result.current.change.done).toBe(true);
    expect(result.current.auth.state).toEqual({ status: 'authenticated', user: customerUser });
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });

  it('CURRENT_PASSWORD_MISMATCH면 false이고 error가 있다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.changePassword.mockRejectedValue(
      new ApiError(400, 'CURRENT_PASSWORD_MISMATCH', '현재 비밀번호가 올바르지 않습니다.'),
    );
    const { result } = await setup(fakes);
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.change.submit(form);
    });
    expect(ok).toBe(false);
    expect(result.current.change.error?.errorCode).toBe('CURRENT_PASSWORD_MISMATCH');
  });

  it('401이면 인증 상태가 anonymous가 된다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.changePassword.mockRejectedValue(
      new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.'),
    );
    const { result } = await setup(fakes);
    await act(async () => {
      await result.current.change.submit(form);
    });
    expect(result.current.auth.state.status).toBe('anonymous');
  });

  it('제출 중에는 pending이다', async () => {
    const fakes = signedInFakes(customerUser);
    const d = deferred<void>();
    fakes.account.changePassword.mockReturnValue(d.promise);
    const { result } = await setup(fakes);
    act(() => {
      void result.current.change.submit(form);
    });
    await waitFor(() => expect(result.current.change.pending).toBe(true));
    await act(async () => {
      d.resolve();
    });
    await waitFor(() => expect(result.current.change.pending).toBe(false));
  });
});
