import { apiGet, request } from '@/shared/api/client';
import type { AuthGateway, LoginResult } from '../application/ports';
import type { AccountStatus, User } from '../domain/user';
import { pick, toUser, type MeDto } from './userDto';

type LoginDto = { access_token: string; token_type: string; status: string };

const LOGIN_STATUSES: readonly AccountStatus[] = ['APPROVED', 'PENDING', 'REJECTED', 'SUSPENDED'];

export class HttpAuthGateway implements AuthGateway {
  async login(email: string, password: string, signal?: AbortSignal): Promise<LoginResult> {
    const dto = await request<LoginDto>('/v1/auth/login', {
      method: 'POST',
      body: { email, password },
      auth: false,
      signal,
    });
    return {
      accessToken: dto.access_token,
      status: pick(LOGIN_STATUSES, dto.status, 'status'),
    };
  }

  async logout(signal?: AbortSignal): Promise<void> {
    await request<void>('/v1/auth/logout', { method: 'POST', signal });
  }

  async findMe(signal?: AbortSignal): Promise<User> {
    return toUser(await apiGet<MeDto>('/v1/users/me', signal));
  }
}
