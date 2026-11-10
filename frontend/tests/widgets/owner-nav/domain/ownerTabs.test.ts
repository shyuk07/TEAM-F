import { OWNER_TABS, activeOwnerTab } from '@/widgets/owner-nav/domain/ownerTabs';
import { ROUTES } from '@/shared/lib/routes';

describe('activeOwnerTab', () => {
  it.each([
    ['/owner/today', 'today'],
    ['/owner/offers', 'offers'],
    ['/owner/offers/', 'offers'],
    ['/owner/offers/new', 'offers'],
    ['/owner/store', 'store'],
    ['/owner/products/new', 'store'],
    ['/owner/products/p1', 'store'],
    ['/owner', null],
    ['/login', null],
    ['/', null],
    ['/owner/offersx', null],
  ])('%s → %s', (pathname, expected) => {
    expect(activeOwnerTab(pathname)).toBe(expected);
  });
});

describe('OWNER_TABS', () => {
  it('3개이고 라벨 순서는 오늘·할인·매장이다', () => {
    expect(OWNER_TABS.map((t) => t.label)).toEqual(['오늘', '할인', '매장']);
  });

  it('경로는 ROUTES 값 순서와 같다', () => {
    expect(OWNER_TABS.map((t) => t.path)).toEqual([
      ROUTES.ownerToday,
      ROUTES.ownerOffers,
      ROUTES.ownerStore,
    ]);
  });
});
