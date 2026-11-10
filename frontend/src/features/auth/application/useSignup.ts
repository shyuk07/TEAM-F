import type { SignupForm } from '../domain/signupInput';
import type { ErrorInfo } from './errorInfo';
import type { SignupOutcome } from './signup';

export function useSignup(): {
  submit(form: SignupForm): Promise<SignupOutcome | undefined>;
  pending: boolean;
  error: ErrorInfo | null;
} {
  throw new Error('not implemented: useSignup');
}
