import type { Reservation } from './reservation';

// 결제 화면(C3)에서 결제할 수 있는 예약인지. 결제 대기만 결제한다 (docs/design/frontend/payments.md D-6)
export function isPayable(r: Reservation): boolean {
  return r.status === 'PENDING_PAYMENT';
}
