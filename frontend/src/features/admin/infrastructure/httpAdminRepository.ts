import { apiGet, request } from '@/shared/api/client';
import type { AdminRepository } from '../domain/adminRepository';
import type {
  AdminAccountStatus,
  AdminRole,
  AdminUserDetail,
  AdminUserSummary,
  ModeratedOffer,
  ModeratedStore,
  PointEntry,
  PointHistory,
  UserPage,
} from '../domain/adminUser';
import type { UserListQuery } from '../domain/userQuery';

// reference/admin.md §10, backend/src/admin/presentation/schemas.py UserListItemResponse
type UserListItemDto = {
  id: string;
  email: string;
  name: string | null;
  role: string;
  status: string;
  created_at: string;
};
type UserPageDto = { items: UserListItemDto[]; page: number; size: number; total: number };

// backend/src/auth/presentation/schemas.py UserResponse (GET /v1/admin/users/{id})
type UserDto = UserListItemDto & { phone: string | null; users_point: number };

type PointItemDto = {
  id: string | null;
  amount: number;
  type: string;
  reason: string | null;
  balance_after: number | null;
  created_at: string | null;
};
type PointPageDto = {
  user_id: string;
  balance: number;
  history: PointItemDto[];
  page: number;
  size: number;
  total: number;
};

type StoreDto = { id: string; name: string; status: string };
type OfferDto = { id: string; title: string; status: string };
type WithdrawalDto = { cancelled_reservation_count: number };
type GrantDto = { balance_after: number | null };

const toSummary = (d: UserListItemDto): AdminUserSummary => ({
  id: d.id,
  email: d.email,
  name: d.name,
  role: d.role as AdminRole,
  status: d.status as AdminAccountStatus,
  createdAt: new Date(d.created_at),
});

const toPointEntry = (d: PointItemDto): PointEntry => ({
  id: d.id,
  amount: d.amount,
  type: d.type,
  reason: d.reason,
  balanceAfter: d.balance_after,
  createdAt: d.created_at === null ? null : new Date(d.created_at),
});

const toStore = (d: StoreDto): ModeratedStore => ({ id: d.id, name: d.name, status: d.status });
const toOffer = (d: OfferDto): ModeratedOffer => ({ id: d.id, title: d.title, status: d.status });

const enc = encodeURIComponent;

export class HttpAdminRepository implements AdminRepository {
  async listUsers(q: UserListQuery, signal?: AbortSignal): Promise<UserPage> {
    const qs = new URLSearchParams();
    if (q.role) qs.set('role', q.role);
    if (q.status) qs.set('status', q.status);
    if (q.email) qs.set('email', q.email);
    qs.set('page', String(q.page));
    qs.set('size', String(q.size));
    const d = await apiGet<UserPageDto>(`/v1/admin/users?${qs.toString()}`, signal);
    return { items: d.items.map(toSummary), page: d.page, size: d.size, total: d.total };
  }

  async findUser(id: string, signal?: AbortSignal): Promise<AdminUserDetail> {
    const d = await apiGet<UserDto>(`/v1/admin/users/${enc(id)}`, signal);
    return { ...toSummary(d), phone: d.phone, point: d.users_point };
  }

  async findUserPoints(
    id: string,
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<PointHistory> {
    const qs = new URLSearchParams({ page: String(page), size: String(size) });
    const d = await apiGet<PointPageDto>(
      `/v1/admin/users/${enc(id)}/points?${qs.toString()}`,
      signal,
    );
    return {
      userId: d.user_id,
      balance: d.balance,
      entries: d.history.map(toPointEntry),
      page: d.page,
      size: d.size,
      total: d.total,
    };
  }

  async approveOwner(id: string): Promise<void> {
    await request(`/v1/admin/owners/${enc(id)}/approve`, { method: 'PATCH' });
  }

  async rejectOwner(id: string, reason: string): Promise<void> {
    await request(`/v1/admin/owners/${enc(id)}/reject`, { method: 'PATCH', body: { reason } });
  }

  async suspendUser(id: string, reason: string, until: Date | null): Promise<void> {
    await request(`/v1/admin/users/${enc(id)}/suspend`, {
      method: 'PATCH',
      body: { reason, suspended_until: until === null ? null : until.toISOString() },
    });
  }

  async withdrawUser(id: string, reason: string): Promise<{ cancelledReservationCount: number }> {
    const d = await request<WithdrawalDto>(`/v1/admin/users/${enc(id)}`, {
      method: 'DELETE',
      body: { reason },
    });
    return { cancelledReservationCount: d.cancelled_reservation_count };
  }

  async suspendStore(id: string, reason: string): Promise<ModeratedStore> {
    return toStore(
      await request<StoreDto>(`/v1/admin/stores/${enc(id)}/suspend`, {
        method: 'PATCH',
        body: { reason },
      }),
    );
  }

  async closeStore(id: string, reason: string): Promise<ModeratedStore> {
    return toStore(
      await request<StoreDto>(`/v1/admin/stores/${enc(id)}/close`, {
        method: 'PATCH',
        body: { reason },
      }),
    );
  }

  async suspendOffer(id: string, reason: string): Promise<ModeratedOffer> {
    return toOffer(
      await request<OfferDto>(`/v1/admin/offers/${enc(id)}/suspend`, {
        method: 'PATCH',
        body: { reason },
      }),
    );
  }

  async grantPoints(
    id: string,
    amount: number,
    reason: string,
  ): Promise<{ balanceAfter: number | null }> {
    const d = await request<GrantDto>(`/v1/admin/users/${enc(id)}/points`, {
      method: 'POST',
      body: { amount, reason },
    });
    return { balanceAfter: d.balance_after };
  }
}
