import type { ReactNode } from 'react';
import { MyStoreProvider, StoreRepositoryToken } from '@/entities/store';
import { StoreCommandsToken } from '@/features/stores/application/tokens';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { bind, Container } from '@/shared/lib/di';
import { FakeStoreRepository } from '../../../entities/store/fakes/fakeStoreRepository.fake';
import { FakeStoreCommands } from '../fakes/fakeStoreCommands.fake';

export function renderStoresContainer(
  fakes = { repo: new FakeStoreRepository(), commands: new FakeStoreCommands() },
) {
  const container = new Container([
    bind(StoreRepositoryToken, fakes.repo),
    bind(StoreCommandsToken, fakes.commands),
  ]);
  const wrapper = ({ children }: { children: ReactNode }) => (
    <DepsProvider container={container}>
      <MyStoreProvider>{children}</MyStoreProvider>
    </DepsProvider>
  );
  return { wrapper, container, ...fakes };
}
