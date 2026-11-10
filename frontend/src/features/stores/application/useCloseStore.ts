import type { Store } from '@/entities/store';
import { useDep } from '@/shared/lib/di';
import { closeStoreErrorMessage } from '../domain/storeMessage';
import { closeStore } from './closeStore';
import { StoreCommandsToken } from './tokens';
import { useStoreSubmission } from './useStoreSubmission';

// 폐점 흐름은 useStoreSubmission에 맡기고 딱 폐점 유스케이스·문구·충돌 코드만 안다.
// 성공·충돌 reload는 상점 재조회로 화면을 O0로 보낸다(가드).
export function useCloseStore(store: Store): {
  submit(typedName: string): Promise<void>;
  pending: boolean;
  errorMessage: string | null;
} {
  const commands = useDep(StoreCommandsToken);
  return useStoreSubmission({
    run: (typedName, signal) => closeStore({ commands }, { store, typedName }, signal),
    errorMessage: closeStoreErrorMessage,
    conflictReload: 'STORE_ALREADY_CLOSED',
  });
}
