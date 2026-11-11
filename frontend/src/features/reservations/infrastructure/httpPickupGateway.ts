import { request } from '@/shared/api/client';
import type { PickupGateway, PickupResult } from '../domain/pickupGateway';
import { toStoreReservationStatus } from './storeReservationDto';

type PickupResponseDto = {
  id: string;
  pickup_code: string;
  status: string;
  picked_up_at: string;
};

export class HttpPickupGateway implements PickupGateway {
  async pickup(reservationId: string, code: string, signal?: AbortSignal): Promise<PickupResult> {
    const dto = await request<PickupResponseDto>(
      `/v1/reservations/${encodeURIComponent(reservationId)}/pickup`,
      {
        method: 'POST',
        body: {
          pickup_code: code,
        },
        signal,
      },
    );

    return {
      id: dto.id,
      pickupCode: dto.pickup_code,
      status: toStoreReservationStatus(dto.status),
      pickedUpAt: new Date(dto.picked_up_at),
    };
  }
}
