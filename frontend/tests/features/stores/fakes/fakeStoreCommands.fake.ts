import { vi } from 'vitest';
import type { StoreCommands } from '@/features/stores/domain/storeCommands';
import { activeStore } from '../../../entities/store/fakes/stores';

export class FakeStoreCommands implements StoreCommands {
  open = vi.fn<StoreCommands['open']>(() => Promise.resolve(activeStore));
  close = vi.fn<StoreCommands['close']>(() => Promise.resolve());
}
