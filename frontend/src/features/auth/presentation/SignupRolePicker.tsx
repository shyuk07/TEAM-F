import type { SignupRole } from '../domain/signupInput';

// 내부 부품(공개 API 아님): A2 역할 선택
export function SignupRolePicker(props: { value: SignupRole; onChange(role: SignupRole): void }) {
  void props;
  return null;
}
