import type { Store } from '@/entities/store';

const base = {
  id: 'st-1',
  ownerId: 'u-owner',
  name: '망원베이커리',
  pickupAddress: '서울시 마포구 망원로 10',
  latitude: 37.55,
  longitude: 126.9,
  createdAt: new Date('2026-01-02T03:04:05Z'),
  approvalAt: new Date('2026-01-03T00:00:00Z'),
};

export const activeStore: Store = { ...base, closedAt: null, status: 'ACTIVE' };

export const suspendedStore: Store = { ...base, closedAt: null, status: 'SUSPENDED' };

export const closedStore: Store = {
  ...base,
  closedAt: new Date('2026-02-01T09:00:00Z'),
  status: 'CLOSED',
};
