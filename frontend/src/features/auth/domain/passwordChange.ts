import { checkPassword } from './passwordRule';

export type PasswordChangeForm = { current: string; next: string; confirm: string };

export function isConfirmMismatch(next: string, confirm: string): boolean {
  return confirm !== '' && next !== confirm;
}

// 현재 비밀번호는 형식 검사 없이 비어 있지만 않으면 된다.
export function canSubmitPasswordChange(form: PasswordChangeForm): boolean {
  return form.current !== '' && checkPassword(form.next) === 'ok' && form.next === form.confirm;
}
