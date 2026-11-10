import { signupAndLogin } from '@/features/auth/application/signup';
import type { SignupForm } from '@/features/auth/domain/signupInput';
import type { User } from '@/features/auth/domain/user';
import { ApiError } from '@/shared/api/error';
import { FakeAccountGateway } from '../fakes/fakeAccountGateway.fake';
import { customerUser, ownerUser } from '../fakes/users';

const form: SignupForm = {
  role: 'CUSTOMER',
  name: ' 홍길동 ',
  email: ' a@b.c ',
  password: 'pw123456',
  phone: ' 010-1 ',
};

function setup(user: User = customerUser) {
  const account = new FakeAccountGateway();
  const login = vi.fn((email: string, password: string): Promise<User> => {
    void email;
    void password;
    return Promise.resolve(user);
  });
  return { account, login, deps: { account, login } };
}

describe('signupAndLogin', () => {
  it('정리된 입력으로 가입한 뒤 같은 이메일·비밀번호로 로그인하고 loggedIn을 돌려준다', async () => {
    const { account, login, deps } = setup();
    const outcome = await signupAndLogin(deps, form);
    expect(account.signup).toHaveBeenCalledTimes(1);
    expect(account.signup.mock.calls[0]?.[0]).toEqual({
      role: 'CUSTOMER',
      name: '홍길동',
      email: 'a@b.c',
      password: 'pw123456',
      phone: '010-1',
    });
    expect(login).toHaveBeenCalledWith('a@b.c', 'pw123456');
    expect(account.signup.mock.invocationCallOrder[0]).toBeLessThan(
      login.mock.invocationCallOrder[0],
    );
    expect(outcome).toEqual({ kind: 'loggedIn', user: customerUser });
  });

  it('가입이 409면 같은 ApiError로 reject하고 로그인하지 않는다', async () => {
    const { account, login, deps } = setup();
    const err = new ApiError(409, 'EMAIL_DUPLICATED', '이미 가입된 이메일입니다.');
    account.signup.mockRejectedValue(err);
    await expect(signupAndLogin(deps, form)).rejects.toBe(err);
    expect(login).not.toHaveBeenCalled();
  });

  it('가입 성공 뒤 로그인이 실패하면 loginFailed로 resolve한다', async () => {
    const { login, deps } = setup();
    login.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    await expect(signupAndLogin(deps, form)).resolves.toEqual({ kind: 'loginFailed' });
  });

  it('가입이 400이면 reject한다', async () => {
    const { account, deps } = setup();
    const err = new ApiError(400, 'VALIDATION_ERROR', '이메일 형식이 올바르지 않습니다.');
    account.signup.mockRejectedValue(err);
    await expect(signupAndLogin(deps, form)).rejects.toBe(err);
  });

  it('상점주 폼이면 role OWNER로 가입한다', async () => {
    const { account, deps } = setup(ownerUser);
    await signupAndLogin(deps, { ...form, role: 'OWNER' });
    expect(account.signup.mock.calls[0]?.[0]).toMatchObject({ role: 'OWNER' });
  });
});
