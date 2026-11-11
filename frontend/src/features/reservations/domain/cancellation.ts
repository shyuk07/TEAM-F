import type { Reservation } from './reservation';

export type CancelAvailability =
  | { kind: 'cancellable'; until: Date | null }
  | { kind: 'deadlinePassed'; until: Date }
  | { kind: 'none' };

// 정각은 취소 가능(서버도 정각 허용, reference/reservations.md §3).
export function cancelAvailability(r: Reservation, now: Date): CancelAvailability {
  if (r.status === 'PENDING_PAYMENT') return { kind: 'cancellable', until: null };
  if (r.status !== 'RESERVED') return { kind: 'none' };
  return now.getTime() <= r.cancellableUntil.getTime()
    ? { kind: 'cancellable', until: r.cancellableUntil }
    : { kind: 'deadlinePassed', until: r.cancellableUntil };
}

export function findPendingForOffer(list: Reservation[], offerId: string): Reservation | null {
  return list.find((r) => r.offerId === offerId && r.status === 'PENDING_PAYMENT') ?? null;
}

export function shouldRefreshAfterCancelError(error: {
  status: number;
  errorCode: string;
}): boolean {
  return (
    error.status === 409 ||
    (error.status === 400 && error.errorCode === 'CANCELLATION_DEADLINE_PASSED')
  );
}
