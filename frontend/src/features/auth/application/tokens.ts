import { createToken } from '@/shared/lib/di';
import type { AccountGateway, AuthGateway } from './ports';

export const AuthGatewayToken = createToken<AuthGateway>('AuthGateway');

export const AccountGatewayToken = createToken<AccountGateway>('AccountGateway');
