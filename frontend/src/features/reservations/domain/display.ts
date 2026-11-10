import type { Reservation } from './reservation';

export type DisplayState =
  | 'PENDING_PAYMENT'
  | 'RESERVED'
  | 'PICKUP_MISSED'
  | 'PICKED_UP'
  | 'CANCELLED_BY_CUSTOMER'
  | 'CANCELLED_BY_STORE'
  | 'CANCELLED';

// 픽업 마감 정각은 아직 픽업 가능(reference/reservations.md §4, 양 끝 포함).
export function isPickupMissed(r: Reservation, now: Date): boolean {
  return r.status === 'RESERVED' && now.getTime() > r.pickupEnd.getTime();
}

export function displayState(r: Reservation, now: Date): DisplayState {
  switch (r.status) {
    case 'PENDING_PAYMENT':
      return 'PENDING_PAYMENT';
    case 'RESERVED':
      return isPickupMissed(r, now) ? 'PICKUP_MISSED' : 'RESERVED';
    case 'PICKED_UP':
      return 'PICKED_UP';
    case 'CANCELLED':
      if (r.cancelledBy === 'CUSTOMER') return 'CANCELLED_BY_CUSTOMER';
      if (r.cancelledBy === 'STORE') return 'CANCELLED_BY_STORE';
      return 'CANCELLED';
  }
}

const LABELS: Record<DisplayState, string> = {
  PENDING_PAYMENT: '결제 대기',
  RESERVED: '예약 확정',
  PICKUP_MISSED: '픽업 시간 지남',
  PICKED_UP: '픽업 완료',
  CANCELLED_BY_CUSTOMER: '취소됨',
  CANCELLED_BY_STORE: '매장 사정으로 취소됨',
  CANCELLED: '취소됨',
};

export function statusLabel(s: DisplayState): string {
  return LABELS[s];
}

export function statusTone(s: DisplayState): 'hot' | 'ok' | 'mute' {
  if (s === 'PENDING_PAYMENT') return 'hot';
  if (s === 'RESERVED') return 'ok';
  return 'mute';
}
