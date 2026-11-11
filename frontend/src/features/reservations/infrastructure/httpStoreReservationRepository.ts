import { request } from '@/shared/api/client';
import type { StoreReservationPage, StoreReservationStatus } from '../domain/storeReservation';
import type { StoreReservationRepository } from '../domain/storeReservationRepository';
import { type StoreReservationListDto, toStoreReservation } from './storeReservationDto';

export class HttpStoreReservationRepository implements StoreReservationRepository {
  async findByStore(
    storeId: string,
    status: StoreReservationStatus,
    page: number,
    size: number,
    signal?: AbortSignal,
  ): Promise<StoreReservationPage> {
    const params = new URLSearchParams();
    params.set('status', status);
    params.set('page', String(page));
    params.set('size', String(size));

    const dto = await request<StoreReservationListDto>(
      `/v1/stores/${encodeURIComponent(storeId)}/reservations?${params.toString()}`,
      { signal },
    );

    return {
      items: dto.reservations.map(toStoreReservation),
      page: dto.page,
      size: dto.size,
      total: dto.total,
    };
  }
}
