import { bind, type Binding } from '@/shared/lib/di';
import { ReservationRepositoryToken } from './application/tokens';
import { HttpReservationRepository } from './infrastructure/httpReservationRepository';

export function wireReservations(): Binding[] {
  return [bind(ReservationRepositoryToken, new HttpReservationRepository())];
}
