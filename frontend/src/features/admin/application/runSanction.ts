import type { AdminRepository } from '../domain/adminRepository';
import type { ModeratedOffer, ModeratedStore } from '../domain/adminUser';
import type { SanctionKind, ValidSanction } from '../domain/sanction';

export type SanctionResult =
  | { kind: 'user' }
  | { kind: 'withdrawn'; cancelledReservationCount: number }
  | { kind: 'store'; store: ModeratedStore }
  | { kind: 'offer'; offer: ModeratedOffer };

export async function runSanction(
  deps: { admin: AdminRepository },
  kind: SanctionKind,
  targetId: string,
  input: ValidSanction,
): Promise<SanctionResult> {
  const { admin } = deps;
  switch (kind) {
    case 'rejectOwner':
      await admin.rejectOwner(targetId, input.reason);
      return { kind: 'user' };
    case 'suspendUser':
      await admin.suspendUser(targetId, input.reason, input.until);
      return { kind: 'user' };
    case 'withdrawUser': {
      const r = await admin.withdrawUser(targetId, input.reason);
      return { kind: 'withdrawn', cancelledReservationCount: r.cancelledReservationCount };
    }
    case 'suspendStore':
      return { kind: 'store', store: await admin.suspendStore(targetId, input.reason) };
    case 'closeStore':
      return { kind: 'store', store: await admin.closeStore(targetId, input.reason) };
    case 'suspendOffer':
      return { kind: 'offer', offer: await admin.suspendOffer(targetId, input.reason) };
  }
}
