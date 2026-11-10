import { checkPassword } from './passwordRule';

export type SignupRole = 'CUSTOMER' | 'OWNER';

export type SignupForm = {
  role: SignupRole;
  name: string;
  email: string;
  password: string;
  phone: string;
};

// 보내기 전에 정리한 값(이름·이메일·전화번호 trim)
export type SignupInput = SignupForm;

export const PROFILE_TEXT_MAX_LENGTH = 100;
export const EMAIL_MAX_LENGTH = 255;

// 상점주 미리 선택은 `?role=owner` 하나뿐이다(대소문자 구분). ADMIN은 화면에서 만들 수 없다(REQ-1).
export function readSignupRole(search: string): SignupRole {
  return new URLSearchParams(search).get('role') === 'owner' ? 'OWNER' : 'CUSTOMER';
}

// 이메일 형식은 화면에서 검사하지 않고 서버 문구를 보인다(auth-account.md D-14).
export function canSubmitSignup(form: SignupForm): boolean {
  return (
    form.name.trim() !== '' &&
    form.email.trim() !== '' &&
    form.phone.trim() !== '' &&
    checkPassword(form.password) === 'ok'
  );
}

// 비밀번호의 공백은 값의 일부라 정리하지 않는다(auth-account.md D-15).
export function toSignupInput(form: SignupForm): SignupInput {
  return {
    role: form.role,
    name: form.name.trim(),
    email: form.email.trim(),
    password: form.password,
    phone: form.phone.trim(),
  };
}

export function nameLabel(role: SignupRole): string {
  return role === 'OWNER' ? '상호(상점명으로 쓰임) *' : '이름 *';
}
