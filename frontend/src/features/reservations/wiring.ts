import { bind, type Binding } from '@/shared/lib/di';
import {
  PickupGatewayToken,
  ReservationRepositoryToken,
  StoreReservationRepositoryToken,
} from './application/tokens';
import { HttpPickupGateway } from './infrastructure/httpPickupGateway';
import { HttpReservationRepository } from './infrastructure/httpReservationRepository';
import { HttpStoreReservationRepository } from './infrastructure/httpStoreReservationRepository';

export function wireReservations(): Binding[] {
  return [
    bind(ReservationRepositoryToken, new HttpReservationRepository()),
    bind(StoreReservationRepositoryToken, new HttpStoreReservationRepository()),
    bind(PickupGatewayToken, new HttpPickupGateway()),
  ];
}
