import type { Offer } from './offer';

// GET /v1/offers/{id} 응답의 화면용 모양(catalog §10, offers.md §2.1).
export type OfferDetail = {
  offer: Offer;
  description: string | null;
  imageUrls: string[];
  pickupAddress: string;
  latitude: number | null;
  longitude: number | null;
  notice: string;
  cancellableUntil: Date;
  cancelPolicyText: string;
};
