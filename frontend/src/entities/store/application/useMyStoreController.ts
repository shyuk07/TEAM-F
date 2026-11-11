import { useDep } from '@/shared/lib/di';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { useAsync } from '@/shared/lib/useAsync';
import type { Store } from '../domain/store';
import type { MyStoreLookup } from '../domain/ownerEntry';
import type { MyStoreContextValue } from './myStoreContext';
import { StoreRepositoryToken } from './tokens';

// useDep(StoreRepositoryToken)으로 findMine을 부르고 lookup·reload로 바꿔 준다(D-15).
export function useMyStoreController(): MyStoreContextValue {
  const repo = useDep(StoreRepositoryToken);
  const state = useAsync<Store | null>((signal) => repo.findMine(signal), 'my-store');

  let lookup: MyStoreLookup;
  if (state.status === 'loading') {
    lookup = { status: 'loading' };
  } else if (state.status === 'error') {
    // readErrorInfo의 status(숫자 예: 0)는 lookup.status('error' 리터럴)와 같은 키라 필드를 나눠 담는다.
    const info = readErrorInfo(state.error);
    lookup = { status: 'error', errorCode: info.errorCode, message: info.message };
  } else if (state.data === null) {
    lookup = { status: 'none' };
  } else {
    lookup = { status: 'found', store: state.data };
  }

  return { lookup, reload: state.reload };
}
