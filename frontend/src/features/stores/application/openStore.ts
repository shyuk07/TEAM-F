import type { Store } from '@/entities/store';
import { canSubmitOpenStore } from '../domain/openStoreInput';
import type { StoreCommands } from '../domain/storeCommands';

// canSubmitOpenStore가 false이면 포트를 부르지 않고 Error를 던진다. 포트 호출 값은 pickupAddress.trim()(D-19).
export async function openStore(
  deps: { commands: StoreCommands },
  input: { pickupAddress: string },
  signal?: AbortSignal,
): Promise<Store> {
  if (!canSubmitOpenStore(input.pickupAddress)) {
    throw new Error('픽업 주소를 입력해 주세요.');
  }
  return deps.commands.open(input.pickupAddress.trim(), signal);
}
