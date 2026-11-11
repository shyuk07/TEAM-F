import type { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import { RouterProvider, createMemoryRouter, type InitialEntry } from 'react-router';
import { ProductRepositoryToken } from '@/entities/product';
import { ProductCommandsToken } from '@/features/products/application/tokens';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { Container, bind } from '@/shared/lib/di';
import { FakeProductRepository } from '../../../entities/product/fakes/fakeProductRepository.fake';
import { FakeProductCommands } from './fakeProductCommands.fake';

type Fakes = { repo: FakeProductRepository; commands: FakeProductCommands };

export function createProductsContainer(
  fakes: Fakes = { repo: new FakeProductRepository(), commands: new FakeProductCommands() },
) {
  const container = new Container([
    bind(ProductRepositoryToken, fakes.repo),
    bind(ProductCommandsToken, fakes.commands),
  ]);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>{children}</DepsProvider>
  );
  return { wrapper, container, ...fakes };
}

/** presentation 렌더용: 가짜 상품 포트 + 라우터('*' 라우트). 이동은 router로 확인한다. */
export function renderProducts(
  ui: ReactElement,
  opts: Partial<Fakes> & { initialEntries?: InitialEntry[] } = {},
) {
  const ctx = createProductsContainer({
    repo: opts.repo ?? new FakeProductRepository(),
    commands: opts.commands ?? new FakeProductCommands(),
  });
  const router = createMemoryRouter([{ path: '*', element: ui }], {
    initialEntries: opts.initialEntries ?? ['/'],
  });
  const result = render(
    <DepsProvider container={ctx.container}>
      <div className="app">
        <RouterProvider router={router} />
      </div>
    </DepsProvider>,
  );
  return { ...result, router, repo: ctx.repo, commands: ctx.commands };
}
