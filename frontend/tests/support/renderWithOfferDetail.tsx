import { render } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { SessionStoreToken } from '@/entities/session';
import { AccountGatewayToken, AuthGatewayToken, AuthProvider } from '@/features/auth';
import { LocationProviderToken, OfferRepositoryToken } from '@/features/offers';
import { PaymentRepositoryToken } from '@/features/payments/application/tokens';
import { ReservationRepositoryToken } from '@/features/reservations/application/tokens';
import { Container, bind } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { anonymousFakes, type AuthFakes } from './authFakes';
import { createFakes, type DepsFakes } from './renderWithDeps';

/** C2처럼 offers·reservations·payments·auth 가짜가 모두 필요한 라우트를 렌더한다(offers.md §9.5). */
export function createOfferDetailContainer(fakes: DepsFakes): Container {
  return new Container([
    bind(AuthGatewayToken, fakes.auth),
    bind(AccountGatewayToken, fakes.account),
    bind(SessionStoreToken, fakes.session),
    bind(OfferRepositoryToken, fakes.offers),
    bind(LocationProviderToken, fakes.location),
    bind(ReservationRepositoryToken, fakes.reservations),
    bind(PaymentRepositoryToken, fakes.payments),
  ]);
}

function isDepsFakes(f: AuthFakes | DepsFakes): f is DepsFakes {
  return 'reservations' in f && 'payments' in f;
}

export function renderRoutesWithOfferDetail(
  routes: RouteObject[],
  opts: { initialEntries: InitialEntry[]; fakes?: AuthFakes | DepsFakes },
) {
  const base = opts.fakes ?? anonymousFakes();
  const fakes: DepsFakes = isDepsFakes(base) ? base : createFakes(base);
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(
    <DepsProvider container={createOfferDetailContainer(fakes)}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </DepsProvider>,
  );
  return { ...result, router, fakes };
}
