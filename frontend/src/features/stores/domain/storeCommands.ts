import type { Store } from '@/entities/store';

// 이 영역만 쓰는 도메인 포트(D-16). 개설 응답본문은 status가 없다(reference/stores.md §3).
export interface StoreCommands {
  open(pickupAddress: string, signal?: AbortSignal): Promise<Store>;
  close(storeId: string, signal?: AbortSignal): Promise<void>;
}
