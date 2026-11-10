export type StoreStatus = 'ACTIVE' | 'SUSPENDED' | 'CLOSED';

export type Store = {
  id: string;
  ownerId: string;
  name: string;
  pickupAddress: string;
  latitude: number | null;
  longitude: number | null;
  createdAt: Date;
  approvalAt: Date | null;
  closedAt: Date | null;
  status: StoreStatus;
};

// states.md 상점 표기 (F13)
const LABELS: Record<StoreStatus, string> = {
  ACTIVE: '영업 중',
  SUSPENDED: '상점 정지',
  CLOSED: '폐점',
};

export function storeStatusLabel(s: StoreStatus): string {
  return LABELS[s];
}

export function storeStatusTone(s: StoreStatus): 'ok' | 'hot' | 'mute' {
  switch (s) {
    case 'ACTIVE':
      return 'ok';
    case 'SUSPENDED':
      return 'hot';
    case 'CLOSED':
      return 'mute';
  }
}
