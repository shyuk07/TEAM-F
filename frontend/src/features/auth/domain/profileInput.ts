import type { User } from './user';

export type ProfileForm = { name: string; phone: string };

export type ProfilePatch = { name?: string; phone?: string };

// 상점주 상호는 잠근다(open-issues.md C8 임시 동작, 주석은 ProfileForm에 둠).
export function isNameLocked(user: User): boolean {
  return user.role === 'OWNER';
}

export function profileFormOf(user: User): ProfileForm {
  return { name: user.name ?? '', phone: user.phone ?? '' };
}

// 바뀐 칸만 담는다(trim 뒤 비교). 상점주 이름은 잠겨 있어 넣지 않는다.
export function profilePatch(user: User, form: ProfileForm): ProfilePatch {
  const patch: ProfilePatch = {};
  const name = form.name.trim();
  const phone = form.phone.trim();
  if (!isNameLocked(user) && name !== (user.name ?? '')) patch.name = name;
  if (phone !== (user.phone ?? '')) patch.phone = phone;
  return patch;
}

// 관리자를 뺀 회원은 변경 뒤 이름·전화번호가 둘 다 있어야 한다(reference/auth.md §8, REQ-23).
export function canSaveProfile(user: User, form: ProfileForm): boolean {
  const patch = profilePatch(user, form);
  const values = Object.values(patch);
  if (values.length === 0) return false;
  if (values.some((v) => v === '')) return false;
  if (user.role === 'ADMIN') return true;
  const name = patch.name ?? user.name ?? '';
  const phone = patch.phone ?? user.phone ?? '';
  return name.trim() !== '' && phone.trim() !== '';
}
