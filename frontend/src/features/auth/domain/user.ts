export type Role = 'CUSTOMER' | 'OWNER' | 'ADMIN';

export type AccountStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | 'WITHDRAWN';

export type User = {
  id: string;
  email: string;
  name: string | null;
  phone: string | null;
  role: Role;
  status: AccountStatus;
  point: number;
  createdAt: Date;
};

const ROLE_LABELS: Record<Role, string> = {
  OWNER: '상점주',
  CUSTOMER: '고객',
  ADMIN: '관리자',
};

export function roleLabel(role: Role): string {
  return ROLE_LABELS[role];
}

export function isOwnerPath(path: string): boolean {
  return path === '/owner' || path.startsWith('/owner/');
}

export function isAdminPath(path: string): boolean {
  return path === '/admin' || path.startsWith('/admin/');
}
