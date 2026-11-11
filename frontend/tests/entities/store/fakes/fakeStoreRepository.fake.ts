import { vi } from 'vitest';
import type { StoreRepository } from '@/entities/store';
import { activeStore } from './stores';

export class FakeStoreRepository implements StoreRepository {
  findMine = vi.fn<StoreRepository['findMine']>(() => Promise.resolve(activeStore));
}
