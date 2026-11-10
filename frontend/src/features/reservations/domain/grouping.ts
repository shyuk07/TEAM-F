import type { Reservation } from './reservation';

export type ReservationTab = 'active' | 'past';

export function isVisibleToCustomer(r: Reservation): boolean {
  return r.cancelledBy !== 'SYSTEM';
}

export function tabOf(r: Reservation, now: Date): ReservationTab {
  const beforeEnd = now.getTime() <= r.pickupEnd.getTime();
  if (r.status === 'PENDING_PAYMENT') return 'active';
  if (r.status === 'RESERVED' && beforeEnd) return 'active';
  if (r.status === 'CANCELLED' && r.cancelledBy === 'STORE' && beforeEnd) return 'active';
  return 'past';
}

export function splitByTab(
  list: Reservation[],
  now: Date,
): { active: Reservation[]; past: Reservation[] } {
  const sorted = list
    .filter(isVisibleToCustomer)
    .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  return {
    active: sorted.filter((r) => tabOf(r, now) === 'active'),
    past: sorted.filter((r) => tabOf(r, now) === 'past'),
  };
}
