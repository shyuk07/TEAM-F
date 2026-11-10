import { act } from '@testing-library/react';
import { usePasswordReset } from '@/features/auth/application/usePasswordReset';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes } from '../../../support/authFakes';
import { renderAuthHook } from '../../../support/renderAuthHook';

function setup(fakes = anonymousFakes()) {
  return renderAuthHook(() => usePasswordReset(), { fakes });
}

async function requestCode(result: ReturnType<typeof setup>['result'], email = 'a@b.c') {
  await act(async () => {
    await result.current.request(email);
  });
}

describe('usePasswordReset', () => {
  it('처음에는 sentEmail이 null이다', () => {
    const { result } = setup();
    expect(result.current.sentEmail).toBeNull();
  });

  it('request(" a@b.c ") 성공하면 sentEmail이 정리된 이메일이다', async () => {
    const { result, fakes } = setup();
    await requestCode(result, ' a@b.c ');
    expect(fakes.account.requestPasswordReset.mock.calls[0]?.[0]).toBe('a@b.c');
    expect(result.current.sentEmail).toBe('a@b.c');
  });

  it('요청이 실패하면 requestError가 있고 sentEmail은 null 그대로다', async () => {
    const fakes = anonymousFakes();
    fakes.account.requestPasswordReset.mockRejectedValue(
      new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'),
    );
    const { result } = setup(fakes);
    await requestCode(result);
    expect(result.current.requestError?.errorCode).toBe('NETWORK_ERROR');
    expect(result.current.sentEmail).toBeNull();
  });

  it('resend()는 보낸 이메일로 다시 요청한다', async () => {
    const { result, fakes } = setup();
    await requestCode(result);
    await act(async () => {
      await result.current.resend();
    });
    expect(fakes.account.requestPasswordReset).toHaveBeenCalledTimes(2);
    expect(fakes.account.requestPasswordReset.mock.calls[1]?.[0]).toBe('a@b.c');
  });

  it('confirm 성공이면 true를 돌려주고 session.clear를 부른다', async () => {
    const { result, fakes } = setup();
    await requestCode(result);
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.confirm('123456', 'pw123456');
    });
    expect(ok).toBe(true);
    expect(fakes.account.confirmPasswordReset.mock.calls[0]?.[0]).toEqual({
      email: 'a@b.c',
      code: '123456',
      newPassword: 'pw123456',
    });
    expect(fakes.session.clear).toHaveBeenCalled();
  });

  it('INVALID_RESET_CODE면 false를 돌려주고 confirmError가 있다', async () => {
    const fakes = anonymousFakes();
    fakes.account.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, 'INVALID_RESET_CODE', '재설정 코드가 올바르지 않거나 만료되었습니다.'),
    );
    const { result } = setup(fakes);
    await requestCode(result);
    let ok: boolean | undefined;
    await act(async () => {
      ok = await result.current.confirm('123456', 'pw123456');
    });
    expect(ok).toBe(false);
    expect(result.current.confirmError?.errorCode).toBe('INVALID_RESET_CODE');
  });

  it('invalidate()는 sentEmail과 confirmError를 지운다', async () => {
    const fakes = anonymousFakes();
    fakes.account.confirmPasswordReset.mockRejectedValue(
      new ApiError(400, 'INVALID_RESET_CODE', 'x'),
    );
    const { result } = setup(fakes);
    await requestCode(result);
    await act(async () => {
      await result.current.confirm('123456', 'pw123456');
    });
    act(() => result.current.invalidate());
    expect(result.current.sentEmail).toBeNull();
    expect(result.current.confirmError).toBeNull();
  });
});
