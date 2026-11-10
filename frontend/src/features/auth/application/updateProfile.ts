import type { SessionStore } from '@/entities/session';
import type { ProfilePatch } from '../domain/profileInput';
import type { User } from '../domain/user';
import type { AccountGateway } from './ports';

export async function updateProfile(
  deps: { account: AccountGateway; session: SessionStore },
  patch: ProfilePatch,
): Promise<User> {
  void deps;
  void patch;
  throw new Error('not implemented: updateProfile');
}
