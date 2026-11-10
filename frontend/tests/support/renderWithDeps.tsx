import type { ReactNode } from 'react';
import { render } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { SessionStoreToken } from '@/entities/session';
import { AuthGatewayToken, AuthProvider } from '@/features/auth';
import { PaymentRepositoryToken } from '@/features/payments/application/tokens';
import { ReservationRepositoryToken } from '@/features/reservations/application/tokens';
import { Container, bind } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { FakePaymentRepository } from '../features/payments/fakes/fakePaymentRepository.fake';
import { FakeReservationRepository } from '../features/reservations/fakes/fakeReservationRepository.fake';
import { anonymousFakes, type AuthFakes } from './authFakes';

export type DepsFakes = AuthFakes & {
  reservations: FakeReservationRepository;
  payments: FakePaymentRepository;
};

export function createFakes(auth: AuthFakes = anonymousFakes()): DepsFakes {
  return {
    ...auth,
    reservations: new FakeReservationRepository(),
    payments: new FakePaymentRepository(),
  };
}

export function createDepsContainer(fakes: DepsFakes): Container {
  return new Container([
    bind(AuthGatewayToken, fakes.auth),
    bind(SessionStoreToken, fakes.session),
    bind(ReservationRepositoryToken, fakes.reservations),
    bind(PaymentRepositoryToken, fakes.payments),
  ]);
}

/** auth·reservations·payments 가짜 포트를 넣은 DepsProvider + AuthProvider로 감싼다. */
export function withDeps(fakes: DepsFakes, children: ReactNode) {
  return (
    <DepsProvider container={createDepsContainer(fakes)}>
      <AuthProvider>{children}</AuthProvider>
    </DepsProvider>
  );
}

export function renderWithDeps(ui: ReactNode, opts: { fakes?: DepsFakes } = {}) {
  const fakes = opts.fakes ?? createFakes();
  const result = render(withDeps(fakes, ui));
  return { ...result, fakes };
}

export function renderRoutesWithDeps(
  routes: RouteObject[],
  opts: { initialEntries: InitialEntry[]; fakes?: DepsFakes },
) {
  const fakes = opts.fakes ?? createFakes();
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(withDeps(fakes, <RouterProvider router={router} />));
  return { ...result, router, fakes };
}
