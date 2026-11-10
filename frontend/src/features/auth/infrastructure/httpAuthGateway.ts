import { apiGet, request } from '@/shared/api/client';
import type { AuthGateway, LoginResult } from '../application/ports';
import type { AccountStatus, Role, User } from '../domain/user';

type LoginDto = { access_token: string; token_type: string; status: string };
type MeDto = {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  role: string;
  users_point: number;
  created_at: string;
  status: string;
};

const LOGIN_STATUSES: readonly AccountStatus[] = ['APPROVED', 'PENDING', 'REJECTED', 'SUSPENDED'];
const ROLES: readonly Role[] = ['CUSTOMER', 'OWNER', 'ADMIN'];
const STATUSES: readonly AccountStatus[] = [
  'PENDING',
  'APPROVED',
  'REJECTED',
  'SUSPENDED',
  'WITHDRAWN',
];

function pick<T extends string>(allowed: readonly T[], value: string, what: string): T {
  const found = allowed.find((a) => a === value);
  if (found === undefined) throw new Error(`알 수 없는 ${what}: ${value}`);
  return found;
}

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
    const dto = await apiGet<MeDto>('/v1/users/me', signal);
    return {
      id: dto.id,
      email: dto.email,
      name: dto.name,
      phone: dto.phone,
      role: pick(ROLES, dto.role, 'role'),
      status: pick(STATUSES, dto.status, 'status'),
      point: dto.users_point,
      createdAt: new Date(dto.created_at),
    };
  }
}
