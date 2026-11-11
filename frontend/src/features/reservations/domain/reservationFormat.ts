import { formatHm, groupDigits } from '@/shared/lib/format';
import type { StoreReservation } from './storeReservation';

export function rowTitle(r: StoreReservation): string {
  return `${r.productName} × ${r.quantity}`;
}

export function rowMeta(r: StoreReservation): string {
  return `${groupDigits(r.totalPrice)}원 · ${formatHm(r.createdAt)} 예약`;
}

export function handoverLine(r: StoreReservation): string {
  return `${r.productName} × ${r.quantity} 전달하세요`;
}
