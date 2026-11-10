import type { ProfilePatch } from '../domain/profileInput';
import type { User } from '../domain/user';
import type { ErrorInfo } from './errorInfo';

export function useUpdateProfile(): {
  submit(patch: ProfilePatch): Promise<User | undefined>;
  pending: boolean;
  error: ErrorInfo | null;
  done: boolean;
  reset(): void;
} {
  throw new Error('not implemented: useUpdateProfile');
}
