import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { AccountGatewayToken, AuthGatewayToken, AuthProvider } from '@/features/auth';
import { SessionStoreToken } from '@/entities/session';
import { ProductRepositoryToken } from '@/entities/product';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import { ProductCommandsToken } from '@/features/products/application/tokens';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { OfferCommandsToken, OfferRepositoryToken } from '@/features/offers';
import { PickupGatewayToken, StoreReservationRepositoryToken } from '@/features/reservations';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { Container, bind } from '@/shared/lib/di';
import { anonymousFakes, signedInFakes, type AuthFakes } from './authFakes';
import { FakeProductRepository } from '../entities/product/fakes/fakeProductRepository.fake';
import { FakeStoreRepository } from '../entities/store/fakes/fakeStoreRepository.fake';
import { FakeOfferCommands } from '../features/offers/fakes/fakeOfferCommands.fake';
import { FakeOfferRepository } from '../features/offers/fakes/fakeOfferRepository.fake';
import { FakeProductCommands } from '../features/products/fakes/fakeProductCommands.fake';
import { FakePickupGateway } from '../features/reservations/fakes/fakePickupGateway.fake';
import { FakeStoreReservationRepository } from '../features/reservations/fakes/fakeStoreReservationRepository.fake';
import { FakeStoreCommands } from '../features/stores/fakes/fakeStoreCommands.fake';

type Deps = {
  fakes: AuthFakes;
  repo: FakeStoreRepository;
  commands: FakeStoreCommands;
  products: FakeProductRepository;
  productCommands: FakeProductCommands;
  offers: FakeOfferRepository;
  offerCommands: FakeOfferCommands;
  storeReservations: FakeStoreReservationRepository;
  pickupGateway: FakePickupGateway;
};

type DepOptions = {
  fakes?: AuthFakes;
  repo?: FakeStoreRepository;
  commands?: FakeStoreCommands;
  products?: FakeProductRepository;
  productCommands?: FakeProductCommands;
  offers?: FakeOfferRepository;
  offerCommands?: FakeOfferCommands;
  storeReservations?: FakeStoreReservationRepository;
  pickupGateway?: FakePickupGateway;
};

function createDeps(opts: DepOptions): Deps {
  return {
    fakes: opts.fakes ?? anonymousFakes(),
    repo: opts.repo ?? new FakeStoreRepository(),
    commands: opts.commands ?? new FakeStoreCommands(),
    products: opts.products ?? new FakeProductRepository(),
    productCommands: opts.productCommands ?? new FakeProductCommands(),
    offers: opts.offers ?? new FakeOfferRepository(),
    offerCommands: opts.offerCommands ?? new FakeOfferCommands(),
    storeReservations: opts.storeReservations ?? new FakeStoreReservationRepository(),
    pickupGateway: opts.pickupGateway ?? new FakePickupGateway(),
  };
}

// 인증 가짜 + 상점 가짜 + 상품 가짜 컨테이너(authFakes의 Container binding + Store·Product 토큰).
function createOwnerContainer(deps: Deps): Container {
  return new Container([
    bind(AuthGatewayToken, deps.fakes.auth),
    bind(AccountGatewayToken, deps.fakes.account),
    bind(SessionStoreToken, deps.fakes.session),
    bind(StoreRepositoryToken, deps.repo),
    bind(StoreCommandsToken, deps.commands),
    bind(ProductRepositoryToken, deps.products),
    bind(ProductCommandsToken, deps.productCommands),
    bind(OfferRepositoryToken, deps.offers),
    bind(OfferCommandsToken, deps.offerCommands),
    bind(StoreReservationRepositoryToken, deps.storeReservations),
    bind(PickupGatewayToken, deps.pickupGateway),
  ]);
}

/** 단일 page 렌더용: MyStoreProvider를 포함한다(page가 MyStoreProvider 밖에 있을 때). */
function ownerPageTree(deps: Deps, children: ReactNode) {
  return (
    <DepsProvider container={createOwnerContainer(deps)}>
      <AuthProvider>
        <MyStoreProvider>{children}</MyStoreProvider>
      </AuthProvider>
    </DepsProvider>
  );
}

/** 라우트 렌더용: MyStoreProvider를 감싸지 않는다(OwnerLayout이 직접 제공, eager findMine 중복 방지). */
function ownerRouteTree(deps: Deps, children: ReactNode) {
  return (
    <DepsProvider container={createOwnerContainer(deps)}>
      <AuthProvider>{children}</AuthProvider>
    </DepsProvider>
  );
}

/**
 * page 1개를 MemoryRouter 라우트 '*'로 감싸 렌더한다. router로 이동을 확인한다.
 * routePath를 주면(예: '/owner/products/:productId') 그 패턴에 page를 걸고, 나머지 주소는 빈 화면으로 보낸다.
 */
export function renderWithOwnerStore(
  ui: ReactElement,
  opts: DepOptions & { initialEntries?: InitialEntry[]; routePath?: string } = {},
) {
  const deps = createDeps(opts);
  const routes: RouteObject[] =
    opts.routePath === undefined
      ? [{ path: '*', element: ui }]
      : [
          { path: opts.routePath, element: ui },
          { path: '*', element: <p>다른 화면</p> },
        ];
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries ?? ['/'] });
  const result = render(ownerPageTree(deps, <RouterProvider router={router} />));
  return {
    ...result,
    router,
    fakes: deps.fakes,
    repo: deps.repo,
    products: deps.products,
    productCommands: deps.productCommands,
  };
}

/** 라우트 객체를 그대로 렌더한다(가드·레이아웃 테스트용). */
export function renderRoutesWithOwnerStore(
  routes: RouteObject[],
  opts: DepOptions & { initialEntries: InitialEntry[] },
) {
  const deps = createDeps(opts);
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(ownerRouteTree(deps, <RouterProvider router={router} />));
  return {
    ...result,
    router,
    fakes: deps.fakes,
    repo: deps.repo,
    products: deps.products,
    productCommands: deps.productCommands,
  };
}

export { signedInFakes };
