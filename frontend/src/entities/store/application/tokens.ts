import { createToken } from '@/shared/lib/di';
import type { StoreRepository } from '../domain/storeRepository';

export const StoreRepositoryToken = createToken<StoreRepository>('StoreRepository');
