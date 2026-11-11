import type { Offer } from './offer';
import type { OfferChanges } from './offerCommands';

export type OfferEditValues = {
  salePrice: number;
  initialStock: number;
  salesEnd: Date;
  pickupStart: Date;
  pickupEnd: Date;
};

export function quantityFloor(offer: Offer): number {
  const sold = offer.initialStock - offer.remainingStock;
  return Math.max(1, sold);
}

export function diffOfferChanges(offer: Offer, values: OfferEditValues): OfferChanges {
  const changes: OfferChanges = {};

  if (values.salePrice !== offer.salePrice) {
    changes.salePrice = values.salePrice;
  }
  if (values.initialStock !== offer.initialStock) {
    changes.initialStock = values.initialStock;
  }
  if (values.salesEnd.getTime() !== offer.salesEnd.getTime()) {
    changes.salesEnd = values.salesEnd;
  }
  if (values.pickupStart.getTime() !== offer.pickupStart.getTime()) {
    changes.pickupStart = values.pickupStart;
  }
  if (values.pickupEnd.getTime() !== offer.pickupEnd.getTime()) {
    changes.pickupEnd = values.pickupEnd;
  }

  return changes;
}

export function hasChanges(changes: OfferChanges): boolean {
  return Object.keys(changes).length > 0;
}

export function isEditable(offer: Offer): boolean {
  return (
    offer.isActive &&
    (offer.status === 'ON_SALE' || offer.status === 'SCHEDULED' || offer.status === 'SOLD_OUT')
  );
}
