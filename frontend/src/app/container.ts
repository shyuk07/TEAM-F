import { Container } from '@/shared/lib/di';
import { wireAdmin } from '@/features/admin/wiring';
import { wireAuth } from '@/features/auth/wiring';
import { wireOffers } from '@/features/offers/wiring';
import { wireStores } from '@/features/stores/wiring';
import { wireReservations } from '@/features/reservations/wiring';
import { wirePayments } from '@/features/payments/wiring';

export function createContainer(): Container {
  return new Container([
    ...wireAuth(),
    ...wireOffers(),
    ...wireAdmin(),
    ...wireStores(),
    ...wireReservations(),
    ...wirePayments(),
  ]);
}
