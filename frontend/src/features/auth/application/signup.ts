import type { SignupForm } from '../domain/signupInput';
import type { User } from '../domain/user';
import type { AccountGateway } from './ports';

export type SignupOutcome = { kind: 'loggedIn'; user: User } | { kind: 'loginFailed' };

export async function signupAndLogin(
  deps: { account: AccountGateway; login(email: string, password: string): Promise<User> },
  form: SignupForm,
): Promise<SignupOutcome> {
  void deps;
  void form;
  throw new Error('not implemented: signupAndLogin');
}
