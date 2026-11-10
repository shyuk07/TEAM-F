import { act, waitFor } from '@testing-library/react';
import { useAuth } from '@/features/auth';
import { useUpdateProfile } from '@/features/auth/application/useUpdateProfile';
import type { AuthState } from '@/features/auth/domain/authState';
import type { User } from '@/features/auth/domain/user';
import { ApiError } from '@/shared/api/error';
import { signedInFakes } from '../../../support/authFakes';
import { renderAuthHook } from '../../../support/renderAuthHook';
import { deferred } from '../fakes/deferred';
import { customerUser } from '../fakes/users';

async function setup(fakes = signedInFakes(customerUser)) {
  const history: AuthState[] = [];
  const hook = renderAuthHook(
    () => {
      const auth = useAuth();
      history.push(auth.state);
      return { profile: useUpdateProfile(), auth };
    },
    { fakes },
  );
  await waitFor(() => expect(hook.result.current.auth.state.status).toBe('authenticated'));
  return { ...hook, history };
}

describe('useUpdateProfile', () => {
  it('성공하면 인증 상태의 사용자가 응답 User로 바뀌고 done이며 loading을 거치지 않는다', async () => {
    const { result, history } = await setup();
    const mark = history.length;
    await act(async () => {
      await result.current.profile.submit({ phone: '010-2' });
    });
    expect(result.current.auth.state).toEqual({
      status: 'authenticated',
      user: { ...customerUser, phone: '010-2' },
    });
    expect(result.current.profile.done).toBe(true);
    expect(history.slice(mark)).not.toContainEqual({ status: 'loading' });
  });

  it('401이면 인증 상태가 anonymous가 된다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.updateProfile.mockRejectedValue(
      new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.'),
    );
    const { result } = await setup(fakes);
    await act(async () => {
      await result.current.profile.submit({ phone: '010-2' });
    });
    expect(result.current.auth.state.status).toBe('anonymous');
  });

  it('400이면 error가 있다', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.account.updateProfile.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '서버 규칙 문구'),
    );
    const { result } = await setup(fakes);
    await act(async () => {
      await result.current.profile.submit({ phone: '010-2' });
    });
    expect(result.current.profile.error).toEqual({
      status: 400,
      errorCode: 'VALIDATION_ERROR',
      message: '서버 규칙 문구',
    });
  });

  it('제출 중에는 pending이다', async () => {
    const fakes = signedInFakes(customerUser);
    const d = deferred<User>();
    fakes.account.updateProfile.mockReturnValue(d.promise);
    const { result } = await setup(fakes);
    act(() => {
      void result.current.profile.submit({ phone: '010-2' });
    });
    await waitFor(() => expect(result.current.profile.pending).toBe(true));
    await act(async () => {
      d.resolve({ ...customerUser, phone: '010-2' });
    });
    await waitFor(() => expect(result.current.profile.pending).toBe(false));
  });
});
