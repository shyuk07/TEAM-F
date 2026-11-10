import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { ProfilePatch } from '../domain/profileInput';
import type { User } from '../domain/user';
import { useAuth } from './authContext';
import type { ErrorInfo } from './errorInfo';
import { AccountGatewayToken } from './tokens';
import { updateProfile } from './updateProfile';
import { useSubmit } from './useSubmit';

// 성공하면 응답 User로 인증 상태를 바로 바꾼다. reload()는 loading을 거쳐 화면이 내려가므로 쓰지 않는다(auth-account.md D-13).
export function useUpdateProfile(): {
  submit(patch: ProfilePatch): Promise<User | undefined>;
  pending: boolean;
  error: ErrorInfo | null;
  done: boolean;
  reset(): void;
} {
  const account = useDep(AccountGatewayToken);
  const session = useDep(SessionStoreToken);
  const { replaceUser } = useAuth();
  const { state, submit, reset } = useSubmit<ProfilePatch, User>(async (patch, signal) => {
    const user = await updateProfile({ account, session }, patch, signal);
    if (!signal.aborted) replaceUser(user);
    return user;
  });
  return { submit, pending: state.pending, error: state.error, done: state.done, reset };
}
