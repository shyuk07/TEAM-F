import { request } from '@/shared/api/client';
import type { AccountGateway } from '../application/ports';
import type { PointPage } from '../domain/points';
import type { ProfilePatch } from '../domain/profileInput';
import type { SignupInput } from '../domain/signupInput';
import type { User } from '../domain/user';
import { toUser, type MeDto } from './userDto';

type ProfilePatchDto = { name?: string; phone?: string };

// 넣은 키만 보낸다(undefined 키를 만들지 않음).
function toProfilePatchDto(patch: ProfilePatch): ProfilePatchDto {
  const dto: ProfilePatchDto = {};
  if (patch.name !== undefined) dto.name = patch.name;
  if (patch.phone !== undefined) dto.phone = patch.phone;
  return dto;
}

export class HttpAccountGateway implements AccountGateway {
  async signup(input: SignupInput, signal?: AbortSignal): Promise<void> {
    await request<unknown>('/v1/auth/signup', {
      method: 'POST',
      body: {
        email: input.email,
        password: input.password,
        name: input.name,
        phone: input.phone,
        role: input.role,
      },
      auth: false,
      signal,
    });
  }

  async requestPasswordReset(email: string, signal?: AbortSignal): Promise<void> {
    await request<void>('/v1/auth/password-reset/request', {
      method: 'POST',
      body: { email },
      auth: false,
      signal,
    });
  }

  async confirmPasswordReset(
    input: { email: string; code: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void> {
    await request<void>('/v1/auth/password-reset/confirm', {
      method: 'POST',
      body: { email: input.email, code: input.code, new_password: input.newPassword },
      auth: false,
      signal,
    });
  }

  async updateProfile(patch: ProfilePatch, signal?: AbortSignal): Promise<User> {
    const dto = await request<MeDto>('/v1/users/me', {
      method: 'PATCH',
      body: toProfilePatchDto(patch),
      signal,
    });
    return toUser(dto);
  }

  async changePassword(
    input: { currentPassword: string; newPassword: string },
    signal?: AbortSignal,
  ): Promise<void> {
    await request<void>('/v1/users/me/password', {
      method: 'POST',
      body: { current_password: input.currentPassword, new_password: input.newPassword },
      signal,
    });
  }

  findPoints(query: { page: number; size: number }, signal?: AbortSignal): Promise<PointPage> {
    void query;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.findPoints');
  }

  withdraw(password: string, signal?: AbortSignal): Promise<void> {
    void password;
    void signal;
    throw new Error('not implemented: HttpAccountGateway.withdraw');
  }
}
