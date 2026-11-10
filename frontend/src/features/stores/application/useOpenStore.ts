import { useDep } from '@/shared/lib/di';
import { openStoreErrorMessage } from '../domain/storeMessage';
import { openStore } from './openStore';
import { StoreCommandsToken } from './tokens';
import { useStoreSubmission } from './useStoreSubmission';

// 개설 흐름은 useStoreSubmission에 맡기고 딱 개설 유스케이스·문구·충돌 코드만 안다.
export function useOpenStore(): {
  submit(pickupAddress: string): Promise<void>;
  pending: boolean;
  errorMessage: string | null;
} {
  const commands = useDep(StoreCommandsToken);
  return useStoreSubmission({
    run: (pickupAddress, signal) => openStore({ commands }, { pickupAddress }, signal),
    errorMessage: openStoreErrorMessage,
    conflictReload: 'STORE_ALREADY_EXISTS',
  });
}
