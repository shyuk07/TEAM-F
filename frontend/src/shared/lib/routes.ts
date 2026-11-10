export const ROUTES = {
  login: '/login',
  home: '/',
  owner: '/owner',
  ownerToday: '/owner/today',
  ownerOffers: '/owner/offers',
  ownerOfferNew: '/owner/offers/new',
  ownerStore: '/owner/store',
  ownerProducts: '/owner/products',
  ownerProductNew: '/owner/products/new',
  ownerProduct: (id: string) => `/owner/products/${encodeURIComponent(id)}`,
  myReservations: '/me/reservations',
  checkout: (reservationId: string) => `/checkout/${encodeURIComponent(reservationId)}`,
  paymentComplete: (reservationId: string) =>
    `/checkout/${encodeURIComponent(reservationId)}/complete`,
} as const;

export const ROUTE_PATTERNS = {
  ownerProduct: '/owner/products/:productId',
  checkout: '/checkout/:reservationId',
  paymentComplete: '/checkout/:reservationId/complete',
} as const;
