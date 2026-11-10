import type { ReactNode } from 'react';
import { render } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { AuthProvider } from '@/features/auth';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { anonymousFakes, createAuthContainer, type AuthFakes } from './authFakes';

function withAuth(fakes: AuthFakes, children: ReactNode) {
  return (
    <DepsProvider container={createAuthContainer(fakes)}>
      <AuthProvider>{children}</AuthProvider>
    </DepsProvider>
  );
}

export function renderWithAuth(ui: ReactNode, opts: { fakes?: AuthFakes } = {}) {
  const fakes = opts.fakes ?? anonymousFakes();
  const result = render(withAuth(fakes, ui));
  return { ...result, fakes };
}

export function renderRoutesWithAuth(
  routes: RouteObject[],
  opts: { initialEntries: InitialEntry[]; fakes?: AuthFakes },
) {
  const fakes = opts.fakes ?? anonymousFakes();
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(withAuth(fakes, <RouterProvider router={router} />));
  return { ...result, router, fakes };
}
