import type { Offer } from '../domain/offer';
import type { OfferChanges, OfferCommands } from '../domain/offerCommands';

export async function saveOffer(
  deps: { commands: OfferCommands },
  offerId: string,
  changes: OfferChanges,
  signal?: AbortSignal,
): Promise<Offer> {
  return deps.commands.update(offerId, changes, signal);
}
