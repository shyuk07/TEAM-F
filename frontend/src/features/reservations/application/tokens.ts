import { createToken } from '@/shared/lib/di';
import type { ReservationRepository } from '../domain/ports';

export const ReservationRepositoryToken =
  createToken<ReservationRepository>('ReservationRepository');
