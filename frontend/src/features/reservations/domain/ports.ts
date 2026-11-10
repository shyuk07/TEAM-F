import type {
  CancelledBy,
  CreatedReservation,
  Reservation,
  ReservationStatus,
} from './reservation';

export interface ReservationRepository {
  create(
    input: { offerId: string; quantity: number },
    signal?: AbortSignal,
  ): Promise<CreatedReservation>;
  listMine(
    query: { status?: ReservationStatus; page: number; size: number },
    signal?: AbortSignal,
  ): Promise<{ items: Reservation[]; page: number; size: number; total: number }>;
  // GET /v1/reservations/{id} (reference/reservations.md §2-1). 403·404는 ApiError로 던진다.
  get(id: string, signal?: AbortSignal): Promise<Reservation>;
  cancel(
    id: string,
    signal?: AbortSignal,
  ): Promise<{ id: string; status: ReservationStatus; cancelledBy: CancelledBy }>;
}
