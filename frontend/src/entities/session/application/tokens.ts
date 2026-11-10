import { createToken } from '@/shared/lib/di';
import type { SessionStore } from './ports';

export const SessionStoreToken = createToken<SessionStore>('SessionStore');
