import { validatePickupCode } from '../domain/pickupCode';
import type { PickupGateway, PickupResult } from '../domain/pickupGateway';

export type CompletePickupInput = {
  reservationId: string;
  code: string;
};

export async function completePickup(
  deps: { gateway: PickupGateway },
  input: CompletePickupInput,
  signal?: AbortSignal,
): Promise<PickupResult> {
  const issue = validatePickupCode(input.code);
  if (issue !== null) {
    throw new Error(`유효하지 않은 픽업 코드: ${issue}`);
  }
  return deps.gateway.pickup(input.reservationId, input.code.trim(), signal);
}
