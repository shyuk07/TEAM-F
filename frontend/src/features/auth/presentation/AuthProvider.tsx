import type { ReactNode } from 'react';
import { AuthContext } from '../application/authContext';
import { useAuthController } from '../application/useAuthController';

export function AuthProvider({ children }: { children: ReactNode }) {
  const value = useAuthController();
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
