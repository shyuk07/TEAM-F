import type { ReactNode } from 'react';
import { DepsContext, type Container } from './di';

export function DepsProvider({
  container,
  children,
}: {
  container: Container;
  children: ReactNode;
}) {
  return <DepsContext.Provider value={container}>{children}</DepsContext.Provider>;
}
