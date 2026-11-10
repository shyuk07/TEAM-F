import { checkPassword } from './passwordRule';

// 서버 `^\d{6}$`가 pydantic 영문 오류를 내지 않게 ASCII 숫자 6자리만 받는다(전각 숫자·공백 거부).
export function isResetCode(code: string): boolean {
  return /^[0-9]{6}$/.test(code);
}

export function canRequestReset(email: string): boolean {
  return email.trim() !== '';
}

export function canConfirmReset(input: {
  codeSent: boolean;
  code: string;
  newPassword: string;
}): boolean {
  return input.codeSent && isResetCode(input.code) && checkPassword(input.newPassword) === 'ok';
}
