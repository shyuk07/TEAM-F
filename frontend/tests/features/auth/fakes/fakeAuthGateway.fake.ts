import { vi } from 'vitest';
import type { AuthGateway } from '@/features/auth';
import { ownerUser } from './users';

export class FakeAuthGateway implements AuthGateway {
  login = vi.fn<AuthGateway['login']>(() =>
    Promise.resolve({ accessToken: 't1', status: 'APPROVED' }),
  );
  logout = vi.fn<AuthGateway['logout']>(() => Promise.resolve());
  findMe = vi.fn<AuthGateway['findMe']>(() => Promise.resolve(ownerUser));
}
