import { createToken } from '@/shared/lib/di';
import type { AuthGateway } from './ports';

export const AuthGatewayToken = createToken<AuthGateway>('AuthGateway');
