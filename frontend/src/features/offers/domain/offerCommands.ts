import type { Offer, OfferStatus } from './offer';

export type NewOffer = {
  salePrice: number;
  initialStock: number;
  salesStart?: Date;
  salesEnd: Date;
  pickupStart: Date;
  pickupEnd: Date;
};

export type OfferChanges = {
  salePrice?: number;
  initialStock?: number;
  salesEnd?: Date;
  pickupStart?: Date;
  pickupEnd?: Date;
};

export type DeactivateInput = {
  reason: string;
  cancelReservations: boolean;
};

export type StockAdjustResult = {
  remainingStock: number;
  isSoldOut: boolean;
  status: OfferStatus;
};

export type DeactivateResult = {
  offer: Offer;
  cancelledCount: number;
};

export interface OfferCommands {
  register(productId: string, input: NewOffer, signal?: AbortSignal): Promise<Offer>;
  relist(offerId: string, input: NewOffer, signal?: AbortSignal): Promise<Offer>;
  update(offerId: string, changes: OfferChanges, signal?: AbortSignal): Promise<Offer>;
  deactivate(
    offerId: string,
    input: DeactivateInput,
    signal?: AbortSignal,
  ): Promise<DeactivateResult>;
  adjustStock(
    offerId: string,
    amount: number,
    reason?: string,
    signal?: AbortSignal,
  ): Promise<StockAdjustResult>;
}
