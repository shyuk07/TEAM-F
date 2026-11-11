import type { ReactNode } from 'react';
import { MyStoreContext } from '../application/myStoreContext';
import { useMyStoreController } from '../application/useMyStoreController';

// OwnerStoreGate가 key={user.id}로 마운트해 계정이 바뀌면 다시 불러온다(D-15).
export function MyStoreProvider({ children }: { children: ReactNode }) {
  const value = useMyStoreController();
  return <MyStoreContext.Provider value={value}>{children}</MyStoreContext.Provider>;
}
