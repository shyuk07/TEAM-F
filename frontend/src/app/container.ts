import { Container } from '@/shared/lib/di';
import { wireAuth } from '@/features/auth/wiring';
import { wireReservations } from '@/features/reservations/wiring';
import { wirePayments } from '@/features/payments/wiring';

export function createContainer(): Container {
  return new Container([...wireAuth(), ...wireReservations(), ...wirePayments()]);
}
