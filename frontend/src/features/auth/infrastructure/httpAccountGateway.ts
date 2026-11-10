import type { AccountGateway } from '../application/ports';
import type { ProfilePatch } from '../domain/profileInput';
import type { SignupInput } from '../domain/signupInput';
import type { User } from '../domain/user';

export class HttpAccountGateway implements AccountGateway {
  async signup(input: SignupInput, signal?: AbortSignal): Promise<void> {
    void input;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.signup');
  }

  async requestPasswordReset(email: string, signal?: AbortSignal): Promise<void> {
    void email;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.requestPasswordReset');
  }

  async confirmPasswordReset(
    input: { email: string; code: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void> {
    void input;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.confirmPasswordReset');
  }

  async updateProfile(patch: ProfilePatch, signal?: AbortSignal): Promise<User> {
    void patch;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.updateProfile');
  }

  async changePassword(
    input: { currentPassword: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void> {
    void input;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.changePassword');
  }
}
