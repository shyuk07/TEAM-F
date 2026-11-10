import { createContainer } from '@/app/container';
import { SessionStoreToken } from '@/entities/session';
import { AdminRepositoryToken } from '@/features/admin';
import { AccountGatewayToken, AuthGatewayToken } from '@/features/auth';
import { LocationProviderToken, OfferRepositoryToken } from '@/features/offers';
import { Container, type Token } from '@/shared/lib/di';

// 영역 wiring이 추가될 때마다 같은 커밋에서 이 목록에 토큰을 추가한다.
const TOKENS: readonly Token<unknown>[] = [
  SessionStoreToken,
  AuthGatewayToken,
  AccountGatewayToken,
  OfferRepositoryToken,
  LocationProviderToken,
  AdminRepositoryToken,
];

describe('createContainer', () => {
  it('예외 없이 Container를 반환한다', () => {
    expect(createContainer()).toBeInstanceOf(Container);
  });

  it('호출할 때마다 새 인스턴스를 만든다', () => {
    expect(createContainer()).not.toBe(createContainer());
  });

  it('등록된 토큰은 모두 풀린다', () => {
    const container = createContainer();
    for (const token of TOKENS) {
      expect(() => container.get(token)).not.toThrow();
    }
  });
});
