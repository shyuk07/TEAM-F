import type { User } from './user';

export type ProfileForm = { name: string; phone: string };

export type ProfilePatch = { name?: string; phone?: string };

export function isNameLocked(user: User): boolean {
  void user;
  throw new Error('not implemented: isNameLocked');
}

export function profileFormOf(user: User): ProfileForm {
  void user;
  throw new Error('not implemented: profileFormOf');
}

export function profilePatch(user: User, form: ProfileForm): ProfilePatch {
  void user;
  void form;
  throw new Error('not implemented: profilePatch');
}

export function canSaveProfile(user: User, form: ProfileForm): boolean {
  void user;
  void form;
  throw new Error('not implemented: canSaveProfile');
}
