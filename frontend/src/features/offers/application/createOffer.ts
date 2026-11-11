import type { Offer } from '../domain/offer';
import type { OfferCommands } from '../domain/offerCommands';
import { toCreateInput, type OfferDraft } from '../domain/offerDraft';

export type CreateOfferMode = 'new' | 'relist' | 'refill';

export type CreateOfferInput = {
  mode: CreateOfferMode;
  productId: string;
  sourceOfferId?: string;
  draft: OfferDraft;
  now: Date;
};

export async function createOffer(
  deps: { commands: OfferCommands },
  input: CreateOfferInput,
  signal?: AbortSignal,
): Promise<Offer> {
  const newOfferInput = toCreateInput(input.draft);
  if (input.mode === 'relist' && input.sourceOfferId) {
    return deps.commands.relist(input.sourceOfferId, newOfferInput, signal);
  }
  return deps.commands.register(input.productId, newOfferInput, signal);
}
