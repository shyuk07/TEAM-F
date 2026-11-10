import type { AccountStatus, Role, User } from '../domain/user';

// 내부 파일(공개 API 아님): GET·PATCH /v1/users/me 응답 변환을 HttpAuthGateway·HttpAccountGateway가 함께 쓴다.
export type MeDto = {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  role: string;
  users_point: number;
  created_at: string;
  status: string;
};

const ROLES: readonly Role[] = ['CUSTOMER', 'OWNER', 'ADMIN'];
const STATUSES: readonly AccountStatus[] = [
  'PENDING',
  'APPROVED',
  'REJECTED',
  'SUSPENDED',
  'WITHDRAWN',
];

export function pick<T extends string>(allowed: readonly T[], value: string, what: string): T {
  const found = allowed.find((a) => a === value);
  if (found === undefined) throw new Error(`알 수 없는 ${what}: ${value}`);
  return found;
}

export function toUser(dto: MeDto): User {
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
