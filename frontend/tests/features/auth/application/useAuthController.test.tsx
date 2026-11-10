import { StrictMode, type ReactNode } from 'react';
import { act, renderHook, waitFor } from '@testing-library/react';
import { useAuth } from '@/features/auth';
import { useAuthController } from '@/features/auth/application/useAuthController';
import type { AuthState } from '@/features/auth/domain/authState';
import type { User } from '@/features/auth/domain/user';
import { ApiError } from '@/shared/api/error';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import {
  createAuthContainer,
  signedInFakes,
  anonymousFakes,
  type AuthFakes,
} from '../../../support/authFakes';
import { deferred } from '../fakes/deferred';
import { ownerUser } from '../fakes/users';

function setup(fakes: AuthFakes, strict = false) {
  const history: AuthState[] = [];
  const wrapper = ({ children }: { children: ReactNode }) => {
    const tree = <DepsProvider container={createAuthContainer(fakes)}>{children}</DepsProvider>;
    return strict ? <StrictMode>{tree}</StrictMode> : tree;
  };
  const hook = renderHook(
    () => {
      const value = useAuthController();
      history.push(value.state);
      return value;
    },
    { wrapper },
  );
  return { ...hook, history, fakes };
}

const anonymousOther = { status: 'anonymous', cause: 'other' };

describe('useAuthController', () => {
  it('세션이 없으면 동기로 anonymous(other)이고 findMe를 부르지 않는다', () => {
    const { result, fakes } = setup(anonymousFakes());
    expect(result.current.state).toEqual(anonymousOther);
    expect(fakes.auth.findMe).not.toHaveBeenCalled();
  });

  it('세션이 있으면 loading에서 시작해 findMe 성공 뒤 authenticated가 된다', async () => {
    const fakes = signedInFakes();
    const d = deferred<User>();
    fakes.auth.findMe.mockReturnValue(d.promise);
    const { result } = setup(fakes);
    expect(result.current.state).toEqual({ status: 'loading' });
    await act(async () => {
      d.resolve(ownerUser);
    });
    expect(result.current.state).toEqual({ status: 'authenticated', user: ownerUser });
  });

  it('세션이 있고 401이면 loading → anonymous(other)이고 세션을 지운다', async () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockRejectedValue(new ApiError(401, 'UNAUTHORIZED', 'x'));
    const { result } = setup(fakes);
    expect(result.current.state).toEqual({ status: 'loading' });
    await waitFor(() => expect(result.current.state).toEqual(anonymousOther));
    expect(fakes.session.clear).toHaveBeenCalled();
  });

  it('네트워크 오류면 error이고 reload()로 다시 시도해 authenticated가 된다', async () => {
    const fakes = signedInFakes();
    fakes.auth.findMe.mockRejectedValueOnce(new ApiError(0, 'NETWORK_ERROR', '네트워크'));
    const { result } = setup(fakes);
    await waitFor(() =>
      expect(result.current.state).toEqual({
        status: 'error',
        errorCode: 'NETWORK_ERROR',
        message: '네트워크',
      }),
    );
    act(() => result.current.reload());
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'authenticated', user: ownerUser }),
    );
  });

  it('login()이 성공하면 authenticated가 되고 User를 돌려준다', async () => {
    const { result } = setup(anonymousFakes());
    let user: User | undefined;
    await act(async () => {
      user = await result.current.login('a@b.c', 'pw');
    });
    expect(user).toBe(ownerUser);
    expect(result.current.state).toEqual({ status: 'authenticated', user: ownerUser });
  });

  it('login()이 401로 실패하면 상태는 그대로이고 호출한 쪽이 오류를 받는다', async () => {
    const fakes = anonymousFakes();
    const err = new ApiError(401, 'INVALID_CREDENTIALS', 'x');
    fakes.auth.login.mockRejectedValue(err);
    const { result } = setup(fakes);
    await act(async () => {
      await expect(result.current.login('a@b.c', 'bad')).rejects.toBe(err);
    });
    expect(result.current.state).toEqual(anonymousOther);
  });

  it('logout()은 최종 anonymous(loggedOut)이고 중간에 anonymous(other)가 나타나지 않는다', async () => {
    const { result, history } = setup(signedInFakes());
    await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
    const mark = history.length;
    await act(async () => {
      await result.current.logout();
    });
    expect(result.current.state).toEqual({ status: 'anonymous', cause: 'loggedOut' });
    expect(history.slice(mark)).not.toContainEqual(anonymousOther);
  });

  it('인증된 상태에서 다른 탭 로그아웃(emit false)이면 anonymous(other)가 된다', async () => {
    const fakes = signedInFakes();
    const { result } = setup(fakes);
    await waitFor(() => expect(result.current.state.status).toBe('authenticated'));
    act(() => fakes.session.emit(false));
    expect(result.current.state).toEqual(anonymousOther);
  });

  it('anonymous 상태에서 다른 탭 로그인(emit true)이면 loading을 거쳐 authenticated가 된다', async () => {
    const fakes = anonymousFakes();
    const { result, history } = setup(fakes);
    act(() => fakes.session.emit(true));
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'authenticated', user: ownerUser }),
    );
    expect(history).toContainEqual({ status: 'loading' });
  });

  it('언마운트하면 진행 중이던 findMe의 signal이 abort되고 상태 갱신 경고가 없다', async () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    const fakes = signedInFakes();
    const d = deferred<User>();
    fakes.auth.findMe.mockReturnValue(d.promise);
    const { unmount } = setup(fakes);
    const signal = fakes.auth.findMe.mock.calls[0]?.[0];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      d.resolve(ownerUser);
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('StrictMode에서도 최종 authenticated가 된다', async () => {
    const { result } = setup(signedInFakes(), true);
    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'authenticated', user: ownerUser }),
    );
  });

  it('useAuth()를 Provider 밖에서 부르면 AuthProvider를 안내하며 throw한다', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    expect(() => renderHook(() => useAuth())).toThrow(/AuthProvider/);
    errorSpy.mockRestore();
  });
});
