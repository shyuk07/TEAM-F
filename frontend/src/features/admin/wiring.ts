import { bind, type Binding } from '@/shared/lib/di';
import { AdminRepositoryToken } from './application/tokens';
import { HttpAdminRepository } from './infrastructure/httpAdminRepository';

export function wireAdmin(): Binding[] {
  return [bind(AdminRepositoryToken, new HttpAdminRepository())];
}
