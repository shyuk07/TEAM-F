import type { StoreReservationPage, StoreReservationStatus } from './storeReservation';

export interface StoreReservationRepository {
  findByStore(
    storeId: string,
    status: StoreReservationStatus,
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<StoreReservationPage>;
}
