import type { ReactNode } from 'react';
import { render, renderHook } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { SessionStoreToken } from '@/entities/session';
import { AccountGatewayToken, AuthGatewayToken, AuthProvider } from '@/features/auth';
import { LocationProviderToken, OfferRepositoryToken } from '@/features/offers';
import { Container, bind, type Binding } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { FakeLocationProvider } from '../features/offers/fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../features/offers/fakes/fakeOfferRepository.fake';
import { anonymousFakes, type AuthFakes } from './authFakes';

export type OfferFakes = { offers: FakeOfferRepository; location: FakeLocationProvider };

/** 저장소는 기본 결과(카드 1장), 위치는 수동(resolve()로 풀기 전까지 대기). */
export function defaultOfferFakes(): OfferFakes {
  return { offers: new FakeOfferRepository(), location: new FakeLocationProvider() };
}

function offerBindings(fakes: OfferFakes): Binding[] {
  return [bind(OfferRepositoryToken, fakes.offers), bind(LocationProviderToken, fakes.location)];
}

function authBindings(fakes: AuthFakes): Binding[] {
  return [
    bind(AuthGatewayToken, fakes.auth),
    bind(SessionStoreToken, fakes.session),
    bind(AccountGatewayToken, fakes.account),
  ];
}

/** 인증 가짜 + offers 가짜를 한 컨테이너에 담는다. */
export function createAuthOffersContainer(auth: AuthFakes, offerFakes: OfferFakes): Container {
  return new Container([...authBindings(auth), ...offerBindings(offerFakes)]);
}

export function renderRoutesWithOffers(
  routes: RouteObject[],
  opts: { initialEntries: InitialEntry[]; fakes?: AuthFakes; offerFakes?: OfferFakes },
) {
  const fakes = opts.fakes ?? anonymousFakes();
  const offerFakes = opts.offerFakes ?? defaultOfferFakes();
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(
    <DepsProvider container={createAuthOffersContainer(fakes, offerFakes)}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </DepsProvider>,
  );
  return { ...result, router, fakes, offerFakes };
}

/** offers 가짜만 담은 DepsProvider 안에서 훅을 렌더한다. useAuth를 쓰지 않는 훅용. */
export function renderOffersHook<R, P = undefined>(
  hook: (props: P) => R,
  opts: { offerFakes?: OfferFakes; initialProps?: P } = {},
) {
  const offerFakes = opts.offerFakes ?? defaultOfferFakes();
  const container = new Container(offerBindings(offerFakes));
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>{children}</DepsProvider>
  );
  return { ...renderHook(hook, { wrapper, initialProps: opts.initialProps as P }), offerFakes };
}
