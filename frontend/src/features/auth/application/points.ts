import type { SessionStore } from '@/entities/session';
import type { PointPage } from '../domain/points';
import type { AccountGateway } from './ports';

export function loadPoints(
  deps: { account: AccountGateway; session: SessionStore },
  query: { page: number; size: number },
  signal?: AbortSignal,
): Promise<PointPage> {
  void deps;
  void query;
  void signal;
  throw new Error('not implemented: loadPoints');
}
