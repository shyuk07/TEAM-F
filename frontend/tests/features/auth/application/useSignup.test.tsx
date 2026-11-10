import { act, waitFor } from '@testing-library/react';
import { useAuth } from '@/features/auth';
import type { SignupOutcome } from '@/features/auth/application/signup';
import { useSignup } from '@/features/auth/application/useSignup';
import type { SignupForm } from '@/features/auth/domain/signupInput';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes } from '../../../support/authFakes';
import { renderAuthHook } from '../../../support/renderAuthHook';
import { deferred } from '../fakes/deferred';
import { customerUser } from '../fakes/users';

const form: SignupForm = {
  role: 'CUSTOMER',
  name: '홍길동',
  email: 'a@b.c',
  password: 'pw123456',
  phone: '010-1',
};

function setup(fakes = anonymousFakes()) {
  fakes.auth.findMe.mockResolvedValue(customerUser);
  return renderAuthHook(() => ({ signup: useSignup(), auth: useAuth() }), { fakes });
}

describe('useSignup', () => {
  it('성공하면 로그인까지 하고 인증 상태가 authenticated이며 loggedIn을 돌려준다', async () => {
    const { result, fakes } = setup();
    let outcome: SignupOutcome | undefined;
    await act(async () => {
      outcome = await result.current.signup.submit(form);
    });
    expect(fakes.auth.login).toHaveBeenCalledWith('a@b.c', 'pw123456');
    expect(result.current.auth.state).toEqual({ status: 'authenticated', user: customerUser });
    expect(outcome).toEqual({ kind: 'loggedIn', user: customerUser });
  });

  it('409면 error.errorCode가 EMAIL_DUPLICATED이고 상태는 anonymous다', async () => {
    const fakes = anonymousFakes();
    fakes.account.signup.mockRejectedValue(
      new ApiError(409, 'EMAIL_DUPLICATED', '이미 가입된 이메일입니다.'),
    );
    const { result } = setup(fakes);
    await act(async () => {
      await result.current.signup.submit(form);
    });
    expect(result.current.signup.error?.errorCode).toBe('EMAIL_DUPLICATED');
    expect(result.current.auth.state.status).toBe('anonymous');
  });

  it('가입 뒤 로그인이 실패하면 loginFailed를 돌려주고 error는 없다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.login.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    const { result } = setup(fakes);
    let outcome: SignupOutcome | undefined;
    await act(async () => {
      outcome = await result.current.signup.submit(form);
    });
    expect(outcome).toEqual({ kind: 'loginFailed' });
    expect(result.current.signup.error).toBeNull();
  });

  it('제출 중에는 pending이다', async () => {
    const fakes = anonymousFakes();
    const d = deferred<void>();
    fakes.account.signup.mockReturnValue(d.promise);
    const { result } = setup(fakes);
    expect(result.current.signup.pending).toBe(false);
    act(() => {
      void result.current.signup.submit(form);
    });
    await waitFor(() => expect(result.current.signup.pending).toBe(true));
    await act(async () => {
      d.resolve();
    });
    await waitFor(() => expect(result.current.signup.pending).toBe(false));
  });
});
