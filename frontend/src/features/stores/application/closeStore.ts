import type { Store } from '@/entities/store';
import { canSubmitClose } from '../domain/closeStoreInput';
import type { StoreCommands } from '../domain/storeCommands';

// canSubmitClose가 false이면 포트를 부르지 않고 Error를 던진다(D-8).
export async function closeStore(
  deps: { commands: StoreCommands },
  input: { store: Store; typedName: string },
  signal?: AbortSignal,
): Promise<void> {
  if (!canSubmitClose(input.typedName, input.store.name)) {
    throw new Error('상점명이 일치하지 않아요.');
  }
  await deps.commands.close(input.store.id, signal);
}
