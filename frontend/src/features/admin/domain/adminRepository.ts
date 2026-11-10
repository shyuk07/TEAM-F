import type {
  AdminUserDetail,
  ModeratedOffer,
  ModeratedStore,
  PointHistory,
  UserPage,
} from './adminUser';
import type { UserListQuery } from './userQuery';

export interface AdminRepository {
  listUsers(q: UserListQuery, signal?: AbortSignal): Promise<UserPage>;
  findUser(id: string, signal?: AbortSignal): Promise<AdminUserDetail>;
  findUserPoints(
    id: string,
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<PointHistory>;
  approveOwner(id: string): Promise<void>;
  rejectOwner(id: string, reason: string): Promise<void>;
  suspendUser(id: string, reason: string, until: Date | null): Promise<void>;
  withdrawUser(id: string, reason: string): Promise<{ cancelledReservationCount: number }>;
  suspendStore(id: string, reason: string): Promise<ModeratedStore>;
  closeStore(id: string, reason: string): Promise<ModeratedStore>;
  suspendOffer(id: string, reason: string): Promise<ModeratedOffer>;
  grantPoints(id: string, amount: number, reason: string): Promise<{ balanceAfter: number | null }>;
}
