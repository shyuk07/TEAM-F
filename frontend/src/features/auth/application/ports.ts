import type { AccountStatus, User } from '../domain/user';

export type LoginResult = { accessToken: string; status: AccountStatus };

export interface AuthGateway {
  login(email: string, password: string, signal?: AbortSignal): Promise<LoginResult>;
  logout(signal?: AbortSignal): Promise<void>;
  findMe(signal?: AbortSignal): Promise<User>;
}
