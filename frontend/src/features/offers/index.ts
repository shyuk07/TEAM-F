export type { Offer, OfferStatus, NearbyOffer, OfferPage, OfferList } from './domain/offer';
export { isSoldOut } from './domain/offer';
export type { GeoPoint, OfferSort, RadiusKm } from './domain/nearbyQuery';
export type { HomeFilter } from './domain/homeFilter';
export { readHomeFilter, toHomeSearch, nextRadius, locationChipLabel } from './domain/homeFilter';
export type { OfferRepository } from './domain/offerRepository';
export { salesCountdown, pickupWindow, formatDistance, formatWon } from './domain/offerFormat';
export type { OfferDetail } from './domain/offerDetail';
export type { UnavailableReason, OfferAvailability } from './domain/offerAvailability';
export { offerAvailability, unavailableMessage } from './domain/offerAvailability';
export { readQuantityParam, detailReturnPath } from './domain/detailQuantity';
export {
  OFFERS_LOAD_FAILED_MESSAGE,
  OWNER_APPLY_LINK,
  LOAD_MORE_LABEL,
  SEARCH_LABEL,
  OFFER_DETAIL_LOAD_FAILED_MESSAGE,
  OFFER_NOT_FOUND_MESSAGE,
} from './domain/offerMessages';
export { KEYWORD_MAX_LENGTH } from './domain/nearbyQuery';
export { DEFAULT_MAP_CENTER, mapEmbedUrl, kakaoMapLevel } from './domain/locationMap';

// 상점주 할인 관리 domain
export type {
  OfferCommands,
  NewOffer,
  OfferChanges,
  StockAdjustResult,
  DeactivateResult,
  DeactivateInput,
} from './domain/offerCommands';
export type { OwnerFilter, OwnerRowAction } from './domain/ownerOffer';
export {
  OWNER_FILTERS,
  ownerStatusTag,
  ownerRowActions,
  countByFilter,
  matchesFilter,
  ownerRowSummary,
} from './domain/ownerOffer';
export type { OfferDraft, SalesStart, DraftIssue } from './domain/offerDraft';
export {
  defaultDraft,
  applyQuickPick,
  pickupLeadMinutes,
  cancelDeadline,
  isCancelBlocked,
  QUICK_PICKS,
  quickPickLabel,
  validateDraft,
  toCreateInput,
} from './domain/offerDraft';
export type { OfferEditValues } from './domain/offerEdit';
export { quantityFloor, diffOfferChanges, hasChanges, isEditable } from './domain/offerEdit';
export type { StockMode, StockIssue } from './domain/stockAdjustment';
export {
  STOCK_REASON_MAX,
  STOCK_MAX,
  amountBounds,
  signedAmount,
  stockAfter,
  validateStockAdjust,
} from './domain/stockAdjustment';
export type { DeactivateIssue } from './domain/deactivation';
export { DEACTIVATE_REASON_MAX, validateDeactivate } from './domain/deactivation';
export { OWNER_OFFER_MESSAGES, ownerOfferErrorMessage } from './domain/ownerOfferMessages';

// application
export type { LocationProvider, MapRenderer } from './application/ports';
export {
  OfferRepositoryToken,
  OfferCommandsToken,
  LocationProviderToken,
  MapRendererToken,
} from './application/tokens';
export { useDeviceLocation } from './application/useDeviceLocation';
export { useNearbyOffers } from './application/useNearbyOffers';
export { useOfferDetail } from './application/useOfferDetail';
export { useOwnerOffers } from './application/useOwnerOffers';
export { useOwnerOffer } from './application/useOwnerOffer';
export { useSellableProducts } from './application/useSellableProducts';
export type { CreateOfferMode } from './application/createOffer';
export { useCreateOffer } from './application/useCreateOffer';
export { useSaveOffer } from './application/useSaveOffer';
export { useDeactivateOffer } from './application/useDeactivateOffer';
export { useAdjustStock } from './application/useAdjustStock';
export { useOpenOfferCount } from './application/useOpenOfferCount';

// presentation
export { OfferCard } from './presentation/OfferCard';
export { OfferCardSkeleton } from './presentation/OfferCardSkeleton';
export { SortChips } from './presentation/SortChips';
export { LocationSheet } from './presentation/LocationSheet';
export { LocationMap } from './presentation/LocationMap';
export { NearbyEmpty } from './presentation/NearbyEmpty';
export { OfferImage } from './presentation/OfferImage';
export { OfferDetailBody } from './presentation/OfferDetailBody';
export { OfferDetailSkeleton } from './presentation/OfferDetailSkeleton';
export { OwnerOfferChips } from './presentation/OwnerOfferChips';
export { OwnerOfferRow } from './presentation/OwnerOfferRow';
export { OwnerOfferList } from './presentation/OwnerOfferList';
export { StockAdjustForm } from './presentation/StockAdjustForm';
export { StockAdjustSheet } from './presentation/StockAdjustSheet';
export { OfferCreateForm } from './presentation/OfferCreateForm';
export { OfferScheduleFields } from './presentation/OfferScheduleFields';
export { OfferEditForm } from './presentation/OfferEditForm';
export { OfferDeactivateForm } from './presentation/OfferDeactivateForm';
export { OfferLoadError } from './presentation/OfferLoadError';
