import type { User } from '@/features/auth';

export const ownerUser: User = {
  id: 'u-owner',
  email: 'owner@test.com',
  name: '망원베이커리',
  phone: '010-1111-2222',
  role: 'OWNER',
  status: 'APPROVED',
  point: 0,
  createdAt: new Date('2026-01-02T03:04:05Z'),
};

export const customerUser: User = {
  ...ownerUser,
  id: 'u-customer',
  email: 'customer@test.com',
  name: '고객',
  role: 'CUSTOMER',
};

/** 이름이 없는 기존 고객(REQ-23 경계). */
export const legacyCustomerUser: User = {
  ...customerUser,
  id: 'u-legacy',
  name: null,
};

export const adminUser: User = {
  ...ownerUser,
  id: 'u-admin',
  email: 'admin@test.com',
  name: '관리자',
  role: 'ADMIN',
};
