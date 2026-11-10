import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import {
  RouterProvider,
  createMemoryRouter,
  type InitialEntry,
  type RouteObject,
} from 'react-router';
import { AuthGatewayToken, AuthProvider } from '@/features/auth';
import { SessionStoreToken } from '@/entities/session';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { Container, bind } from '@/shared/lib/di';
import { anonymousFakes, signedInFakes, type AuthFakes } from './authFakes';
import { FakeStoreRepository } from '../entities/store/fakes/fakeStoreRepository.fake';

type Deps = { fakes: AuthFakes; repo: FakeStoreRepository };

function createDeps(opts: { fakes?: AuthFakes; repo?: FakeStoreRepository }): Deps {
  return {
    fakes: opts.fakes ?? anonymousFakes(),
    repo: opts.repo ?? new FakeStoreRepository(),
  };
}

// 인증 가짜 + 상점 가짜 컨테이너(authFakes의 Container binding + StoreRepositoryToken).
function createOwnerContainer(deps: Deps): Container {
  return new Container([
    bind(AuthGatewayToken, deps.fakes.auth),
    bind(SessionStoreToken, deps.fakes.session),
    bind(StoreRepositoryToken, deps.repo),
  ]);
}

function ownerTree(deps: Deps, children: ReactNode) {
  return (
    <DepsProvider container={createOwnerContainer(deps)}>
      <AuthProvider>
        <MyStoreProvider>{children}</MyStoreProvider>
      </AuthProvider>
    </DepsProvider>
  );
}

/** page 1개를 MemoryRouter 라우트 '*'로 감싸 렌더한다. router로 이동을 확인한다. */
export function renderWithOwnerStore(
  ui: ReactElement,
  opts: { initialEntries?: InitialEntry[]; fakes?: AuthFakes; repo?: FakeStoreRepository } = {},
) {
  const deps = createDeps(opts);
  const router = createMemoryRouter([{ path: '*', element: ui }], {
    initialEntries: opts.initialEntries ?? ['/'],
  });
  const result = render(ownerTree(deps, <RouterProvider router={router} />));
  return { ...result, router, fakes: deps.fakes, repo: deps.repo };
}

/** 라우트 객체를 그대로 렌더한다(가드·레이아웃 테스트용). */
export function renderRoutesWithOwnerStore(
  routes: RouteObject[],
  opts: { initialEntries: InitialEntry[]; fakes?: AuthFakes; repo?: FakeStoreRepository },
) {
  const deps = createDeps(opts);
  const router = createMemoryRouter(routes, { initialEntries: opts.initialEntries });
  const result = render(ownerTree(deps, <RouterProvider router={router} />));
  return { ...result, router, fakes: deps.fakes, repo: deps.repo };
}

export { signedInFakes };
