import { render, screen, waitFor } from '@testing-library/react';
import { RouterProvider, createMemoryRouter } from 'react-router';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthFailureBridge } from '@/app/providers/AuthFailureBridge';
import { routes } from '@/app/router/routes';
import { ProductRepositoryToken } from '@/entities/product';
import { SessionStoreToken } from '@/entities/session';
import { StoreRepositoryToken } from '@/entities/store';
import { AccountGatewayToken, AuthGatewayToken, AuthProvider } from '@/features/auth';
import { LocationProviderToken, OfferRepositoryToken } from '@/features/offers';
import { ProductCommandsToken } from '@/features/products/application/tokens';
import { HttpProductRepository } from '@/features/products/infrastructure/httpProductRepository';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { notifyAuthFailure } from '@/shared/api/authFailure';
import { Container, bind } from '@/shared/lib/di';
import { FakeStoreRepository } from '../../entities/store/fakes/fakeStoreRepository.fake';
import { ownerUser } from '../../features/auth/fakes/users';
import { FakeProductCommands } from '../../features/products/fakes/fakeProductCommands.fake';
import { FakeStoreCommands } from '../../features/stores/fakes/fakeStoreCommands.fake';
import { createAuthContainer, anonymousFakes, signedInFakes } from '../../support/authFakes';
import { DepsProvider } from '@/shared/lib/DepsProvider';

type AuthFakes = ReturnType<typeof anonymousFakes>;

function renderBridge(fakes: AuthFakes) {
  render(
    <DepsProvider container={createAuthContainer(fakes)}>
      <AuthFailureBridge />
    </DepsProvider>,
  );
  return fakes;
}

describe('app/providers AuthFailureBridge', () => {
  it('마운트 후 notifyAuthFailure() → FakeSessionStore.clear 1번', () => {
    const fakes = renderBridge(signedInFakes());
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });

  it('언마운트 후에는 불려도 clear가 안 불린다', () => {
    const fakes = anonymousFakes();
    const { unmount } = render(
      <DepsProvider container={createAuthContainer(fakes)}>
        <AuthFailureBridge />
      </DepsProvider>,
    );
    unmount();
    notifyAuthFailure();
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });

  it('다시 마운트해도 한 번만 불린다(중복 등록 없음)', () => {
    const fakes = signedInFakes();
    const first = render(
      <DepsProvider container={createAuthContainer(fakes)}>
        <AuthFailureBridge />
      </DepsProvider>,
    );
    first.unmount();
    renderBridge(fakes);
    expect(screen.queryByRole('alert')).toBeNull();
    notifyAuthFailure();
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });
});

// products.md §9.8 (C-12, D-27): 세션 유무로 중복을 막는다. FakeSessionStore는 clear()에서 hasSession을 false로,
// save()에서 true로 바꾸는 상태 있는 가짜다.
describe('app/providers AuthFailureBridge 세션 유무 기준 정리 (D-27)', () => {
  it('세션이 있을 때 첫 401은 clear를 1회 부른다', () => {
    const fakes = renderBridge(signedInFakes());
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });

  it('같은 세션에서 401이 연속 3번 와도 clear는 총 1회', () => {
    const fakes = renderBridge(signedInFakes());
    notifyAuthFailure();
    notifyAuthFailure();
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });

  it('처음부터 세션이 없으면 401이 와도 clear를 부르지 않는다', () => {
    const fakes = renderBridge(anonymousFakes());
    notifyAuthFailure();
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });

  it('재로그인 뒤 두 번째 401도 세션을 정리한다(clear 총 2회)', () => {
    const fakes = renderBridge(signedInFakes());
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
    fakes.session.save('t2');
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(2);
  });

  it('두 번째 세션 만료 뒤의 연속 401은 다시 1회만 정리한다(총 2회 유지)', () => {
    const fakes = renderBridge(signedInFakes());
    notifyAuthFailure();
    fakes.session.save('t2');
    notifyAuthFailure();
    notifyAuthFailure();
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(2);
  });

  it('언마운트 후 notifyAuthFailure()는 세션이 있어도 clear를 부르지 않는다(핸들러 해제)', () => {
    const fakes = signedInFakes();
    const { unmount } = render(
      <DepsProvider container={createAuthContainer(fakes)}>
        <AuthFailureBridge />
      </DepsProvider>,
    );
    unmount();
    notifyAuthFailure();
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });
});

// products.md §9.8 통합: 실제 request를 거치는 HttpProductRepository가 401을 받으면 세션이 정리되고 O4가 로그인 화면으로 간다.
describe('app/providers AuthFailureBridge 통합 (products 요청의 401)', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function respondWith(status: number, errorCode: string) {
    fetchMock.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ success: false, error_code: errorCode, message: 'x' }), {
          status,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );
  }

  function renderOwnerStoreRoute() {
    const fakes = signedInFakes(ownerUser);
    const container = new Container([
      bind(AuthGatewayToken, fakes.auth),
      bind(AccountGatewayToken, fakes.account),
      bind(SessionStoreToken, fakes.session),
      bind(OfferRepositoryToken, fakes.offers),
      bind(LocationProviderToken, fakes.location),
      bind(StoreRepositoryToken, new FakeStoreRepository()),
      bind(StoreCommandsToken, new FakeStoreCommands()),
      bind(ProductRepositoryToken, new HttpProductRepository()),
      bind(ProductCommandsToken, new FakeProductCommands()),
    ]);
    const router = createMemoryRouter(routes, { initialEntries: ['/owner/store'] });
    render(
      <DepsProvider container={container}>
        <AuthProvider>
          <AuthFailureBridge />
          <RouterProvider router={router} />
        </AuthProvider>
      </DepsProvider>,
    );
    return { fakes, router };
  }

  it('401 UNAUTHORIZED → SessionStore.clear 1회, O4가 로그인 화면으로 이동', async () => {
    respondWith(401, 'UNAUTHORIZED');
    const { fakes, router } = renderOwnerStoreRoute();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(String(fetchMock.mock.calls[0][0])).toContain('/v1/stores/st-1/products');
    await waitFor(() => expect(fakes.session.clear).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });

  it('403은 clear를 부르지 않는다', async () => {
    respondWith(403, 'FORBIDDEN');
    const { fakes } = renderOwnerStoreRoute();
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });
});
