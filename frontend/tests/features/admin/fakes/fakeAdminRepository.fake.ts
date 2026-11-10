import { vi } from 'vitest';
import type { AdminRepository } from '@/features/admin';
import type {
  AdminUserDetail,
  AdminUserSummary,
  PointHistory,
  UserPage,
} from '@/features/admin/domain/adminUser';

export const pendingOwner: AdminUserSummary = {
  id: '11111111-1111-4111-8111-111111111111',
  email: 'owner1@example.com',
  name: '한끼반찬',
  role: 'OWNER',
  status: 'PENDING',
  createdAt: new Date(2026, 10, 8, 10, 0),
};

export const customer: AdminUserSummary = {
  id: '22222222-2222-4222-8222-222222222222',
  email: 'customer3@example.com',
  name: '박고객',
  role: 'CUSTOMER',
  status: 'APPROVED',
  createdAt: new Date(2026, 9, 21, 10, 0),
};

export const customerDetail: AdminUserDetail = {
  ...customer,
  phone: '010-1234-5678',
  point: 2300,
};

export function page(items: AdminUserSummary[], total = items.length, p = 1, size = 20): UserPage {
  return { items, page: p, size, total };
}

export function history(balance = 2300): PointHistory {
  return {
    userId: customer.id,
    balance,
    entries: [
      {
        id: 'p1',
        amount: 115,
        type: 'EARN',
        reason: null,
        balanceAfter: 2300,
        createdAt: new Date(2026, 10, 7, 18, 2),
      },
      {
        id: 'p2',
        amount: 1000,
        type: 'GRANT',
        reason: '이벤트',
        balanceAfter: 2185,
        createdAt: new Date(2026, 10, 1, 9, 0),
      },
    ],
    page: 1,
    size: 5,
    total: 2,
  };
}

/** 모든 메서드가 vi.fn이다. 기본값: 빈 목록, customerDetail, history(). */
export class FakeAdminRepository implements AdminRepository {
  listUsers = vi.fn<AdminRepository['listUsers']>().mockResolvedValue(page([]));
  findUser = vi.fn<AdminRepository['findUser']>().mockResolvedValue(customerDetail);
  findUserPoints = vi.fn<AdminRepository['findUserPoints']>().mockResolvedValue(history());
  approveOwner = vi.fn<AdminRepository['approveOwner']>().mockResolvedValue(undefined);
  rejectOwner = vi.fn<AdminRepository['rejectOwner']>().mockResolvedValue(undefined);
  suspendUser = vi.fn<AdminRepository['suspendUser']>().mockResolvedValue(undefined);
  withdrawUser = vi
    .fn<AdminRepository['withdrawUser']>()
    .mockResolvedValue({ cancelledReservationCount: 0 });
  suspendStore = vi
    .fn<AdminRepository['suspendStore']>()
    .mockResolvedValue({ id: 's1', name: '망원베이커리', status: 'SUSPENDED' });
  closeStore = vi
    .fn<AdminRepository['closeStore']>()
    .mockResolvedValue({ id: 's1', name: '망원베이커리', status: 'CLOSED' });
  suspendOffer = vi
    .fn<AdminRepository['suspendOffer']>()
    .mockResolvedValue({ id: 'o1', title: '식빵 모둠 5종', status: 'SUSPENDED' });
  grantPoints = vi.fn<AdminRepository['grantPoints']>().mockResolvedValue({ balanceAfter: 3300 });
}
