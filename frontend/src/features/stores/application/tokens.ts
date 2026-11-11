import { createToken } from '@/shared/lib/di';
import type { StoreCommands } from '../domain/storeCommands';

export const StoreCommandsToken = createToken<StoreCommands>('StoreCommands');
