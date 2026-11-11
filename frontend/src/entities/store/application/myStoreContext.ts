import { useContext } from 'react';
import { createContext } from 'react';
import type { MyStoreLookup } from '../domain/ownerEntry';
import type { Store } from '../domain/store';

export type MyStoreContextValue = { lookup: MyStoreLookup; reload(): void };

// Provider 컴포넌트는 presentation/MyStoreProvider.tsx에 둔다(authContext.ts 방식, Fast Refresh).
export const MyStoreContext = createContext<MyStoreContextValue | null>(null);

export function useMyStore(): MyStoreContextValue {
  const value = useContext(MyStoreContext);
  if (!value) throw new Error('MyStoreProvider 밖에서 useMyStore를 호출했습니다.');
  return value;
}

// lookup이 found가 아닌 상태(가드 밖)에서 부르면 오류다.
export function useOwnerStore(): Store {
  const { lookup } = useMyStore();
  if (lookup.status === 'found') return lookup.store;
  if (lookup.status === 'loading') return null as unknown as Store;
  throw new Error('상점이 없는 상태에서 useOwnerStore를 호출했습니다.');
}
