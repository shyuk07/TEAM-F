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
  admin: '/admin',
  adminApprovals: '/admin/approvals',
  adminUsers: '/admin/users',
  adminUser: (id: string) => `/admin/users/${encodeURIComponent(id)}`,
  adminStores: '/admin/stores',
  adminOffers: '/admin/offers',
} as const;

export const ROUTE_PATTERNS = {
  ownerProduct: '/owner/products/:productId',
  adminUser: '/admin/users/:userId',
} as const;
