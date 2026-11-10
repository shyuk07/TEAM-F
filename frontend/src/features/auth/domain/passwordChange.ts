export type PasswordChangeForm = { current: string; next: string; confirm: string };

export function isConfirmMismatch(next: string, confirm: string): boolean {
  void next;
  void confirm;
  throw new Error('not implemented: isConfirmMismatch');
}

export function canSubmitPasswordChange(form: PasswordChangeForm): boolean {
  void form;
  throw new Error('not implemented: canSubmitPasswordChange');
}
