import type { ProfilePatch } from '../domain/profileInput';
import type { SignupInput } from '../domain/signupInput';
import type { AccountStatus, User } from '../domain/user';

export type LoginResult = { accessToken: string; status: AccountStatus };

export interface AuthGateway {
  login(email: string, password: string, signal?: AbortSignal): Promise<LoginResult>;
  logout(signal?: AbortSignal): Promise<void>;
  findMe(signal?: AbortSignal): Promise<User>;
}

// 계정 관리(가입·비밀번호 재설정·프로필·비밀번호 변경). 인증 상태를 다루는 AuthGateway와 나눈다(auth-account.md D-8).
export interface AccountGateway {
  signup(input: SignupInput, signal?: AbortSignal): Promise<void>;
  requestPasswordReset(email: string, signal?: AbortSignal): Promise<void>;
  confirmPasswordReset(
    input: { email: string; code: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void>;
  updateProfile(patch: ProfilePatch, signal?: AbortSignal): Promise<User>;
  changePassword(
    input: { currentPassword: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void>;
}
