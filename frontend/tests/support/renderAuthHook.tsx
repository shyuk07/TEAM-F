import type { ReactNode } from 'react';
import { renderHook } from '@testing-library/react';
import { AuthProvider } from '@/features/auth';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { anonymousFakes, createAuthContainer, type AuthFakes } from './authFakes';

/** 가짜 컨테이너(DepsProvider) + AuthProvider 안에서 훅을 렌더한다. */
export function renderAuthHook<R>(hook: () => R, opts: { fakes?: AuthFakes } = {}) {
  const fakes = opts.fakes ?? anonymousFakes();
  const container = createAuthContainer(fakes);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>
      <AuthProvider>{children}</AuthProvider>
    </DepsProvider>
  );
  return { ...renderHook(hook, { wrapper }), fakes };
}
