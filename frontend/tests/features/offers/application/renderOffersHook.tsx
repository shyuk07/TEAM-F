import type { ReactNode } from 'react';
import { renderHook } from '@testing-library/react';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { anonymousFakes, createAuthContainer, type AuthFakes } from '../../../support/authFakes';

/** offers 가짜(OfferRepository·LocationProvider)가 등록된 컨테이너로 훅을 렌더한다. */
export function renderOffersHook<P, R>(
  hook: (props: P) => R,
  opts: { fakes?: AuthFakes; initialProps?: P } = {},
) {
  const fakes = opts.fakes ?? anonymousFakes();
  const container = createAuthContainer(fakes);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>{children}</DepsProvider>
  );
  return { ...renderHook(hook, { wrapper, initialProps: opts.initialProps }), fakes };
}
