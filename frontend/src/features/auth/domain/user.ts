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

export function roleLabel(role: Role): string {
  void role;
  throw new Error('not implemented: roleLabel');
}

export function isOwnerPath(path: string): boolean {
  void path;
  throw new Error('not implemented: isOwnerPath');
}
