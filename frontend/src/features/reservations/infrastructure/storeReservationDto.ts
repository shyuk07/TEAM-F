import type { StoreReservation, StoreReservationStatus } from '../domain/storeReservation';

export type StoreReservationItemDto = {
  id: string;
  product_name: string;
  quantity: number;
  total_price: number;
  status: string;
  created_at: string;
};

export type StoreReservationListDto = {
  reservations: StoreReservationItemDto[];
  page: number;
  size: number;
  total: number;
};

const RESERVATION_STATUSES: readonly StoreReservationStatus[] = [
  'PENDING_PAYMENT',
  'RESERVED',
  'PICKED_UP',
  'CANCELLED',
];

export function toStoreReservationStatus(value: string): StoreReservationStatus {
  const hit = RESERVATION_STATUSES.find((s) => s === value);
  if (!hit) {
    throw new Error(`알 수 없는 예약 상태: ${value}`);
  }
  return hit;
}

export function toStoreReservation(dto: StoreReservationItemDto): StoreReservation {
  return {
    id: String(dto.id),
    productName: dto.product_name,
    quantity: dto.quantity,
    totalPrice: dto.total_price,
    status: toStoreReservationStatus(dto.status),
    createdAt: new Date(dto.created_at),
  };
}
