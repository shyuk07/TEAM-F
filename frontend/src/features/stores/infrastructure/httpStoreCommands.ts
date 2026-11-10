import { request } from '@/shared/api/client';
import type { Store } from '@/entities/store';
import type { StoreCommands } from '../domain/storeCommands';
import { type StoreOpenDto, toStore } from './storeDto';

export class HttpStoreCommands implements StoreCommands {
  // POST /v1/stores, body: { pickup_address } → Store(status 없음 → 'ACTIVE')
  async open(pickupAddress: string, signal?: AbortSignal): Promise<Store> {
    const dto: StoreOpenDto = await request<StoreOpenDto>('/v1/stores', {
      method: 'POST',
      body: { pickup_address: pickupAddress },
      signal,
    });
    // 개설 응답에는 status가 없으므로 'ACTIVE'로 채운다(reference/stores.md §3).
    return toStore(dto, 'ACTIVE');
  }

  // POST /v1/stores/{id}/close. 응답 본문은 쓰지 않는다(D-14).
  async close(storeId: string, signal?: AbortSignal): Promise<void> {
    await request<void>(`/v1/stores/${encodeURIComponent(storeId)}/close`, {
      method: 'POST',
      signal,
    });
  }
}
