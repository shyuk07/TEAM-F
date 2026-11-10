export type PasswordCheck = 'ok' | 'empty' | 'blank' | 'tooShort' | 'tooLong';

export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_BYTES = 72;

// TextEncoder 없이 코드 포인트별 UTF-8 바이트 수를 더한다(백엔드 bcrypt 72바이트 제한과 같은 기준).
export function utf8ByteLength(text: string): number {
  let bytes = 0;
  for (const ch of text) {
    const cp = ch.codePointAt(0) ?? 0;
    if (cp <= 0x7f) bytes += 1;
    else if (cp <= 0x7ff) bytes += 2;
    else if (cp <= 0xffff) bytes += 3;
    else bytes += 4;
  }
  return bytes;
}

// 백엔드 user.py와 같은 순서: 빈 값 → 공백만 → 최소 길이(코드 포인트) → 최대 바이트. trim하지 않는다.
export function checkPassword(password: string): PasswordCheck {
  if (password === '') return 'empty';
  if (password.trim() === '') return 'blank';
  if ([...password].length < PASSWORD_MIN_LENGTH) return 'tooShort';
  if (utf8ByteLength(password) > PASSWORD_MAX_BYTES) return 'tooLong';
  return 'ok';
}
