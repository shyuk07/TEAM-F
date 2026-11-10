// auth의 Role·AccountStatus와 같은 값이다. 영역끼리 import할 수 없어 따로 둔다 (admin.md D-9).
export type AdminRole = 'CUSTOMER' | 'OWNER' | 'ADMIN';
export type AdminAccountStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | 'WITHDRAWN';

export type AdminUserSummary = {
  id: string;
  email: string;
  name: string | null;
  role: AdminRole;
  status: AdminAccountStatus;
  createdAt: Date;
};

export type AdminUserDetail = AdminUserSummary & { phone: string | null; point: number };

export type UserPage = { items: AdminUserSummary[]; page: number; size: number; total: number };

export type PointEntry = {
  id: string | null;
  amount: number;
  type: string;
  reason: string | null;
  balanceAfter: number | null;
  createdAt: Date | null;
};

export type PointHistory = {
  userId: string;
  balance: number;
  entries: PointEntry[];
  page: number;
  size: number;
  total: number;
};

export type ModeratedStore = { id: string; name: string; status: string };
export type ModeratedOffer = { id: string; title: string; status: string };
