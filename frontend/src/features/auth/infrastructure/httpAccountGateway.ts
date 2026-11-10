import { request } from '@/shared/api/client';
import type { AccountGateway } from '../application/ports';
import { POINT_TYPES, type PointLog, type PointPage } from '../domain/points';
import type { ProfilePatch } from '../domain/profileInput';
import type { SignupInput } from '../domain/signupInput';
import type { User } from '../domain/user';
import { pick, toUser, type MeDto } from './userDto';

type ProfilePatchDto = { name?: string; phone?: string };

type PointLogDto = {
  id: string;
  amount: number;
  point_type: string;
  balance_after: number | null;
  created_at: string;
};

type PointLogListDto = {
  users_point: number;
  logs: PointLogDto[];
  page: number;
  size: number;
  total_elements: number;
};

function toPointLog(dto: PointLogDto): PointLog {
  return {
    id: dto.id,
    amount: dto.amount,
    type: pick(POINT_TYPES, dto.point_type, 'point_type'),
    balanceAfter: dto.balance_after,
    createdAt: new Date(dto.created_at),
  };
}

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

  // page는 0부터, 전체 건수는 total_elements(customer-home.md C-10)
  async findPoints(
    query: { page: number; size: number },
    signal?: AbortSignal,
  ): Promise<PointPage> {
    const params = new URLSearchParams({ page: String(query.page), size: String(query.size) });
    const dto = await request<PointLogListDto>(`/v1/users/me/points?${params.toString()}`, {
      signal,
    });
    return {
      balance: dto.users_point,
      logs: dto.logs.map(toPointLog),
      page: dto.page,
      size: dto.size,
      total: dto.total_elements,
    };
  }

  // 응답(WithdrawalResponse)은 쓰지 않는다. 비밀번호는 trim하지 않는다.
  async withdraw(password: string, signal?: AbortSignal): Promise<void> {
    await request<unknown>('/v1/users/me/withdraw', {
      method: 'POST',
      body: { password },
      signal,
    });
  }
}
