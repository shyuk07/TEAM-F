import { createToken } from '@/shared/lib/di';
import type { PickupGateway } from '../domain/pickupGateway';
import type { ReservationRepository } from '../domain/ports';
import type { StoreReservationRepository } from '../domain/storeReservationRepository';

export const ReservationRepositoryToken =
  createToken<ReservationRepository>('ReservationRepository');

export const StoreReservationRepositoryToken = createToken<StoreReservationRepository>(
  'StoreReservationRepository',
);

export const PickupGatewayToken = createToken<PickupGateway>('PickupGateway');
