import { SessionStoreToken } from '@/entities/session';
import { AccountGatewayToken, AuthGatewayToken, type User } from '@/features/auth';
import { LocationProviderToken, MapRendererToken, OfferRepositoryToken } from '@/features/offers';
import { Container, bind } from '@/shared/lib/di';
import { FakeAccountGateway } from '../features/auth/fakes/fakeAccountGateway.fake';
import { FakeAuthGateway } from '../features/auth/fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../features/auth/fakes/fakeSessionStore.fake';
import { ownerUser } from '../features/auth/fakes/users';
import { FakeLocationProvider } from '../features/offers/fakes/fakeLocationProvider.fake';
import { FakeMapRenderer } from '../features/offers/fakes/fakeMapRenderer.fake';
import { FakeOfferRepository } from '../features/offers/fakes/fakeOfferRepository.fake';

export type AuthFakes = {
  auth: FakeAuthGateway;
  session: FakeSessionStore;
  account: FakeAccountGateway;
  /** 할인 목록(기본 빈 페이지). 전체 routes를 렌더하는 테스트가 깨지지 않게 함께 등록한다(customer-home.md §5.7). */
  offers: FakeOfferRepository;
  /** 기기 위치(기본 null = 위치 없음). */
  location: FakeLocationProvider;
  /** 지도 그리기(기본 resolve). */
  map: FakeMapRenderer;
};

/** 세션이 없는 상태. findMe는 기본으로 ownerUser를 돌려준다(로그인 뒤 호출됨). */
export function anonymousFakes(): AuthFakes {
  return {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(false),
    account: new FakeAccountGateway(),
    offers: new FakeOfferRepository(),
    location: new FakeLocationProvider(),
    map: new FakeMapRenderer(),
  };
}

/** 세션이 있고 findMe가 user를 돌려주는 상태. account.updateProfile은 user에 patch를 반영해 돌려준다. */
export function signedInFakes(user: User = ownerUser): AuthFakes {
  const fakes = {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(true),
    account: new FakeAccountGateway(user),
    offers: new FakeOfferRepository(),
    location: new FakeLocationProvider(),
    map: new FakeMapRenderer(),
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
    bind(LocationProviderToken, fakes.location),
    bind(MapRendererToken, fakes.map),
  ]);
}
