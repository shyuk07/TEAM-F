import { toSignupInput, type SignupForm } from '../domain/signupInput';
import type { User } from '../domain/user';
import type { AccountGateway } from './ports';

export type SignupOutcome = { kind: 'loggedIn'; user: User } | { kind: 'loginFailed' };

// 가입 응답에는 토큰이 없어 같은 이메일·비밀번호로 로그인한다(screens.md A2).
// 가입 실패는 그대로 throw, 가입 뒤 로그인 실패는 계정이 이미 생겼으므로 loginFailed로 알린다(auth-account.md D-25).
export async function signupAndLogin(
  deps: { account: AccountGateway; login(email: string, password: string): Promise<User> },
  form: SignupForm,
  signal?: AbortSignal,
): Promise<SignupOutcome> {
  const input = toSignupInput(form);
  await deps.account.signup(input, signal);
  try {
    const user = await deps.login(input.email, input.password);
    return { kind: 'loggedIn', user };
  } catch {
    return { kind: 'loginFailed' };
  }
}
