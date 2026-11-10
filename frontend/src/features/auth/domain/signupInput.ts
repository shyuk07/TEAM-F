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

export function readSignupRole(search: string): SignupRole {
  void search;
  throw new Error('not implemented: readSignupRole');
}

export function canSubmitSignup(form: SignupForm): boolean {
  void form;
  throw new Error('not implemented: canSubmitSignup');
}

export function toSignupInput(form: SignupForm): SignupInput {
  void form;
  throw new Error('not implemented: toSignupInput');
}

export function nameLabel(role: SignupRole): string {
  void role;
  throw new Error('not implemented: nameLabel');
}
