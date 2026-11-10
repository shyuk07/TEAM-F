export type PasswordCheck = 'ok' | 'empty' | 'blank' | 'tooShort' | 'tooLong';

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

export function utf8ByteLength(text: string): number {
  void text;
  throw new Error('not implemented: utf8ByteLength');
}

export function checkPassword(password: string): PasswordCheck {
  void password;
  throw new Error('not implemented: checkPassword');
}
