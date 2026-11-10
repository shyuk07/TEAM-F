import { vi } from 'vitest';
import type { AccountGateway, User } from '@/features/auth';
import { ownerUser } from './users';

// 모든 메서드는 기본으로 resolve한다. updateProfile은 base 사용자에 넘긴 patch를 반영한 User를 돌려준다.
export class FakeAccountGateway implements AccountGateway {
  constructor(private readonly base: User = ownerUser) {}

  signup = vi.fn<AccountGateway['signup']>(() => Promise.resolve());
  requestPasswordReset = vi.fn<AccountGateway['requestPasswordReset']>(() => Promise.resolve());
  confirmPasswordReset = vi.fn<AccountGateway['confirmPasswordReset']>(() => Promise.resolve());
  updateProfile = vi.fn<AccountGateway['updateProfile']>((patch) =>
    Promise.resolve({ ...this.base, ...patch }),
  );
  changePassword = vi.fn<AccountGateway['changePassword']>(() => Promise.resolve());
  // 기본: 잔액 0·빈 목록
  findPoints = vi.fn<AccountGateway['findPoints']>((query) =>
    Promise.resolve({ balance: 0, logs: [], page: query.page, size: query.size, total: 0 }),
  );
  withdraw = vi.fn<AccountGateway['withdraw']>(() => Promise.resolve());
}
