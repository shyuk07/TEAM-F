import { SessionStoreToken } from '@/entities/session';
import { ProductRepositoryToken } from '@/entities/product';
import { StoreRepositoryToken } from '@/entities/store';
import { AccountGatewayToken, AuthGatewayToken, type User } from '@/features/auth';
import {
  LocationProviderToken,
  MapRendererToken,
  OfferCommandsToken,
  OfferRepositoryToken,
} from '@/features/offers';
import { ProductCommandsToken } from '@/features/products/application/tokens';
import {
  PickupGatewayToken,
  ReservationRepositoryToken,
  StoreReservationRepositoryToken,
} from '@/features/reservations';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { Container, bind } from '@/shared/lib/di';
import { FakeProductRepository } from '../entities/product/fakes/fakeProductRepository.fake';
import { FakeStoreRepository } from '../entities/store/fakes/fakeStoreRepository.fake';
import { FakeAccountGateway } from '../features/auth/fakes/fakeAccountGateway.fake';
import { FakeAuthGateway } from '../features/auth/fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../features/auth/fakes/fakeSessionStore.fake';
import { ownerUser } from '../features/auth/fakes/users';
import { FakeLocationProvider } from '../features/offers/fakes/fakeLocationProvider.fake';
import { FakeMapRenderer } from '../features/offers/fakes/fakeMapRenderer.fake';
import { FakeOfferCommands } from '../features/offers/fakes/fakeOfferCommands.fake';
import { FakeOfferRepository } from '../features/offers/fakes/fakeOfferRepository.fake';
import { FakeProductCommands } from '../features/products/fakes/fakeProductCommands.fake';
import { FakePickupGateway } from '../features/reservations/fakes/fakePickupGateway.fake';
import { FakeReservationRepository } from '../features/reservations/fakes/fakeReservationRepository.fake';
import { FakeStoreReservationRepository } from '../features/reservations/fakes/fakeStoreReservationRepository.fake';
import { FakeStoreCommands } from '../features/stores/fakes/fakeStoreCommands.fake';

export type AuthFakes = {
  auth: FakeAuthGateway;
  session: FakeSessionStore;
  account: FakeAccountGateway;
  /** 할인 목록(기본 빈 페이지). 전체 routes를 렌더하는 테스트가 깨지지 않게 함께 등록한다(customer-home.md §5.7). */
  offers: FakeOfferRepository;
  offerCommands: FakeOfferCommands;
  /** 기기 위치(기본 null = 위치 없음). */
  location: FakeLocationProvider;
  /** 지도 그리기(기본 resolve). */
  map: FakeMapRenderer;
  store: FakeStoreRepository;
  storeCommands: FakeStoreCommands;
  product: FakeProductRepository;
  productCommands: FakeProductCommands;
  storeReservations: FakeStoreReservationRepository;
  pickupGateway: FakePickupGateway;
  reservation: FakeReservationRepository;
};

/** 세션이 없는 상태. findMe는 기본으로 ownerUser를 돌려준다(로그인 뒤 호출됨). */
export function anonymousFakes(): AuthFakes {
  return {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(false),
    account: new FakeAccountGateway(),
    offers: new FakeOfferRepository(),
    offerCommands: new FakeOfferCommands(),
    location: new FakeLocationProvider(),
    map: new FakeMapRenderer(),
    store: new FakeStoreRepository(),
    storeCommands: new FakeStoreCommands(),
    product: new FakeProductRepository(),
    productCommands: new FakeProductCommands(),
    storeReservations: new FakeStoreReservationRepository(),
    pickupGateway: new FakePickupGateway(),
    reservation: new FakeReservationRepository(),
  };
}

/** 세션이 있고 findMe가 user를 돌려주는 상태. account.updateProfile은 user에 patch를 반영해 돌려준다. */
export function signedInFakes(user: User = ownerUser): AuthFakes {
  const fakes = {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(true),
    account: new FakeAccountGateway(user),
    offers: new FakeOfferRepository(),
    offerCommands: new FakeOfferCommands(),
    location: new FakeLocationProvider(),
    map: new FakeMapRenderer(),
    store: new FakeStoreRepository(),
    storeCommands: new FakeStoreCommands(),
    product: new FakeProductRepository(),
    productCommands: new FakeProductCommands(),
    storeReservations: new FakeStoreReservationRepository(),
    pickupGateway: new FakePickupGateway(),
    reservation: new FakeReservationRepository(),
  };
  fakes.auth.findMe.mockResolvedValue(user);
  return fakes;
}

export function createAuthContainer(fakes: AuthFakes): Container {
  return new Container([
    bind(AuthGatewayToken, fakes.auth),
    bind(SessionStoreToken, fakes.session),
    bind(AccountGatewayToken, fakes.account),
    bind(OfferRepositoryToken, fakes.offers),
    bind(OfferCommandsToken, fakes.offerCommands),
    bind(LocationProviderToken, fakes.location),
    bind(MapRendererToken, fakes.map),
    bind(StoreRepositoryToken, fakes.store),
    bind(StoreCommandsToken, fakes.storeCommands),
    bind(ProductRepositoryToken, fakes.product),
    bind(ProductCommandsToken, fakes.productCommands),
    bind(StoreReservationRepositoryToken, fakes.storeReservations),
    bind(PickupGatewayToken, fakes.pickupGateway),
    bind(ReservationRepositoryToken, fakes.reservation),
  ]);
}
