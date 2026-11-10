import { createToken } from '@/shared/lib/di';
import type { AdminRepository } from '../domain/adminRepository';

export const AdminRepositoryToken = createToken<AdminRepository>('AdminRepository');
