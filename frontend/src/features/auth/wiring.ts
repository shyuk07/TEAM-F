import { bind, type Binding } from '@/shared/lib/di';
import { SessionStoreToken } from '@/entities/session';
import { AccountGatewayToken, AuthGatewayToken } from './application/tokens';
import { HttpAccountGateway } from './infrastructure/httpAccountGateway';
import { HttpAuthGateway } from './infrastructure/httpAuthGateway';
import { LocalSessionStore } from './infrastructure/localSessionStore';

export function wireAuth(): Binding[] {
  return [
    bind(AuthGatewayToken, new HttpAuthGateway()),
    bind(SessionStoreToken, new LocalSessionStore()),
    bind(AccountGatewayToken, new HttpAccountGateway()),
  ];
}
