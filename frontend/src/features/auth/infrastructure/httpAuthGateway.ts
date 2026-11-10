import type { AuthGateway, LoginResult } from '../application/ports';
import type { User } from '../domain/user';

export class HttpAuthGateway implements AuthGateway {
  login(email: string, password: string, signal?: AbortSignal): Promise<LoginResult> {
    void email;
    void password;
    void signal;
    throw new Error('not implemented: HttpAuthGateway.login');
  }

  logout(signal?: AbortSignal): Promise<void> {
    void signal;
    throw new Error('not implemented: HttpAuthGateway.logout');
  }

  findMe(signal?: AbortSignal): Promise<User> {
    void signal;
    throw new Error('not implemented: HttpAuthGateway.findMe');
  }
}
