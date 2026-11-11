import { validateDeactivate } from '../domain/deactivation';
import type { DeactivateInput, DeactivateResult, OfferCommands } from '../domain/offerCommands';

export async function deactivateOffer(
  deps: { commands: OfferCommands },
  offerId: string,
  input: DeactivateInput,
  signal?: AbortSignal,
): Promise<DeactivateResult> {
  const issue = validateDeactivate(input);
  if (issue !== null) {
    throw new Error(`유효하지 않은 사유: ${issue}`);
  }
  return deps.commands.deactivate(offerId, input, signal);
}
