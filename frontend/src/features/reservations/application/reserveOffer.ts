import { findPendingForOffer } from '../domain/cancellation';
import type { ReservationRepository } from '../domain/ports';
import { readErrorInfo } from './errorInfo';
import { fetchAllMine } from './fetchAllMine';

export type ReserveOfferResult =
  | { kind: 'created'; reservationId: string }
  | { kind: 'pendingExists'; reservationId: string | null };

export async function reserveOffer(
  repo: ReservationRepository,
  input: { offerId: string; quantity: number },
  signal: AbortSignal,
): Promise<ReserveOfferResult> {
  try {
    const created = await repo.create(input, signal);
    return { kind: 'created', reservationId: created.id };
  } catch (e) {
    const info = readErrorInfo(e);
    if (info.status !== 409 || info.errorCode !== 'PENDING_RESERVATION_EXISTS') throw e;
    const pending = await fetchAllMine(repo, signal, 'PENDING_PAYMENT');
    return {
      kind: 'pendingExists',
      reservationId: findPendingForOffer(pending, input.offerId)?.id ?? null,
    };
  }
}
