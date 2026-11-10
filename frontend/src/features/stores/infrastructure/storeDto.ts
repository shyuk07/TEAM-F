import type { Store, StoreStatus } from '@/entities/store';

// DTO 타입과 변환은 infrastructure 안에만 둔다(F9).
type StoreDto = {
  id: string;
  owner_id: string;
  name: string;
  pickup_address: string;
  latitude: number | null;
  longitude: number | null;
  created_at: string;
  approval_at: string | null;
  closed_at: string | null;
  status: string;
};

// 개설 응답에는 status가 없다(reference/stores.md §3). 조회 응답에는 있다.
export type { StoreDto as MyStoreDto };
export type StoreOpenDto = Omit<StoreDto, 'status'>;

function storeStatusOrThrow(rawStatus: string, fallbackStatus?: StoreStatus): StoreStatus {
  if (fallbackStatus !== undefined) return fallbackStatus;
  if (rawStatus === 'ACTIVE' || rawStatus === 'SUSPENDED' || rawStatus === 'CLOSED') {
    return rawStatus;
  }
  throw new Error(`알 수 없는 status: ${String(rawStatus)}`);
}

// status가 ACTIVE·SUSPENDED·CLOSED가 아니면 Error. 개설 응답은 fallbackStatus로 'ACTIVE'를 채운다.
export function toStore(dto: StoreDto | StoreOpenDto, fallbackStatus?: StoreStatus): Store {
  const raw = dto as StoreDto;
  return {
    id: raw.id,
    ownerId: raw.owner_id,
    name: raw.name,
    pickupAddress: raw.pickup_address,
    latitude: raw.latitude,
    longitude: raw.longitude,
    createdAt: new Date(raw.created_at),
    approvalAt: raw.approval_at !== null ? new Date(raw.approval_at) : null,
    closedAt: raw.closed_at !== null ? new Date(raw.closed_at) : null,
    status: storeStatusOrThrow(raw.status, fallbackStatus),
  };
}
