export const ROUTES = {
  login: '/login',
  home: '/',
  owner: '/owner',
  ownerToday: '/owner/today',
  ownerOffers: '/owner/offers',
  ownerOfferNew: '/owner/offers/new',
  ownerStore: '/owner/store',
  ownerProductNew: '/owner/products/new',
  ownerProduct: (id: string) => `/owner/products/${encodeURIComponent(id)}`,
} as const;

export const ROUTE_PATTERNS = {
  ownerProduct: '/owner/products/:productId',
} as const;
