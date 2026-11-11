import type { StoreReservationStatus } from './storeReservation';

export type PickupResult = {
  id: string;
  pickupCode: string;
  status: StoreReservationStatus;
  pickedUpAt: Date;
};

export interface PickupGateway {
  pickup(reservationId: string, code: string, signal?: AbortSignal): Promise<PickupResult>;
}
