import { SessionStoreToken } from '@/entities/session';
import { AccountGatewayToken, AuthGatewayToken, type User } from '@/features/auth';
import { Container, bind } from '@/shared/lib/di';
import { FakeAccountGateway } from '../features/auth/fakes/fakeAccountGateway.fake';
import { FakeAuthGateway } from '../features/auth/fakes/fakeAuthGateway.fake';
import { FakeSessionStore } from '../features/auth/fakes/fakeSessionStore.fake';
import { ownerUser } from '../features/auth/fakes/users';

export type AuthFakes = {
  auth: FakeAuthGateway;
  session: FakeSessionStore;
  account: FakeAccountGateway;
};

/** 세션이 없는 상태. findMe는 기본으로 ownerUser를 돌려준다(로그인 뒤 호출됨). */
export function anonymousFakes(): AuthFakes {
  return {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(false),
    account: new FakeAccountGateway(),
  };
}

/** 세션이 있고 findMe가 user를 돌려주는 상태. account.updateProfile은 user에 patch를 반영해 돌려준다. */
export function signedInFakes(user: User = ownerUser): AuthFakes {
  const fakes = {
    auth: new FakeAuthGateway(),
    session: new FakeSessionStore(true),
    account: new FakeAccountGateway(user),
  };
  fakes.auth.findMe.mockResolvedValue(user);
  return fakes;
}

export function createAuthContainer(fakes: AuthFakes): Container {
  return new Container([
    bind(AuthGatewayToken, fakes.auth),
    bind(SessionStoreToken, fakes.session),
    bind(AccountGatewayToken, fakes.account),
  ]);
}
