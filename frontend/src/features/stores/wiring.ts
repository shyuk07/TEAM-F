import { bind, type Binding } from '@/shared/lib/di';
import { StoreRepositoryToken } from '@/entities/store';
import { StoreCommandsToken } from './application/tokens';
import { HttpStoreCommands } from './infrastructure/httpStoreCommands';
import { HttpStoreRepository } from './infrastructure/httpStoreRepository';

export function wireStores(): Binding[] {
  return [
    bind(StoreRepositoryToken, new HttpStoreRepository()), // 소유한 entities 포트(D-16)
    bind(StoreCommandsToken, new HttpStoreCommands()), // 이 영역의 포트
  ];
}
