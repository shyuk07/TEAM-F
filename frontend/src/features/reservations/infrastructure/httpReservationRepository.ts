import { apiGet, apiPost } from '@/shared/api/client';
import type { ReservationRepository } from '../domain/ports';
import type {
  CancelledBy,
  CreatedReservation,
  Reservation,
  ReservationStatus,
} from '../domain/reservation';

type CreatedDto = {
  id: string;
  user_id: string;
  offer_id: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  status: string;
  created_at: string;
  store_name: string;
  product_name: string;
};

type ItemDto = {
  id: string;
  offer_id: string;
  store_name: string;
  product_name: string;
  quantity: number;
  total_price: number;
  status: string;
  created_at: string;
  cancelled_by: string | null;
  pickup_code: string;
  pickup_address: string;
  pickup_start: string;
  pickup_end: string;
  cancellable_until: string;
};

type ListDto = { reservations: ItemDto[]; page: number; size: number; total: number };
type CancelDto = { id: string; status: string; cancelled_by: string | null };

const STATUSES: readonly ReservationStatus[] = [
  'PENDING_PAYMENT',
  'RESERVED',
  'PICKED_UP',
  'CANCELLED',
];
const CANCELLERS: readonly Exclude<CancelledBy, null>[] = ['CUSTOMER', 'STORE', 'SYSTEM'];

// 정의 밖 값은 조용히 바꾸지 않고 던진다 (docs/design/frontend/reservations.md D-21)
function toStatus(value: string): ReservationStatus {
  const found = STATUSES.find((s) => s === value);
  if (found === undefined) throw new Error(`알 수 없는 status: ${value}`);
  return found;
}

function toCancelledBy(value: string | null): CancelledBy {
  if (value === null) return null;
  const found = CANCELLERS.find((c) => c === value);
  if (found === undefined) throw new Error(`알 수 없는 cancelled_by: ${value}`);
  return found;
}

function toReservation(dto: ItemDto): Reservation {
  return {
    id: dto.id,
    offerId: dto.offer_id,
    storeName: dto.store_name,
    productName: dto.product_name,
    quantity: dto.quantity,
    totalPrice: dto.total_price,
    status: toStatus(dto.status),
    createdAt: new Date(dto.created_at),
    pickupCode: dto.pickup_code,
    pickupAddress: dto.pickup_address,
    cancelledBy: toCancelledBy(dto.cancelled_by),
    pickupStart: new Date(dto.pickup_start),
    pickupEnd: new Date(dto.pickup_end),
    cancellableUntil: new Date(dto.cancellable_until),
  };
}

const reservationPath = (id: string) => `/v1/reservations/${encodeURIComponent(id)}`;

export class HttpReservationRepository implements ReservationRepository {
  async create(
    input: { offerId: string; quantity: number },
    signal?: AbortSignal,
  ): Promise<CreatedReservation> {
    const dto = await apiPost<CreatedDto>(
      '/v1/reservations',
      { offer_id: input.offerId, quantity: input.quantity },
      signal,
    );
    return {
      id: dto.id,
      offerId: dto.offer_id,
      quantity: dto.quantity,
      unitPrice: dto.unit_price,
      totalPrice: dto.total_price,
      status: toStatus(dto.status),
      createdAt: new Date(dto.created_at),
      storeName: dto.store_name,
      productName: dto.product_name,
    };
  }

  async listMine(
    query: { status?: ReservationStatus; page: number; size: number },
    signal?: AbortSignal,
  ): Promise<{ items: Reservation[]; page: number; size: number; total: number }> {
    const params = new URLSearchParams();
    if (query.status !== undefined) params.set('status', query.status);
    params.set('page', String(query.page));
    params.set('size', String(query.size));
    const dto = await apiGet<ListDto>(`/v1/users/me/reservations?${params.toString()}`, signal);
    return {
      items: dto.reservations.map(toReservation),
      page: dto.page,
      size: dto.size,
      total: dto.total,
    };
  }

  async get(id: string, signal?: AbortSignal): Promise<Reservation> {
    return toReservation(await apiGet<ItemDto>(reservationPath(id), signal));
  }

  async cancel(
    id: string,
    signal?: AbortSignal,
  ): Promise<{ id: string; status: ReservationStatus; cancelledBy: CancelledBy }> {
    const dto = await apiPost<CancelDto>(`${reservationPath(id)}/cancel`, undefined, signal);
    return {
      id: dto.id,
      status: toStatus(dto.status),
      cancelledBy: toCancelledBy(dto.cancelled_by),
    };
  }
}
